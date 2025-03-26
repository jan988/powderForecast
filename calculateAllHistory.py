import pandas as pd
import sys
from datetime import datetime
import os
import io
import contextlib

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def calculate_snowfall_stats(start_date, end_date, country='all', top_n=20):
    """
    Calculate snowfall statistics for ski resorts within a date range.
    Returns top N resorts by average snowfall for the specified country.
    """
    try:
        # Get the directory of the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, 'filtered_weather_data.csv')
        
        print(f"Looking for CSV at: {csv_path}", file=sys.stderr)
        print("Current working directory:", os.getcwd(), file=sys.stderr)
        
        if not os.path.exists(csv_path):
            print(f"Error: CSV file not found at {csv_path}", file=sys.stderr)
            return
            
        # Load the CSV file with absolute path
        df = pd.read_csv(csv_path)
        print(f"Successfully loaded CSV with {len(df)} rows", file=sys.stderr)
        
        # Convert the date column to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Parse input dates
        try:
            start_date = datetime.strptime(start_date, '%m-%d')
            end_date = datetime.strptime(end_date, '%m-%d')
            print(f"Parsed dates: {start_date.strftime('%m-%d')} to {end_date.strftime('%m-%d')}", file=sys.stderr)
        except ValueError as e:
            print(f"Date parsing error: {e}", file=sys.stderr)
            return
        
        # Create a mask for date filtering that ignores the year
        print("Creating date filter mask...", file=sys.stderr)
        if start_date.month <= end_date.month:
            # Normal date range within same year (e.g., Jan to Mar)
            mask = (
                ((df['date'].dt.month == start_date.month) & (df['date'].dt.day >= start_date.day)) |
                (df['date'].dt.month > start_date.month)
            ) & (
                ((df['date'].dt.month == end_date.month) & (df['date'].dt.day <= end_date.day)) |
                (df['date'].dt.month < end_date.month)
            )
        else:
            # Date range spans year boundary (e.g., Dec to Feb)
            mask = (
                ((df['date'].dt.month == start_date.month) & (df['date'].dt.day >= start_date.day)) |
                (df['date'].dt.month > start_date.month) |
                ((df['date'].dt.month == end_date.month) & (df['date'].dt.day <= end_date.day)) |
                (df['date'].dt.month < end_date.month)
            )
        
        filtered_df = df[mask]
        print(f"Filtered to {len(filtered_df)} rows after date filtering", file=sys.stderr)
        
        # Apply country filter if specified
        if country.lower() != 'all':
            filtered_df = filtered_df[filtered_df['country'].str.lower() == country.lower()]
            print(f"Filtered to {len(filtered_df)} rows after country filtering", file=sys.stderr)
        
        # Calculate days in period
        if start_date.month == 12 and end_date.month < 12:
            days_in_december = 31 - start_date.day + 1
            days_in_period = days_in_december + end_date.day
        else:
            if start_date.month == end_date.month:
                days_in_period = end_date.day - start_date.day + 1
            else:
                month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                if start_date.month < end_date.month:
                    days_in_period = (month_days[start_date.month - 1] - start_date.day + 1 +
                                    sum(month_days[start_date.month:(end_date.month - 1)]) +
                                    end_date.day)
                else:
                    days_in_period = (month_days[start_date.month - 1] - start_date.day + 1 +
                                    sum(month_days[start_date.month:] + month_days[:end_date.month - 1]) +
                                    end_date.day)
        
        print(f"Calculated days in period: {days_in_period}", file=sys.stderr)

        # Check if we have data to process
        if len(filtered_df) == 0:
            print("No data found for the specified criteria", file=sys.stderr)
            return

        # Group by resort and calculate statistics
        resort_stats = filtered_df.groupby(['country', 'resort', 'elevation'])['snowfall_sum'].agg([
            ('avg_snowfall', 'mean')
        ]).reset_index()
        
        # Calculate total snowfall based on avg_snowfall * days_in_period
        resort_stats['total_snowfall'] = resort_stats['avg_snowfall'] * days_in_period
        
        # Sort by average snowfall and get top N resorts
        resort_stats = resort_stats.nlargest(top_n, 'avg_snowfall')
        
        print(f"Found {len(resort_stats)} resorts with data", file=sys.stderr)
        
        # Format results for output
        for _, row in resort_stats.iterrows():
            resort_name = f"{row['resort']} ({row['elevation']}m)"
            resort_name = resort_name.replace('\u200b', '').replace('\u2010', '-')
            country = row['country'].replace('\u200b', '').replace('\u2010', '-')
            
            print(f"Location: {resort_name}, Avg Snowfall: {row['avg_snowfall']}, Total Snowfall: {row['total_snowfall']}, Country: {country}")

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

if __name__ == '__main__':
    if len(sys.argv) not in [3, 4]:
        print("Usage: python script.py <start_date> <end_date> [country]", file=sys.stderr)
        sys.exit(1)
    
    start_date = sys.argv[1]  # MM-DD format
    end_date = sys.argv[2]    # MM-DD format
    country = sys.argv[3] if len(sys.argv) > 3 else 'all'
    
    print(f"Starting calculation with params: start_date={start_date}, end_date={end_date}, country={country}", file=sys.stderr)
    calculate_snowfall_stats(start_date, end_date, country)
