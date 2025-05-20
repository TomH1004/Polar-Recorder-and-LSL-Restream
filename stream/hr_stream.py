"""
This script connects to a Polar H10 heart rate monitor and streams Heart Rate (HR)
data via LabStreamingLayer (LSL).

It establishes a Bluetooth Low Energy (BLE) connection to the Polar H10 device.
Once connected, it subscribes to the standard Bluetooth GATT Heart Rate service
and its associated characteristic (UUID `00002a37-0000-1000-8000-00805f9b34fb`)
to receive HR notifications.

An LSL stream outlet is created to broadcast the received HR data, which includes
the heart rate in Beats Per Minute (BPM) and corresponding LSL timestamps.
This makes the real-time HR data available on the local network, allowing other
LSL-compatible applications to subscribe to the stream for analysis, visualization,
or other processing tasks.
"""
from pylsl import StreamInlet, resolve_stream, StreamInfo, StreamOutlet


def main():
    stream_name = 'HeartRate'
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
    info = StreamInfo('HeartRate', 'ExciteOMeter', 1, 10, 'float32', 'hrStream')
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