from pylsl import resolve_streams

# Find and list all available LSL streams on the network
streams = resolve_streams()

for stream in streams:
    print(f"Stream name: {stream.name()}, Type: {stream.type()}, "
          f"Channel count: {stream.channel_count()}, Sampling rate: {stream.nominal_srate()}, "
          f"Data format: {stream.channel_format()}, Source ID: {stream.source_id()}")
