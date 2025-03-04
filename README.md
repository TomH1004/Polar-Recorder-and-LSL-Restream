# Polar H10 Recorder and LSL Restream

## Overview

LSL-Lab.py is a Python application that allows direct connection to a Polar H10 heart rate monitor via Bluetooth Low Energy (BLE) to record and analyze heart rate and RR interval data. The application provides a user-friendly interface with real-time visualization and data analysis capabilities.

## Features

- **Direct Bluetooth Connection**: Connect directly to Polar H10 devices without requiring intermediary applications
- **Real-time Data Visualization**: View heart rate and RR interval data in real-time during recording sessions
- **Session Recording**: Record data sessions with participant IDs for organization
- **Timestamp Marking**: Mark specific moments during recording for later analysis
- **Data Analysis**: Analyze recorded data with statistical metrics including:
  - Mean, median, min, max values
  - Standard deviation
  - Heart rate variability measures (RMSSD, SDNN)
  - Segment analysis between marked timestamps

## Repository Structure

```
Polar-Recorder-and-LSL-Restream/
├── record/                     # Recording and analysis components
│   ├── LSL-Lab.py              # Main application
│   ├── hrv_calc.py             # Heart rate variability calculation
│   └── hrv_overlay.py          # HRV data visualization overlay
├── stream/                     # LSL streaming components
│   ├── hr_stream.py            # Heart rate streaming
│   ├── rr_stream.py            # RR interval streaming
│   ├── ecg_stream.py           # ECG data streaming
│   ├── stream_combined.py      # Combined data streaming
│   └── streamCheck.py          # LSL stream checking utility
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

## Project Components

This repository contains several scripts that work together:

### Main Application
- **LSL-Lab.py** - The main application with a complete GUI for recording and analyzing heart rate data

### Supporting Components
- **hrv_calc.py** - Script for calculating heart rate variability metrics
- **hrv_overlay.py** - Script for overlaying HRV data on visualizations

### Streaming Components
- **hr_stream.py** - Script for streaming heart rate data via LSL
- **rr_stream.py** - Script for streaming RR interval data via LSL
- **ecg_stream.py** - Script for streaming ECG data via LSL
- **stream_combined.py** - Script for streaming combined data via LSL
- **streamCheck.py** - Utility for checking available LSL streams

## Requirements

- Python 3.9 or higher
- Polar H10 heart rate monitor
- Windows, macOS, or Linux with Bluetooth support
- Required Python packages (see requirements.txt)

## Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/Polar-Recorder-and-LSL-Restream.git
cd Polar-Recorder-and-LSL-Restream
```

2. Install the required dependencies:
```
pip install -r requirements.txt
```

3. Run the main application:
```
python record/LSL-Lab.py
```

## Usage

### Main Application (LSL-Lab.py)

#### Recording Data

1. Launch the application by running `python record/LSL-Lab.py`
2. Enter a Participant ID in the left panel
3. Click the "Scan" button to search for nearby Polar devices
4. Select your Polar H10 device from the dropdown menu
5. Click "Connect" to establish a Bluetooth connection
6. Once connected, click "Start Recording" to begin data collection
7. Use the "Mark Timestamp" button to mark specific moments during the recording
8. Click "Stop Recording" when finished

#### Analyzing Data

1. Enter the Participant ID in the right panel
2. Click "Load Data" to load the recorded session
3. The analysis results will display statistics for the entire recording and for segments between marked timestamps

### Using Individual Components

#### HRV Calculation
```
python record/hrv_calc.py
```

#### Streaming Heart Rate Data
```
python stream/hr_stream.py
```

#### Checking Available LSL Streams
```
python stream/streamCheck.py
```

## Data Storage

All data is stored in the `Participant_Data` directory, organized by participant ID. For each recording session, the following files are created:

- `HeartRate_recording.csv`: Heart rate data with timestamps
- `RRinterval_recording.csv`: RR interval data with timestamps
- `marked_timestamps.csv`: Timestamps marked during recording

## Troubleshooting

- **Device Not Found**: Ensure your Polar H10 is charged and in pairing mode
- **Connection Issues**: Try restarting the application and your Polar device
- **Missing Data**: Ensure the Polar H10 is properly positioned on the chest strap
- **Permission Errors**: Make sure the application has write permissions to create and modify files in the application directory
- **LSL Stream Issues**: Use `streamCheck.py` to verify that LSL streams are available

## License

This project is licensed under the MIT License.