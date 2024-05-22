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
    info = StreamInfo('HR', 'HeartRate', 1, 0, 'float32', 'myuniqueid12345')
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