import numpy as np
from pylsl import StreamInlet, resolve_stream, StreamInfo, StreamOutlet
import time


def detect_heartbeat(ecg_signal, threshold=100, refractory_period=0.5, last_beat_time=0):
    """
    Detects a heartbeat in the given ECG signal using a threshold and refractory period.

    :param ecg_signal: The ECG signal sample.
    :param threshold: The threshold value to detect a peak (heartbeat).
    :param refractory_period: Minimum time in seconds between heartbeats.
    :param last_beat_time: The timestamp of the last detected heartbeat.
    :return: Tuple (is_beat, new_last_beat_time)
    """
    current_time = time.time()
    if ecg_signal[0] > threshold and (current_time - last_beat_time) > refractory_period:
        return True, current_time
    return False, last_beat_time


def calculate_bpm(beat_timestamps):
    """
    Calculates the BPM from the list of beat timestamps, filtering out the biggest outlier.

    :param beat_timestamps: List of timestamps when beats were detected.
    :return: The calculated BPM.
    """
    if len(beat_timestamps) < 2:
        return 0

    # Calculate time intervals between beats
    intervals = np.diff(beat_timestamps)

    # Calculate the interquartile range (IQR)
    Q1 = np.percentile(intervals, 25)
    Q3 = np.percentile(intervals, 75)
    IQR = Q3 - Q1

    # Determine the lower and upper bounds for outliers
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    # Filter out the outliers
    filtered_intervals = [interval for interval in intervals if lower_bound <= interval <= upper_bound]

    if not filtered_intervals:
        return 0

    mean_interval = np.mean(filtered_intervals)
    bpm = 60.0 / mean_interval
    return bpm


def is_outlier(new_beat_time, beat_timestamps):
    """
    Checks if the new beat time is an outlier based on previous beat timestamps.

    :param new_beat_time: The timestamp of the new beat.
    :param beat_timestamps: List of previous beat timestamps.
    :return: Boolean indicating if the new beat time is an outlier.
    """
    if len(beat_timestamps) < 20:
        return False

    # Calculate time intervals between beats
    intervals = np.diff(beat_timestamps + [new_beat_time])

    # Calculate the interquartile range (IQR)
    Q1 = np.percentile(intervals, 25)
    Q3 = np.percentile(intervals, 75)
    IQR = Q3 - Q1

    # Determine the lower and upper bounds for outliers
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    # Check if the new interval is an outlier
    new_interval = new_beat_time - beat_timestamps[-1]
    if new_interval < lower_bound or new_interval > upper_bound:
        return True
    return False


def main():
    stream_name = 'RawECG'
    stream_type = 'ExciteOMeter'

    print("Attempting to resolve the stream...")
    streams = resolve_stream('name', stream_name)

    if not streams:
        print(f"No streams named '{stream_name}' of type '{stream_type}' found.")
        return

    inlet = StreamInlet(streams[0])
    print(f"Stream '{stream_name}' found, setting up inlet...")
    print(f"Connected to {inlet.info().name()} from {inlet.info().hostname()}.")

    # Create a new stream to send data forward
    info = StreamInfo('RawECG', 'ECG', 1, 0, 'float32', 'myuniqueid12345')
    outlet = StreamOutlet(info)

    last_beat_time = 0
    threshold = 210
    refractory_period = 0.5  # 500 ms refractory period

    beat_timestamps = []

    try:
        while True:
            sample, timestamp = inlet.pull_sample(timeout=3)
            if sample:
                # Forward the sample to the new stream
                outlet.push_sample(sample)

                # Detect heartbeat
                is_beat, last_beat_time = detect_heartbeat(sample, threshold, refractory_period, last_beat_time)
                if is_beat:
                    print(f"Timestamp: {timestamp}, BEAT")

                    # Check if the new beat is an outlier
                    if is_outlier(last_beat_time, beat_timestamps):
                        print(f"Timestamp: {timestamp}, OUTLIER BEAT")
                        if beat_timestamps:
                            # Add an artificial heartbeat based on the average interval
                            average_interval = np.mean(np.diff(beat_timestamps))
                            artificial_beat_time = beat_timestamps[-1] + average_interval
                            beat_timestamps.append(artificial_beat_time)
                            print(f"Artificial heartbeat added at {artificial_beat_time}")
                    else:
                        beat_timestamps.append(last_beat_time)

                    # Keep only the last 20 beat timestamps
                    if len(beat_timestamps) > 20:
                        beat_timestamps.pop(0)

                    # Calculate BPM if we have at least 20 beats
                    if len(beat_timestamps) == 20:
                        bpm = calculate_bpm(beat_timestamps)
                        print(f"Current BPM: {bpm:.2f}")
    except KeyboardInterrupt:
        print("Stream reading interrupted.")


if __name__ == '__main__':
    main()
