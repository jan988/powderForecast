import openmeteo_requests
import json
import requests_cache
import logging
from retry_requests import retry

import time

# Adjust the sleep time as needed, e.g., 1 second
SLEEP_INTERVAL = 1

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Setup the Open-Meteo API client with cache and retry on error
CACHE_EXPIRY = 86400  # Cache expiry for 24 hours (since forecasts update daily)
cache_session = requests_cache.CachedSession('.cache', expire_after=CACHE_EXPIRY)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# API URL and common parameters
API_URL = "https://api.open-meteo.com/v1/forecast"
COMMON_PARAMS = {
    "daily": ["temperature_2m_max", "apparent_temperature_max", "snowfall_sum", "precipitation_sum",
              "sunshine_duration", "rain_sum", "precipitation_hours", "wind_speed_10m_max"],
    "timezone": "Europe/Berlin",
    "past_days": 14,
    "forecast_days": 14
}

# Initialize the output data structure
output = {}

# Function to fetch weather data for a given resort
def fetch_weather_data(resort):
    """Fetches weather data for a given resort."""
    
    # Initialize output for the resort
    output[resort['resort']] = {
        "country": resort["Country"],  # Add country from the input file
        "url": resort["url"],  # Add resort URL
        "elevations": {},
        "history14daySum": {},
        "3daysSnowSum": {},
        "7daysSnowSum": {},
        "14daysSnowSum": {}
    }
    
    # Elevations to check
    elevations = {
        "Top Lift": resort["topLiftElevation_m"],
        "Mid Lift": resort["midLiftElevation_m"],
        "Bottom Lift": resort["botLiftElevation_m"]
    }
    
    # Loop through each elevation and make API calls
    for lift_name, elevation in elevations.items():
        params = {
            "latitude": float(resort["latitude"]),
            "longitude": float(resort["longitude"]),
            "elevation": elevation,
            "daily": COMMON_PARAMS["daily"],
            "timezone": COMMON_PARAMS["timezone"],
            "past_days": COMMON_PARAMS["past_days"],
            "forecast_days": COMMON_PARAMS["forecast_days"]
        }
        
        try:
            response = openmeteo.weather_api(API_URL, params=params)
            weather_response = response[0]  # Extract first response object
            
            # Extract daily data
            daily_data = weather_response.Daily()
            if daily_data:
                # Initialize data for the specific elevation
                output[resort['resort']]["elevations"][lift_name] = {
                    "elevation_m": elevation,  # Store the elevation value
                    "temperature_2m_max": [],
                    "apparent_temperature_max": [],
                    "snowfall_sum": [],
                    "precipitation_sum": [],
                    "sunshine_duration": [],
                    "rain_sum": [],
                    "precipitation_hours": []
                }
                
                # Extract snowfall_sum data
                snowfall_sum = daily_data.Variables(COMMON_PARAMS['daily'].index('snowfall_sum')).ValuesAsNumpy().tolist()
                logging.info(f"Raw snowfall data for {resort['resort']} at {lift_name}: {snowfall_sum}")
                
                # Calculate snow sums for different periods
                if len(snowfall_sum) >= 28:
                    output[resort['resort']]['history14daySum'][lift_name] = sum(snowfall_sum[:14])
                    output[resort['resort']]['3daysSnowSum'][lift_name] = sum(snowfall_sum[14:17])
                    output[resort['resort']]['7daysSnowSum'][lift_name] = sum(snowfall_sum[14:21])
                    output[resort['resort']]['14daysSnowSum'][lift_name] = sum(snowfall_sum[14:28])
                else:
                    logging.warning(f"Not enough snowfall data for {resort['resort']} at {lift_name}")
                    output[resort['resort']]['history14daySum'][lift_name] = None
                    output[resort['resort']]['3daysSnowSum'][lift_name] = None
                    output[resort['resort']]['7daysSnowSum'][lift_name] = None
                    output[resort['resort']]['14daysSnowSum'][lift_name] = None

                # Store daily values in the output for the specific elevation
                for idx, var in enumerate(COMMON_PARAMS['daily']):
                    output[resort['resort']]["elevations"][lift_name][var] = daily_data.Variables(idx).ValuesAsNumpy().tolist()
            else:
                logging.warning(f"No daily data available for {resort['resort']} at {lift_name}")
        
        except Exception as e:
            logging.error(f"Error fetching data for {resort['resort']} at {lift_name}: {str(e)}")
            
        time.sleep(SLEEP_INTERVAL)

def main():
    # Load resort data from JSON file
    with open('Z_url_merged_resorts.json', 'r', encoding='utf-8') as f:
        resorts = json.load(f)

    
    
    # Loop through each resort and fetch weather data
    for resort in resorts:
        logging.info(f"Fetching data for {resort['resort']}")
        fetch_weather_data(resort)
    
    # Write the output to a file
    with open('weather_dataFull_7.json', 'w', encoding='utf-8') as file:
        json.dump(output, file,ensure_ascii=False, indent=4)
        logging.info("Weather data successfully written to 'weather_dataFull_7.json'")

if __name__ == "__main__":
    main()