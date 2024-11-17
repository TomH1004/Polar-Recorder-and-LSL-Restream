# Polar Recorder and LSL Restream

## Project Overview

Polar Recorder and LSL Restream is a project designed to facilitate data collection and restreaming of biometric signals using a Polar H10 heart rate monitor. It is composed of two main directories: `record` and `stream`. These directories contain scripts for recording biometric data and restreaming that data via Lab Streaming Layer (LSL).

### Directory Structure
- **record**: Contains scripts for recording data and analyzing results.
- **stream**: Contains scripts for restreaming the recorded data via LSL.

## Record Directory
The `record` directory includes two key scripts:

### 1. `record_gui.py`

This script opens a simple GUI that allows for the recording of the following biometric signals:
- Heart Rate (HR)
- RR Interval
- Electrocardiogram (ECG)

Data is collected from a Polar H10 device and transmitted to the **Excite-O-Meter App** via Bluetooth, which then streams the data via LSL. The Excite-O-Meter App is available for **Windows** and **Android** platforms.

The GUI allows the user to:
- Enter a participant ID.
- Record, pause, and add timestamps to the recording session.
- Store each data type in separate CSV files for further analysis.

### 2. `analyzer_gui.py`

This script provides a simple GUI for analyzing the recorded data. The user inputs the participant ID, and the script loads the corresponding CSV files to calculate various metrics, including:
- Minimum, Maximum, Mean values
- Root Mean Square of Successive Differences (RMSSD)
- Interquartile Range (IQR)

The results are displayed for easy review.

## Stream Directory
The `stream` directory contains several scripts designed to restream data from the Excite-O-Meter App via LSL. The available functionality includes:

- **Single Stream Restream**: Restreams a single data stream (HR, RR Interval, or ECG) to enable integration with other applications such as Unity.
- **Parallel Stream Restream**: Restreams HR, RR Interval, and ECG streams concurrently for more complex data analysis or use cases.

### `streamCheck.py`

This utility script lists all available LSL streams to help the user verify the data streams that are currently active and accessible.

## How to Use
1. **Recording Data**:
   - Run `record_gui.py` to start recording biometric data from a Polar H10 device.
   - Enter the participant ID and use the GUI to control the recording session.
   - Data will be stored in separate CSV files in the `record` directory.

2. **Analyzing Data**:
   - Run `analyzer_gui.py` to load and analyze recorded data.
   - Metrics such as min, max, mean, RMSSD, and IQR will be calculated automatically.

3. **Streaming Data**:
   - Use the scripts in the `stream` directory to restream the recorded data via LSL.
   - Run `streamCheck.py` to verify active streams.

## Setup
**environment.yml** can be used for easy setup of dependencies and environment configuration.

## Requirements

- **Polar H10**
- **Excite-O-Meter App** available for Windows and Android