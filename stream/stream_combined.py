"""
This script is designed to find existing LabStreamingLayer (LSL) streams on the
network and re-stream their data under new LSL stream configurations.

It does not connect directly to a Polar H10 device or any other hardware.
Instead, it takes a predefined list of existing LSL stream names and types
(e.g., 'RawECG', 'HeartRate', 'RRinterval') that it attempts to discover on the
local network.

For each successfully discovered LSL stream, this script creates a new LSL outlet.
This new outlet can have different stream parameters (e.g., a new name, type,
sampling frequency, or data format) than the original stream.

The script then continuously pulls data samples from the original (source) LSL
stream and pushes them to the newly created (destination) LSL stream. This
functionality can be useful for several purposes, such as:
- Aggregating data from multiple LSL streams into a single, combined stream (though
  this specific script creates separate new streams for each source).
- Changing the LSL properties of an existing stream (e.g., renaming it, altering
  its reported sampling rate, or changing its data type).
- Making existing LSL streams available under different identifiers or configurations
  for compatibility with specific LSL client applications.

The script utilizes Python's threading capabilities to handle multiple re-streaming
operations concurrently, allowing it to manage several source-to-destination
LSL stream pairs simultaneously.
"""
import threading
from pylsl import StreamInlet, resolve_stream, StreamInfo, StreamOutlet

def restream(stream_name, stream_type, new_stream_name, new_stream_type, new_stream_frequency, new_stream_format):
    print(f"Attempting to resolve the stream '{stream_name}' of type '{stream_type}'...")
    streams = resolve_stream('name', stream_name)

    if not streams:
        print(f"No streams named '{stream_name}' of type '{stream_type}' found.")
        return

    inlet = StreamInlet(streams[0])
    print(f"Stream '{stream_name}' found, setting up inlet...")
    print(f"Connected to {inlet.info().name()} from {inlet.info().hostname()}.")

    # Create a new stream to send data forward
    info = StreamInfo(new_stream_name, new_stream_type, 1, new_stream_frequency, new_stream_format, f'{new_stream_name}Stream')
    outlet = StreamOutlet(info)

    try:
        print(f"{new_stream_name} Stream is active.")
        while True:
            sample, timestamp = inlet.pull_sample(timeout=5.0)
            if sample:
                # Forward the sample to the new stream
                outlet.push_sample(sample)
            else:
                print(f"No new sample available for {stream_name}.")
    except KeyboardInterrupt:
        print(f"Stream reading for {stream_name} interrupted.")

def main():
    streams = [
        ('RawECG', 'ExciteOMeter', 'RawECG', 'ExciteOMeter', 130, 'int32'),
        ('HeartRate', 'ExciteOMeter', 'HeartRate', 'ExciteOMeter', 10, 'float32'),
        ('RRinterval', 'ExciteOMeter', 'RRinterval', 'ExciteOMeter', 10, 'float32')
    ]

    threads = []
    for stream in streams:
        thread = threading.Thread(target=restream, args=stream)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == '__main__':
    main()
