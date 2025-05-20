"""
This script connects to a Polar H10 heart rate monitor and streams RR interval
data (time between heartbeats) via LabStreamingLayer (LSL).

It establishes a Bluetooth Low Energy (BLE) connection to the Polar H10 device.
RR intervals are typically derived from the standard Bluetooth GATT Heart Rate
service notifications, which can include RR interval data alongside heart rate.
Alternatively, RR intervals could be processed from the PMD (Polar Measurement Data)
ECG data stream, though the HR service is the more direct source.

An LSL stream outlet is created to broadcast the RR interval data, which is
typically provided in milliseconds (ms), along with corresponding LSL timestamps.
This makes the real-time RR interval data available on the local network,
allowing other LSL-compatible applications to subscribe to the stream for purposes
such as Heart Rate Variability (HRV) analysis.
"""
from pylsl import StreamInlet, resolve_stream, StreamInfo, StreamOutlet


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

    # Create a new stream to send data forward
    info = StreamInfo('RRinterval', 'ExciteOMeter', 1, 10, 'float32', 'rrStream')
    outlet = StreamOutlet(info)

    try:
        while True:
            sample, timestamp = inlet.pull_sample(timeout=5.0)
            if sample:
                print(f"Timestamp: {timestamp}, Sample: {sample}")
                # Forward the sample to the new stream
                outlet.push_sample(sample)
            else:
                print("No new sample available.")
    except KeyboardInterrupt:
        print("Stream reading interrupted.")


if __name__ == '__main__':
    main()