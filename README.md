# Aerospace Flight Data Analyzer & Simulator

A comprehensive web-based and standalone application for analyzing and visualizing aerospace flight data with real-time simulation capabilities. Built with Python, Dash, and Plotly for interactive data exploration and mission analysis.

## Features

### 🛩️ Core Capabilities
- **Multi-format Data Loading**: Support for CSV flight data files with automatic validation
- **Real-time Flight Simulation**: Interactive playback of flight missions with customizable speed controls
- **Advanced Visualization**: Multiple visualization modes including 2D plots, 3D scatter plots, and satellite map overlays
- **Communication Link Analysis**: Detailed analysis of SATCOM, LEO, and UHF communication systems
- **Professional Reporting**: Generate PDF and Word reports with embedded visualizations

### 📊 Visualization Modes
1. **Flight Path Analysis**: Interactive satellite map showing complete flight trajectories
2. **Flight Simulator**: Real-time mission playback with aircraft position tracking
3. **Telemetry Plots**: Time-series analysis of subsystem data
4. **3D Scatter Plot**: Multi-dimensional data exploration with customizable axes

### 🛰️ Communication Systems Support
- **GEO SATCOM**: Geostationary satellite communications
- **LEO SATCOM**: Low Earth orbit satellite links
- **UHF LOS**: Ultra High Frequency line-of-sight communications
- **Outage Analysis**: Automatic detection and visualization of communication blackouts

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Required Dependencies
```bash
pip install dash
pip install dash-bootstrap-components
pip install plotly
pip install pandas
pip install numpy
pip install reportlab
pip install python-docx
pip install kaleido  # For static image export
```

### Quick Setup
```bash
# Clone or download the application files
git clone <your-repository-url>
cd flight-data-analyzer

# Install dependencies
pip install -r requirements.txt

# Generate sample data (optional)
python generate_data_advanced.py

# Run the application
python app.py
```

## Usage

### Starting the Application
```bash
python app.py
```
The application will start on `http://localhost:8050`

### Loading Flight Data
1. Click the **"Drag and Drop or Select Flight Data File"** area
2. Upload a CSV file containing flight telemetry data
3. The application will automatically validate and process the data
4. View the validation report in the **Data Validation** panel

### Required Data Format
Your CSV file must contain these essential columns:
- `Timestamp`: Date/time in ISO format
- `POS_Latitude_deg`: Latitude in decimal degrees
- `POS_Longitude_deg`: Longitude in decimal degrees  
- `POS_Altitude_ft`: Altitude in feet

### Optional Subsystem Columns
The application automatically detects subsystems based on column prefixes:
- `GNC_*`: Guidance, Navigation, and Control data
- `COMM_*_dB`: Communication link margins in dB
- `PL_*`: Payload data
- Any other `SUBSYSTEM_*` pattern

### Flight Simulation
1. Load your flight data
2. Navigate to the **"Flight Simulator"** tab
3. Use the simulation controls:
   - **▶ Play/⏸ Pause**: Start/stop the simulation
   - **■ Stop**: Reset to beginning
   - **Speed Selector**: Choose playback speed (1x to 500x)
   - **Time Slider**: Manual position control

### Communication Analysis
1. Select a communication link from the dropdown
2. Set the outage threshold (default: 3.0 dB)
3. View link status on the map (red = outage, blue = normal)
4. Check the summary report for outage statistics

### Report Generation
- **PDF Report**: Click "Download PDF Report" for a professional document
- **Word Report**: Click "Download Word Report" for an editable document
- Both reports include flight path visualizations and analysis summary

## Data Generation

### Sample Mission Data
Generate realistic 5-hour ISR mission data:
```bash
python generate_data_advanced.py
```

This creates `flight_data_mission.csv` with:
- Takeoff and landing at the same base
- Multi-POI orbiting mission
- Realistic communication link behavior
- 18,000+ data points at 1Hz sampling

### Sample Mission Profile
- **Base**: City of Binan, Philippines (14.33°N, 121.05°E)
- **POI 1**: Taal Volcano area with orbital reconnaissance
- **POI 2**: Manila Bay surveillance zone  
- **Duration**: 5 hours with realistic climb/cruise/descent phases
- **Altitude**: Up to 60,000 feet cruise altitude

## File Structure

```
flight-data-analyzer/
├── app.py                      # Main Dash application
├── data_parser.py             # Data validation and processing
├── generate_data_advanced.py  # Sample data generator
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── flight_data_mission.csv   # Generated sample data (optional)
```

## Technical Details

### Architecture
- **Frontend**: Dash with Bootstrap components for responsive UI
- **Backend**: Python with Pandas for data processing
- **Visualization**: Plotly for interactive charts and maps
- **Mapping**: Mapbox satellite imagery integration
- **Reports**: ReportLab (PDF) and python-docx (Word) generation

### Data Processing
- Automatic subsystem detection from column prefixes
- Handling of redacted/missing data (marked as -999.0)
- Timestamp parsing and validation
- Numeric data type coercion and cleaning

### Performance Optimization
- Client-side data storage using Dash Store components
- Efficient callback structure to minimize recomputation
- Configurable simulation speeds for large datasets

## Configuration

### Mapbox Token
The application uses a default Mapbox token for satellite imagery. For production use, replace the token in `app.py`:
```python
mapbox_access_token = "your_mapbox_token_here"
```

### Simulation Settings
Adjust simulation parameters in the callback functions:
- Frame rate: Modify `interval` in `dcc.Interval` component
- Speed options: Update `speed-selector` dropdown values
- Default threshold: Change `outage-threshold-input` value

## Troubleshooting

### Common Issues
1. **Data Loading Fails**: Ensure CSV has required columns and proper timestamp format
2. **Map Not Loading**: Check internet connection and Mapbox token validity
3. **Simulation Lag**: Reduce playback speed or dataset size for better performance
4. **Report Generation Errors**: Verify ReportLab and python-docx installations

### Data Format Requirements
- Timestamps must be parseable by `pd.to_datetime()`
- Numeric columns should contain valid numbers or -999.0 for redacted data
- Geographic coordinates must be in decimal degrees
- Communication link columns should end with `_dB` suffix

## Contributing

This application is designed for aerospace data analysis and can be extended with additional features:
- New subsystem support
- Advanced analytics algorithms
- Additional export formats
- Custom visualization types

## License

MIT License 2025 lvlunario

## Support

For questions or issues, please contact
https://github.com/lvlunario

---

*Built for aerospace professionals who need powerful, interactive flight data analysis capabilities.*