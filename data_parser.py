import pandas as pd
import numpy as np
import re

# Define core data columns that are absolutely essential for basic analysis.
CORE_COLUMNS = ['Timestamp', 'POS_Latitude_deg', 'POS_Longitude_deg', 'POS_Altitude_ft']
REDACTED_DATA_MARKER = -999.0

def discover_subsystems(df_columns):
    """Dynamically identifies subsystems and payloads from column prefixes."""
    subsystems = set()
    payloads = set()
    prefix_pattern = re.compile(r'^([A-Z0-9]+)_') # e.g., GNC_, PL_GMTI_

    for col in df_columns:
        match = prefix_pattern.match(col)
        if match:
            prefix = match.group(1)
            if prefix.startswith('PL'):
                payloads.add(prefix)
            else:
                subsystems.add(prefix)
    
    return sorted(list(subsystems)), sorted(list(payloads))

def load_and_validate_data(filepath):
    """
    Loads flight data, validates its integrity, handles missing/redacted data,
    and returns a clean DataFrame along with a summary report.

    Args:
        filepath (str): The path to the data file.

    Returns:
        tuple: (pandas.DataFrame, dict)
               A tuple containing the cleaned DataFrame (or None on failure)
               and a dictionary summarizing the validation process.
    """
    report = {
        'status': 'failure',
        'warnings': [],
        'subsystems_found': [],
        'payloads_found': [],
        'redacted_cols_found': []
    }

    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        report['warnings'].append(f"File not found: {filepath}")
        return None, report
    except Exception as e:
        report['warnings'].append(f"Failed to read file: {e}")
        return None, report

    # --- Validation 1: Core Columns ---
    missing_core = [col for col in CORE_COLUMNS if col not in df.columns]
    if missing_core:
        report['warnings'].append(f"Data is missing essential columns: {missing_core}")
        return None, report
    
    # --- Data Cleaning & Processing ---
    # 1. Handle Timestamp
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    if df['Timestamp'].isnull().any():
        report['warnings'].append("Some timestamps were invalid and have been removed.")
        df.dropna(subset=['Timestamp'], inplace=True)

    # 2. Handle Redacted Data
    for col in df.select_dtypes(include=np.number).columns:
        if (df[col] == REDACTED_DATA_MARKER).any():
            report['redacted_cols_found'].append(col)
            df[col].replace(REDACTED_DATA_MARKER, np.nan, inplace=True)
            
    # 3. Coerce numeric-like object columns to numeric
    for col in df.columns:
        if col != 'Timestamp' and df[col].dtype == 'object':
            # This is a safe way to check if conversion is possible without raising errors on mixed types
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 4. Handle Missing Data in Core Columns
    rows_before_drop = len(df)
    df.dropna(subset=CORE_COLUMNS, inplace=True)
    rows_after_drop = len(df)
    if rows_before_drop > rows_after_drop:
        report['warnings'].append(f"Dropped {rows_before_drop - rows_after_drop} rows due to missing core data.")

    # --- Final Report Generation ---
    report['subsystems_found'], report['payloads_found'] = discover_subsystems(df.columns)
    report['status'] = 'success'
    
    print("--- Data Parser Report ---")
    for key, value in report.items():
        if value: # Only print if there's something to report
            print(f"- {key.replace('_', ' ').title()}: {value}")
    print("--------------------------")
    
    return df, report

if __name__ == '__main__':
    # This block is for directly testing the parser script.
    # It assumes 'flight_data_industrial.csv' has ALREADY been created.
    print("\nAttempting to parse the industrial-grade data file...")
    
    flight_df, report = load_and_validate_data('flight_data_industrial.csv')

    if report['status'] == 'success' and flight_df is not None:
        print("\n--- Data Head ---")
        print(flight_df.head())
    else:
        print("\nParsing failed. Please ensure 'flight_data_industrial.csv' exists by running 'generate_data.py' first.")

