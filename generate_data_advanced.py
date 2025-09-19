import pandas as pd
import numpy as np
import datetime

def generate_mission_data(filename="flight_data_mission.csv"):
    """
    Generates a highly realistic, 5-hour ISR mission flight data file.

    Features:
    - Takeoff and landing at the same point (RTB - Return to Base).
    - Flight path orbits multiple Points of Interest (POIs).
    - Simulates three distinct communication links with different behaviors.
    """
    print(f"Generating advanced 5-hour mission data...")

    # --- Mission Parameters ---
    total_duration_seconds = 5 * 3600  # 5 hours
    data_points = total_duration_seconds * 1 # 1 Hz data rate for longer flight
    start_time = datetime.datetime(2025, 9, 19, 9, 0, 0) # 9 AM local time
    time = np.linspace(0, total_duration_seconds, data_points)

    # --- Points of Interest (POIs) in the Philippines ---
    base_location = {'lat': 14.33, 'lon': 121.05} # City of Binan
    poi_1 = {'lat': 14.01, 'lon': 120.99, 'radius': 0.15, 'name': 'Taal Volcano'}
    poi_2 = {'lat': 14.59, 'lon': 120.98, 'radius': 0.1, 'name': 'Manila Bay'}

    # --- Altitude Profile (Climb -> Cruise -> Descend) ---
    altitude = np.zeros(data_points)
    climb_end_idx = int(data_points * 0.08)
    descent_start_idx = int(data_points * 0.92)
    altitude[:climb_end_idx] = 60000 * np.sin(np.pi/2 * time[:climb_end_idx] / time[climb_end_idx-1])
    altitude[climb_end_idx:descent_start_idx] = 60000
    descent_duration = time[-1] - time[descent_start_idx-1]
    altitude[descent_start_idx:] = 60000 * (1 - (time[descent_start_idx:] - time[descent_start_idx-1]) / descent_duration)
    altitude[altitude < 0] = 0

    # --- Flight Path Generation (Multi-Leg Orbiting Mission) ---
    lat = np.full(data_points, base_location['lat'])
    lon = np.full(data_points, base_location['lon'])
    
    # Define mission phases by index
    transit_to_poi1_end = int(data_points * 0.15)
    orbit_poi1_end = int(data_points * 0.40)
    transit_to_poi2_end = int(data_points * 0.50)
    orbit_poi2_end = int(data_points * 0.75)
    return_to_base_end = int(data_points * 0.92)

    # 1. Transit to POI 1 (Taal)
    lat[climb_end_idx:transit_to_poi1_end] = np.linspace(base_location['lat'], poi_1['lat'], transit_to_poi1_end - climb_end_idx)
    lon[climb_end_idx:transit_to_poi1_end] = np.linspace(base_location['lon'], poi_1['lon'], transit_to_poi1_end - climb_end_idx)

    # 2. Orbit POI 1 (2 full orbits)
    orbit1_points = orbit_poi1_end - transit_to_poi1_end
    angle = np.linspace(0, 4 * np.pi, orbit1_points)
    lat[transit_to_poi1_end:orbit_poi1_end] = poi_1['lat'] + poi_1['radius'] * np.sin(angle)
    lon[transit_to_poi1_end:orbit_poi1_end] = poi_1['lon'] + poi_1['radius'] * np.cos(angle)
    
    # 3. Transit to POI 2 (Manila Bay)
    lat[orbit_poi1_end:transit_to_poi2_end] = np.linspace(lat[orbit_poi1_end-1], poi_2['lat'], transit_to_poi2_end - orbit_poi1_end)
    lon[orbit_poi1_end:transit_to_poi2_end] = np.linspace(lon[orbit_poi1_end-1], poi_2['lon'], transit_to_poi2_end - orbit_poi1_end)
    
    # 4. Orbit POI 2
    orbit2_points = orbit_poi2_end - transit_to_poi2_end
    angle = np.linspace(0, 4 * np.pi, orbit2_points)
    lat[transit_to_poi2_end:orbit_poi2_end] = poi_2['lat'] + poi_2['radius'] * np.sin(angle)
    lon[transit_to_poi2_end:orbit_poi2_end] = poi_2['lon'] + poi_2['radius'] * np.cos(angle)
    
    # 5. Return to Base
    lat[orbit_poi2_end:return_to_base_end] = np.linspace(lat[orbit_poi2_end-1], base_location['lat'], return_to_base_end - orbit_poi2_end)
    lon[orbit_poi2_end:return_to_base_end] = np.linspace(lon[orbit_poi2_end-1], base_location['lon'], return_to_base_end - orbit_poi2_end)

    # --- Simulate Three Communication Links ---
    # 1. GEO SATCOM: Very stable, slight degradation on turns
    roll = np.gradient(np.unwrap(np.arctan2(np.gradient(lat), np.gradient(lon)))) * 1000
    roll = np.clip(roll, -30, 30) + np.random.randn(data_points)
    comm_geo_satcom = 20 - np.abs(roll)/10 + np.random.randn(data_points) * 0.1

    # 2. LEO SATCOM: Good signal, but with predictable long outage window
    comm_leo_satcom = np.full(data_points, 18.0)
    leo_outage_start = int(data_points * 0.45)
    leo_outage_end = int(data_points * 0.65)
    comm_leo_satcom[leo_outage_start:leo_outage_end] = -5.0 # Deep outage
    comm_leo_satcom += np.random.randn(data_points) * 0.2
    
    # 3. UHF LOS: Dependent on distance from base and altitude
    distance_from_base = np.sqrt((lon - base_location['lon'])**2 + (lat - base_location['lat'])**2)
    comm_uhf_los = 30 * (altitude/60000) - (distance_from_base * 40) + np.random.randn(data_points)
    comm_uhf_los[comm_uhf_los < -10] = -10

    # --- DataFrame Assembly ---
    timestamps = [start_time + datetime.timedelta(seconds=int(s)) for s in time]
    
    df = pd.DataFrame({
        'Timestamp': timestamps,
        'POS_Latitude_deg': lat,
        'POS_Longitude_deg': lon,
        'POS_Altitude_ft': altitude,
        'GNC_Roll_deg': roll,
        'COMM_GEO_SATCOM_dB': comm_geo_satcom,
        'COMM_LEO_SATCOM_dB': comm_leo_satcom,
        'COMM_UHF_LOS_dB': comm_uhf_los,
    })
    
    df.to_csv(filename, index=False)
    print(f"Successfully generated '{filename}' with {len(df)} data points.")

if __name__ == "__main__":
    generate_mission_data()