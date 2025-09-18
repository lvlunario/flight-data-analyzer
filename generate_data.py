import pandas as pd
import numpy as np
import datetime

def generate_flight_data(filename="flight_data_nordic.csv"):
    """
    Generates an updated, more realistic flight data CSV file.

    This version features a multi-leg flight path over the Nordic region
    and is specifically designed to create dynamic, sustained communication link outages.
    """
    print("Generating new Nordic flight data with sustained comm outages...")

    # --- Simulation Parameters ---
    total_duration_seconds = 9000  # 2.5-hour flight
    data_points = total_duration_seconds * 2 # 2 Hz data rate
    start_time = datetime.datetime(2025, 10, 22, 8, 0, 0)
    time = np.linspace(0, total_duration_seconds, data_points)
    
    # --- Base Flight Profile (Altitude) ---
    altitude = np.zeros(data_points)
    climb_end_idx = int(data_points * 0.1)
    cruise_start_idx = climb_end_idx
    cruise_end_idx = int(data_points * 0.9)
    descent_start_idx = cruise_end_idx

    altitude[:climb_end_idx] = 50000 * np.sin(np.pi/2 * time[:climb_end_idx] / time[climb_end_idx-1])
    altitude[cruise_start_idx:cruise_end_idx] = 50000 + np.sin(time[cruise_start_idx:cruise_end_idx]/200) * 150
    descent_duration = time[-1] - time[descent_start_idx-1]
    altitude[descent_start_idx:] = 50000 * (1 - (time[descent_start_idx:] - time[descent_start_idx-1]) / descent_duration)
    altitude[altitude < 0] = 0

    # --- Realistic Multi-Leg Flight Path (Position) ---
    # Start near Oslo, Norway
    start_lat, start_lon = 59.9, 10.75
    lat = np.full(data_points, start_lat)
    lon = np.full(data_points, start_lon)
    
    # Leg 1: Fly South-West (20% of flight)
    leg1_end_idx = int(data_points * 0.20)
    lon[:leg1_end_idx] = np.linspace(start_lon, 8.0, leg1_end_idx)
    lat[:leg1_end_idx] = np.linspace(start_lat, 58.5, leg1_end_idx)

    # Leg 2: Turn and fly South-East (from 20% to 60%)
    leg2_end_idx = int(data_points * 0.60)
    lon[leg1_end_idx:leg2_end_idx] = np.linspace(lon[leg1_end_idx-1], 11.0, leg2_end_idx - leg1_end_idx)
    lat[leg1_end_idx:leg2_end_idx] = np.linspace(lat[leg1_end_idx-1], 57.0, leg2_end_idx - leg1_end_idx)

    # Leg 3: Second turn, fly West (from 60% to 90%)
    leg3_end_idx = int(data_points * 0.90)
    # --- BUG FIX WAS HERE ---
    lon[leg2_end_idx:leg3_end_idx] = np.linspace(lon[leg2_end_idx-1], 8.5, leg3_end_idx - leg2_end_idx)
    lat[leg2_end_idx:leg3_end_idx] = np.linspace(lat[leg2_end_idx-1], 57.2, leg3_end_idx - leg2_end_idx)
    
    # Final leg: Descend towards destination
    lon[leg3_end_idx:] = np.linspace(lon[leg3_end_idx-1], 8.3, len(lon) - leg3_end_idx)
    lat[leg3_end_idx:] = np.linspace(lat[leg3_end_idx-1], 57.1, len(lat) - leg3_end_idx)

    # --- GNC (with sharp turns) ---
    roll = np.random.randn(data_points) * 0.5
    turn1_indices = slice(leg1_end_idx - 100, leg1_end_idx + 100)
    roll[turn1_indices] = 30 * np.sin(np.pi * np.linspace(0, 1, 200))
    turn2_indices = slice(leg2_end_idx - 100, leg2_end_idx + 100)
    roll[turn2_indices] = -25 * np.sin(np.pi * np.linspace(0, 1, 200))

    # --- Communications Links (Sustained Outages) ---
    # TCDL (Satellite) Link - Sustained outage during the entire second leg
    tcdl_margin = 15 + np.random.randn(data_points) * 0.2
    tcdl_outage_indices = slice(leg1_end_idx, leg2_end_idx)
    tcdl_margin[tcdl_outage_indices] = -5 + np.random.randn(leg2_end_idx - leg1_end_idx) * 0.5 # Deep outage
    
    # LOS (Line-of-Sight) Link - Degrades sharply with distance
    distance_from_start = np.sqrt((lon - start_lon)**2 + (lat - start_lat)**2)
    los_margin = 20 * (altitude/50000) - (distance_from_start * 8) + np.random.randn(data_points) * 0.3 # More aggressive degradation
    los_margin[los_margin < 0] = 0

    # --- Other Subsystems (Simplified for this update) ---
    engine_rpm = 9500 + (altitude/50000 * 1000) + np.random.randn(data_points) * 50
    bus_a_voltage = 28.0 + np.random.randn(data_points) * 0.1

    # --- DataFrame Assembly ---
    timestamps = [start_time + datetime.timedelta(seconds=int(s)) for s in time]
    
    df = pd.DataFrame({
        'Timestamp': timestamps,
        'POS_Latitude_deg': lat, 'POS_Longitude_deg': lon, 'POS_Altitude_ft': altitude,
        'GNC_Roll_deg': roll,
        'PROP_Engine_RPM': engine_rpm,
        'POWER_BusA_Voltage_V': bus_a_voltage,
        'COMM_TCDL_Margin_dB': tcdl_margin,
        'COMM_LOS_Margin_dB': los_margin,
    })
    
    df.to_csv(filename, index=False)
    print(f"Successfully generated '{filename}' with a new Nordic flight path.")

if __name__ == "__main__":
    generate_flight_data()

