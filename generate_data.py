import pandas as pd
import numpy as np
import datetime

def generate_flight_data(filename="flight_data.csv"):
    """
    Generates a synthetic flight data CSV file with a realistic flight profile.
    """
    print("Generating synthetic flight data...")

    # Simulation parameters
    total_duration_seconds = 3600  # 1 hour flight
    data_points = total_duration_seconds  # 1 Hz data rate
    start_time = datetime.datetime(2025, 9, 18, 14, 0, 0)

    # Base flight path (simple trajectory)
    time = np.linspace(0, total_duration_seconds, data_points)
    altitude = np.zeros(data_points)
    lat = np.zeros(data_points)
    lon = np.zeros(data_points)
    
    # --- Flight Profile Phases ---
    # 1. Takeoff and Climb (first 10 minutes)
    climb_end = 600
    altitude[:climb_end] = 30000 * (time[:climb_end] / climb_end) # Climb to 30,000 ft
    
    # 2. Cruise (from 10 mins to 50 mins)
    cruise_start = climb_end
    cruise_end = 3000
    altitude[cruise_start:cruise_end] = 30000
    
    # 3. Descent and Landing (last 10 minutes)
    descent_start = cruise_end
    altitude[descent_start:] = 30000 * (1 - (time[descent_start:] - descent_start) / (total_duration_seconds - descent_start))
    altitude[altitude < 0] = 0 # Ensure altitude doesn't go below zero

    # Simulate position changes (simple linear path for now)
    # Starting at a known location (e.g., near Edwards AFB)
    start_lat, start_lon = 34.9, -117.9
    # Assume an average ground speed of 500 mph -> ~0.138 miles/sec -> ~0.002 deg/sec
    lon = start_lon + 0.002 * time
    
    # Introduce a banking turn during cruise
    turn_start = 1500
    turn_end = 1800
    lat[cruise_start:turn_start] = start_lat
    turn_duration = turn_end - turn_start
    lat[turn_start:turn_end] = start_lat + 2 * ( (time[turn_start:turn_end] - turn_start) / turn_duration )**2
    lat[turn_end:] = lat[turn_end-1]


    # --- Subsystem Telemetry ---
    # Engine Temp (heats up on climb, cools on descent)
    engine_temp = 150 + (altitude / 30000) * 800 + np.random.randn(data_points) * 10
    
    # Fuel Level (decreases linearly)
    fuel_level = 100 - (time / total_duration_seconds) * 85 + np.random.randn(data_points) * 0.5
    fuel_level[fuel_level < 0] = 0

    # Communications Link Status (simulate some dropouts during the turn)
    comm_status = np.ones(data_points, dtype=int)
    dropout_indices = np.random.randint(turn_start, turn_end, size=30)
    comm_status[dropout_indices] = 0 # 1 = Link OK, 0 = Link Outage

    # Orientation (Roll, Pitch, Yaw)
    roll = np.zeros(data_points)
    roll[turn_start:turn_end] = 30 * np.sin(np.pi * (time[turn_start:turn_end] - turn_start) / turn_duration)
    roll += np.random.randn(data_points) * 0.5 # Add noise

    # --- DataFrame Assembly ---
    timestamps = [start_time + datetime.timedelta(seconds=int(s)) for s in time]

    df = pd.DataFrame({
        'Timestamp': timestamps,
        'Latitude': lat,
        'Longitude': lon,
        'Altitude_ft': altitude,
        'Roll_deg': roll,
        'Pitch_deg': np.random.randn(data_points) * 1.0, # Placeholder
        'Yaw_deg': np.random.randn(data_points) * 1.0, # Placeholder
        'Engine_Temp_C': engine_temp,
        'Fuel_Level_percent': fuel_level,
        'Comm_Link_Status': comm_status
    })

    df.to_csv(filename, index=False)
    print(f"Successfully generated '{filename}' with {len(df)} data points.")


if __name__ == "__main__":
    generate_flight_data()