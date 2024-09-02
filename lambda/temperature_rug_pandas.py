import os
from datetime import timedelta, datetime
import requests
import json
import sys
import traceback
import logging
import pandas as pd
from io import StringIO

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
FORMAT_CHOICE = 'json'  # Can be 'json', 'csv', or 'xml'
DEFAULT_REVERSE_ORDER = True
STATION_CODE = [240] # List with items. Currently only Schiphol
T_MIN = -5
T_MAX = 30
DEG_LIST = [-40, 0, 6, 12, 18, 24, 30, 50]
COLOR_CODES = ['donkerblauw', 'blauw', 'lichtblauw', 'creme', 'lightrood', 'rood', 'donkerrood']
DATE_START = '20220101'
DATE_END = '20230321'
API_URL = "https://www.daggegevens.knmi.nl/klimatologie/daggegevens" # https://www.knmi.nl/kennis-en-datacentrum/achtergrond/data-ophalen-vanuit-een-script

def get_date_range(event=None):
    try:
        # Default to hardcoded values
        start_date = datetime.strptime(DATE_START, '%Y%m%d')
        end_date = datetime.strptime(DATE_END, '%Y%m%d')

       # 1. Check for command-line arguments (local run)
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                if arg.startswith('startdate='):
                    start_date = datetime.strptime(arg.split('=')[1], '%Y%m%d')
                elif arg.startswith('enddate='):
                    end_date = datetime.strptime(arg.split('=')[1], '%Y%m%d')

        # 2. Check for environment variables (Lambda)
        if 'startdate' in os.environ:
            start_date = datetime.strptime(os.environ['startdate'], '%Y%m%d')
        if 'enddate' in os.environ:
            end_date = datetime.strptime(os.environ['enddate'], '%Y%m%d')

        # 3. Check for API Gateway query string parameters (highest priority)
        if event and 'queryStringParameters' in event:
            params = event['queryStringParameters']
            if params:
                if 'startdate' in params:
                    start_date = datetime.strptime(params['startdate'], '%Y%m%d')
                if 'enddate' in params:
                    end_date = datetime.strptime(params['enddate'], '%Y%m%d')

        return start_date, end_date
    except Exception as e:
        logger.error(f"Error in get_date_range: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def get_reverse_order(event=None):
    try:
        # Default to hardcoded value
        reverse_order = DEFAULT_REVERSE_ORDER

       # 1. Check for command-line arguments (local run)
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                if arg.startswith('reverse_order='):
                    reverse_order = arg.split('=')[1].lower() == 'true'
                    break

        # 2. Check for environment variables (Lambda)
        if 'reverse_order' in os.environ:
            reverse_order = os.environ['reverse_order'].lower() == 'true'

        # 3. Check for API Gateway query string parameters (highest priority)
        if event and 'queryStringParameters' in event:
            params = event['queryStringParameters']
            if params and 'reverse_order' in params:
                reverse_order = params['reverse_order'].lower() == 'true'

        return reverse_order
    except Exception as e:
        logger.error(f"Error in get_reverse_order: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def get_color(temperature):
    try:
        for i, temp in enumerate(DEG_LIST[1:], start=1):
            if temperature < temp:
                return COLOR_CODES[i - 1]
        return COLOR_CODES[-1]
    except Exception as e:
        logger.error(f"Error in get_color: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def KNMI_weer(station_numbers, variables, date_start, date_end, fmt):
    try:
        stations = ':'.join(map(str, station_numbers))
        vars_str = ':'.join(variables)

        payload = {
            'start': date_start.strftime('%Y%m%d'),
            'end': date_end.strftime('%Y%m%d'),
            'vars': vars_str,
            'stns': stations,
            'fmt': fmt
        }

        response = requests.post(API_URL, data=payload)
        response.raise_for_status()

        if response.status_code == 200:
             # Parse JSON data into a pandas DataFrame
            df = pd.read_json(StringIO(response.text), orient='records')
            
            # Convert date to datetime and set as index
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df.set_index('date', inplace=True)
            
            # Divide temperature values by 10
            df[variables] = df[variables] / 10

            return df
        else:
            logger.error(f"Error: Unable to fetch data. Status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error in KNMI_weer: {str(e)}")
        logger.error(traceback.format_exc())
        raise


def temperaturerug(event=None):
    try:
        start_date, end_date = get_date_range(event)
        reverse_order = get_reverse_order(event)

        df = KNMI_weer(station_numbers=STATION_CODE, variables=['TG', 'TN', 'TX'], date_start=start_date, date_end=end_date, fmt=FORMAT_CHOICE)
        if df is None:
            return json.dumps({"error": "Failed to fetch data"})

        # Sort the DataFrame
        df = df.sort_index(ascending=not reverse_order)

        # Apply color functions
        df['min_color'] = df['TN'].apply(get_color)
        df['max_color'] = df['TX'].apply(get_color)

        # Format the output
        date_width, temp_width, color_width = 10, 8, 11
        header = (
            f"| {'Date':<{date_width}} | "
            f"{'Min.Temp':<{temp_width}} | "
            f"{'Min.Kleur':<{color_width}} | "
            f"{'Max.Temp':<{temp_width}} | "
            f"{'Max.Kleur':<{color_width}} |"
        )
        separator = "-" * len(header)
        
        # Create the result list with headers
        result = [separator, header, separator]
        
        # Add data rows
        result.extend([
            f"| {date.strftime('%Y-%m-%d'):<10} | "
            f"{row.loc['TN']:>6.1f}\u00B0C | "
            f"{row.loc['min_color']:<11} | "
            f"{row.loc['TX']:>6.1f}\u00B0C | "
            f"{row.loc['max_color']:<11} |"
            for date, row in df.iterrows()
        ])
        
        # Add bottom separator
        result.append(separator)

        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error in temperaturerug: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def lambda_handler(event, context):
    try:
        result = temperaturerug(event)
        return {
            "statusCode": 200,
            "body": result,
            "headers": {
                "Content-Type": "text/plain; charset=utf-8" 
            },
            "isBase64Encoded": False
        }
    except Exception as e:
        logger.error(f"An error occurred in lambda_handler: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal Server Error",
                "message": str(e)
            }),
            "headers": {
                "Content-Type": "application/json; charset=utf-8"
            },
            "isBase64Encoded": False
        }

if __name__ == '__main__':
    try:
        print(temperaturerug())
    except Exception as e:
        logger.error(f"An error occurred in main: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"An error occurred: {str(e)}")
