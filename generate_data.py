import pandas as pd
import numpy as np
import datetime

def generate_flight_data(filename="flight_data_industrial.csv"):
    """
    Generates a synthetic, industrial-grade flight data CSV file.

    This version includes multiple subsystems, payloads, data links,
    and simulates anomalies, missing data, and classified/redacted data.
    """
    print("Generating industrial-grade synthetic flight data...")

    # --- Simulation Parameters ---
    total_duration_seconds = 7200  # 2-hour flight
    data_points = total_duration_seconds * 2 # 2 Hz data rate
    # Set start time based on current time
    start_time = datetime.datetime(2025, 9, 18, 20, 54, 0)
    time = np.linspace(0, total_duration_seconds, data_points)
    
    # --- Base Flight Profile (Position & Altitude) ---
    altitude = np.zeros(data_points)
    lat = np.zeros(data_points)
    lon = np.zeros(data_points)
    
    # Profile Phases
    climb_end_idx = int(data_points * 0.15)    # First 15% of flight
    cruise_start_idx = climb_end_idx
    cruise_end_idx = int(data_points * 0.85)   # Cruise until 85% mark
    descent_start_idx = cruise_end_idx

    # 1. Takeoff and Climb
    altitude[:climb_end_idx] = 45000 * (time[:climb_end_idx] / time[climb_end_idx-1])**2
    
    # 2. Cruise
    altitude[cruise_start_idx:cruise_end_idx] = 45000 + np.sin(time[cruise_start_idx:cruise_end_idx]/100) * 200 # slight variation
    
    # 3. Descent
    descent_duration = time[-1] - time[descent_start_idx-1]
    altitude[descent_start_idx:] = 45000 * (1 - (time[descent_start_idx:] - time[descent_start_idx-1]) / descent_duration)**2
    altitude[altitude < 0] = 0

    # Position (starting near City of Binan, Philippines)
    start_lat, start_lon = 14.33, 121.05
    lon = start_lon + 0.0015 * time # Fly eastward
    lat = start_lat - 0.0005 * time # Fly southward

    # --- GNC (Guidance, Navigation, and Control) ---
    roll = np.random.randn(data_points) * 0.2
    pitch = np.zeros(data_points)
    yaw = np.random.randn(data_points) * 0.2 + 135 # Heading South-East
    
    # Add a banking turn during cruise
    turn_start_idx = int(data_points * 0.4)
    turn_end_idx = int(data_points * 0.5)
    turn_duration_idx = turn_end_idx - turn_start_idx
    roll[turn_start_idx:turn_end_idx] = 25 * np.sin(np.pi * np.linspace(0, 1, turn_duration_idx))

    # --- Propulsion ---
    engine_rpm = np.zeros(data_points)
    engine_rpm[:climb_end_idx] = 2000 + 7500 * (time[:climb_end_idx]/time[climb_end_idx-1])
    engine_rpm[cruise_start_idx:cruise_end_idx] = 9500 + np.random.randn(cruise_end_idx - cruise_start_idx) * 50
    engine_rpm[descent_start_idx:] = 9500 - 6500 * ((time[descent_start_idx:]-time[descent_start_idx-1])/descent_duration)
    fuel_flow = (engine_rpm / 1000) * 2.5 + np.random.randn(data_points) * 0.1 # kg/s

    # --- Power System ---
    bus_a_voltage = 28.0 + np.random.randn(data_points) * 0.1
    bus_b_voltage = 28.0 + np.random.randn(data_points) * 0.1
    # Simulate a Bus A undervoltage anomaly
    anomaly_start_idx = int(data_points * 0.6)
    anomaly_end_idx = int(data_points * 0.62)
    bus_a_voltage[anomaly_start_idx:anomaly_end_idx] -= 4.0

    # --- Thermal System ---
    avionics_temp = 25 + (altitude / 45000) * 15 + np.random.randn(data_points) * 0.5
    payload_bay_temp = 20 - (altitude / 45000) * 25 + np.random.randn(data_points) * 1.2

    # --- Communications Links ---
    # TCDL (Satellite) Link - affected by roll
    tcdl_margin = 15 - np.abs(roll/10) + np.random.randn(data_points) * 0.2
    # LOS (Line-of-Sight) Link - affected by altitude/distance
    los_margin = 20 * (altitude/45000) - 5 + np.random.randn(data_points) * 0.3
    los_margin[los_margin < 0] = 0

    # --- Payloads ---
    # Activate payloads only mid-cruise
    pl_active_start_idx = int(data_points * 0.3)
    pl_active_end_idx = int(data_points * 0.7)
    
    # Payload 1: GMTI (Ground Moving Target Indicator)
    pl_gmti_status = np.full(data_points, "STBY")
    pl_gmti_status[pl_active_start_idx:pl_active_end_idx] = "ACTIVE"
    # When Bus A voltage drops, GMTI goes into safe mode
    pl_gmti_status[anomaly_start_idx:anomaly_end_idx] = "SAFE"
    pl_gmti_power_draw = np.zeros(data_points)
    pl_gmti_power_draw[pl_gmti_status == "ACTIVE"] = 500 + np.random.randn(np.sum(pl_gmti_status == "ACTIVE"))*10

    # Payload 2: EISS (Electro-optical Imaging Sensor Suite)
    pl_eiss_status = np.full(data_points, "OFF")
    pl_eiss_status[pl_active_start_idx:pl_active_end_idx] = "ACTIVE"
    pl_eiss_target_coords = np.full(data_points, "NONE")
    pl_eiss_target_coords[pl_active_start_idx:pl_active_end_idx] = "-999.0" # REDACTED FOR CLASSIFICATION

    # --- DataFrame Assembly ---
    timestamps = [start_time + datetime.timedelta(seconds=int(s)) for s in time]
    
    df = pd.DataFrame({
        'Timestamp': timestamps,
        'POS_Latitude_deg': lat, 'POS_Longitude_deg': lon, 'POS_Altitude_ft': altitude,
        'GNC_Roll_deg': roll, 'GNC_Pitch_deg': pitch, 'GNC_Yaw_deg': yaw,
        'PROP_Engine_RPM': engine_rpm, 'PROP_FuelFlow_kgs': fuel_flow,
        'POWER_BusA_Voltage_V': bus_a_voltage, 'POWER_BusB_Voltage_V': bus_b_voltage,
        'THERMAL_Avionics_C': avionics_temp, 'THERMAL_PayloadBay_C': payload_bay_temp,
        'COMM_TCDL_Margin_dB': tcdl_margin, 'COMM_LOS_Margin_dB': los_margin,
        'PL_GMTI_Status': pl_gmti_status, 'PL_GMTI_Power_W': pl_gmti_power_draw,
        'PL_EISS_Status': pl_eiss_status, 'PL_EISS_Target_Coords': pl_eiss_target_coords,
    })

    # --- Introduce Missing Data ---
    sensor_cols = [col for col in df.columns if col not in ['Timestamp', 'PL_GMTI_Status', 'PL_EISS_Status', 'PL_EISS_Target_Coords']]
    for col in sensor_cols:
        if np.random.rand() < 0.3: # 30% chance for a column to have NaNs
            nan_indices = df.sample(frac=0.01).index # Corrupt 1% of the data
            df.loc[nan_indices, col] = np.nan
    
    df.to_csv(filename, index=False)
    print(f"Successfully generated '{filename}' with {len(df)} data points and expanded subsystems.")

if __name__ == "__main__":
    generate_flight_data()

