# Polar H10 Recorder and Analyzer

## Project Overview

This application allows direct connection to a Polar H10 heart rate monitor via Bluetooth Low Energy (BLE) to record and analyze heart rate and RR interval data. The application provides a user-friendly interface for recording sessions and analyzing the collected data.

## Features

- **Direct Bluetooth Connection**: Connect directly to Polar H10 devices without requiring intermediary applications.
- **Real-time Data Visualization**: View heart rate and RR interval data in real-time during recording sessions.
- **Session Recording**: Record data sessions with participant IDs for organization.
- **Timestamp Marking**: Mark specific moments during recording for later analysis.
- **Data Analysis**: Analyze recorded data with statistical metrics including mean, median, min, max, standard deviation, and heart rate variability measures (RMSSD, SDNN).

## Requirements

- Python 3.9 or higher
- Polar H10 heart rate monitor
- Windows, macOS, or Linux with Bluetooth support
- Required Python packages (see environment.yml)

## Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/Polar-Recorder-and-Analyzer.git
cd Polar-Recorder-and-Analyzer
```

2. Create and activate a conda environment using the provided environment.yml file:
```
conda env create -f environment.yml
conda activate heart_rate_project
```

3. Run the application:
```
python record/LSL-Lab.py
```

## Usage

### Recording Data

1. Launch the application.
2. Enter a Participant ID in the left panel.
3. Click the "Scan" button to search for nearby Polar devices.
4. Select your Polar H10 device from the dropdown menu.
5. Click "Connect" to establish a Bluetooth connection.
6. Once connected, click "Start Recording" to begin data collection.
7. Use the "Mark Timestamp" button to mark specific moments during the recording.
8. Click "Stop Recording" when finished.

### Analyzing Data

1. Enter the Participant ID in the right panel.
2. Click "Load Data" to load the recorded session.
3. The analysis results will display statistics for the entire recording and for segments between marked timestamps.

## Data Storage

All data is stored in the `Participant_Data` directory, organized by participant ID. For each recording session, the following files are created:

- `HeartRate_recording.csv`: Heart rate data with timestamps
- `RRinterval_recording.csv`: RR interval data with timestamps
- `marked_timestamps.csv`: Timestamps marked during recording

## Troubleshooting

- **Device Not Found**: Ensure your Polar H10 is charged and in pairing mode.
- **Connection Issues**: Try restarting the application and your Polar device.
- **Missing Data**: Ensure the Polar H10 is properly positioned on the chest strap.

## License

This project is licensed under the MIT License - see the LICENSE file for details.