import matplotlib.pyplot as plt
import numpy as np
from pylsl import StreamInlet, resolve_stream, StreamInfo, StreamOutlet
from scipy import interpolate


def remove_outliers(rr_intervals, z_threshold=3.0):
    rr_intervals = np.array(rr_intervals)
    mean_rr = np.mean(rr_intervals)
    std_rr = np.std(rr_intervals)
    z_scores = np.abs((rr_intervals - mean_rr) / std_rr)
    non_outliers = z_scores < z_threshold
    filtered_rr_intervals = rr_intervals[non_outliers]
    return filtered_rr_intervals, non_outliers


def interpolate_missing_values(rr_intervals, non_outliers):
    x = np.arange(len(rr_intervals))
    y = np.array(rr_intervals)
    f = interpolate.interp1d(x[non_outliers], y[non_outliers], kind='linear', fill_value="extrapolate")
    interpolated_rr_intervals = f(x)
    return interpolated_rr_intervals


def calculate_hrv_metrics(rr_intervals):
    rr_intervals = np.array(rr_intervals)
    filtered_rr_intervals, non_outliers = remove_outliers(rr_intervals)
    clean_rr_intervals = interpolate_missing_values(rr_intervals, non_outliers)
    sdnn = np.std(clean_rr_intervals, ddof=1)
    rmssd = np.sqrt(np.mean(np.diff(clean_rr_intervals) ** 2))
    return sdnn, rmssd, clean_rr_intervals


def plot_hrv_metrics(sdnn_values, rmssd_values):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    ax1.plot(sdnn_values, marker='o', linestyle='-', color='b', label='SDNN')
    ax1.set_title('SDNN (Standard Deviation of NN Intervals)')
    ax1.set_xlabel('Time (seconds)')
    ax1.set_ylabel('SDNN (ms)')
    ax1.legend()

    ax2.plot(rmssd_values, marker='o', linestyle='-', color='g', label='RMSSD')
    ax2.set_title('RMSSD (Root Mean Square of Successive Differences)')
    ax2.set_xlabel('Time (seconds)')
    ax2.set_ylabel('RMSSD (ms)')
    ax2.legend()

    plt.tight_layout()
    plt.show()


def main():
    stream_name = 'RRinterval'
    stream_type = 'ExciteOMeter'

    print("Attempting to resolve the stream...")
    streams = resolve_stream('name', stream_name)

    if not streams:
        print(f"No streams named '{stream_name}' of type '{stream_type}' found.")
        return

    inlet = StreamInlet(streams[0])
    print(f"Stream '{stream_name}' found, setting up inlet...")
    print(f"Connected to {inlet.info().name()} from {inlet.info().hostname()}.")

    info = StreamInfo('RRinterval', 'ExciteOMeter', 1, 10, 'float32', 'rrStream')
    outlet = StreamOutlet(info)

    rr_intervals = []
    times = []
    sdnn_values = []
    rmssd_values = []

    try:
        while True:
            sample, timestamp = inlet.pull_sample(timeout=5.0)
            if sample:
                rr_interval = sample[0]
                rr_intervals.append(rr_interval)
                times.append(timestamp)
                outlet.push_sample(sample)

                if len(rr_intervals) >= 50:
                    sdnn, rmssd, clean_rr_intervals = calculate_hrv_metrics(rr_intervals)
                    sdnn_values.append(sdnn)
                    rmssd_values.append(rmssd)
                    print(f"SDNN: {sdnn}, RMSSD: {rmssd}")

                    rr_intervals.clear()

                    # Plot every 10 seconds
                    if len(times) % 500 == 0:
                        plot_hrv_metrics(sdnn_values, rmssd_values)
            else:
                print("No new sample available.")
    except KeyboardInterrupt:
        print("Stream reading interrupted.")

    # Plot the final graph
    plot_hrv_metrics(times, sdnn_values, rmssd_values)


if __name__ == '__main__':
    main()
