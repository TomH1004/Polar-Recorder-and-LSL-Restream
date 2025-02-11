import os
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d

# Directory containing participant data (relative to script location)
base_dir = "./Participant_Data"


# Functions for HRV metrics
def calculate_rmssd(rr_intervals):
    diff = np.diff(rr_intervals)
    squared_diff = diff ** 2
    rmssd = np.sqrt(np.mean(squared_diff))
    return rmssd


def calculate_sdnn(rr_intervals):
    return np.std(rr_intervals, ddof=1)


def calculate_pnn50(rr_intervals):
    diff = np.diff(rr_intervals)
    nn50 = np.sum(np.abs(diff) > 50)  # Count differences greater than 50 ms
    pnn50 = (nn50 / len(rr_intervals)) * 100 if len(rr_intervals) > 0 else None
    return pnn50


# Function to remove outliers and interpolate
def clean_rr_intervals(rr_intervals):
    mean = np.mean(rr_intervals)
    std_dev = np.std(rr_intervals)

    # Identify outliers (values beyond 3 standard deviations)
    non_outliers = (rr_intervals > mean - 3 * std_dev) & (rr_intervals < mean + 3 * std_dev)

    # Create a cleaned series
    cleaned = rr_intervals[non_outliers]

    # Interpolate missing values (outliers removed)
    indices = np.arange(len(rr_intervals))
    valid_indices = indices[non_outliers]
    interpolator = interp1d(valid_indices, cleaned, kind="linear", bounds_error=False, fill_value="extrapolate")

    interpolated = interpolator(indices)
    return interpolated

# Process all folders inside Participant_Data
results = []
for participant in os.listdir(base_dir):
    participant_dir = os.path.join(base_dir, participant)

    if not os.path.isdir(participant_dir):
        continue  # Skip files

    rr_file = os.path.join(participant_dir, "RRinterval_recording.csv")
    timestamp_file = os.path.join(participant_dir, "marked_timestamps.csv")

    if not os.path.exists(rr_file) or not os.path.exists(timestamp_file):
        print(f"Missing required files for {participant}. Skipping.")
        continue

    rr_data = pd.read_csv(rr_file)
    timestamps = pd.read_csv(timestamp_file)

    if rr_data['Value'].max() < 10:  # assuming intervals less than 10 are in seconds
        rr_data['Value'] *= 1000

    # Ensure timestamps are properly formatted
    rr_data['Timestamp'] = pd.to_datetime(rr_data['Timestamp'], unit='s')
    timestamps['Marked Timestamp'] = pd.to_datetime(timestamps['Marked Timestamp'], unit='s')

    # Clean RR intervals
    rr_data['Cleaned Value'] = clean_rr_intervals(rr_data['Value'].values)

    # Overall RMSSD, SDNN, and pNN50
    overall_rmssd = calculate_rmssd(rr_data['Cleaned Value'])
    overall_sdnn = calculate_sdnn(rr_data['Cleaned Value'])
    overall_pnn50 = calculate_pnn50(rr_data['Cleaned Value'])

    segment_count = 1

    # RMSSD, SDNN, and pNN50 between timestamps
    for i in range(len(timestamps) - 1):
        start = timestamps.iloc[i]['Marked Timestamp']
        end = timestamps.iloc[i + 1]['Marked Timestamp']

        # Filter RR intervals within the timestamp range
        interval_data = rr_data[(rr_data['Timestamp'] >= start) & (rr_data['Timestamp'] < end)]

        if len(interval_data) > 1:
            rmssd = calculate_rmssd(interval_data['Cleaned Value'].values)
            sdnn = calculate_sdnn(interval_data['Cleaned Value'].values)
            pnn50 = calculate_pnn50(interval_data['Cleaned Value'].values)
        else:
            rmssd = None
            sdnn = None
            pnn50 = None

        results.append({
            "Participant": f"Participant_hrv_{participant}",
            "Segment": f"Segment_{segment_count}",
            "RMSSD": rmssd,
            "SDNN": sdnn,
            "pNN50": pnn50
        })

        segment_count += 1

    # Add overall metrics
    results.append({
        "Participant": f"Participant_hrv_{participant}",
        "Segment": "Overall",
        "RMSSD": overall_rmssd,
        "SDNN": overall_sdnn,
        "pNN50": overall_pnn50
    })

# Create a DataFrame for all results
hrv_df = pd.DataFrame(results)

# Save to CSV
output_file = "./hrv_values.csv"
hrv_df.to_csv(output_file, index=False)

print(f"HRV values saved to {output_file}")
