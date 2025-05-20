"""
This script is a utility to discover and list available LabStreamingLayer (LSL)
streams on the local network.

It utilizes the `pylsl.resolve_streams()` function to find all currently active
LSL streams that are broadcasting data. For each discovered stream, it prints
detailed information, including:
- Stream name
- Stream type
- Number of channels
- Nominal sampling rate (in Hz)
- Data format (e.g., float32, int16)
- Source ID (a unique identifier for the stream source)

This utility is particularly helpful for verifying that expected LSL streams
(e.g., those initiated by `hr_stream.py`, `ecg_stream.py`, `rr_stream.py`, or
`stream_combined.py`) are indeed active and discoverable on the network before
attempting to connect to them with an LSL inlet in a client application.
It aids in troubleshooting LSL stream connectivity issues.
"""
from pylsl import resolve_streams

# Find and list all available LSL streams on the network
streams = resolve_streams()

for stream in streams:
    print(f"Stream name: {stream.name()}, Type: {stream.type()}, "
          f"Channel count: {stream.channel_count()}, Sampling rate: {stream.nominal_srate()}, "
          f"Data format: {stream.channel_format()}, Source ID: {stream.source_id()}")
