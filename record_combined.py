import threading
import csv
import os
import time
from pylsl import StreamInlet, resolve_stream, StreamInfo, StreamOutlet
import keyboard

def restream(stream_name, stream_type, new_stream_name, new_stream_type, new_stream_frequency, new_stream_format, participant_id, recording_event):
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

    # Create CSV file for this stream
    csv_filename = f"{participant_id}_{new_stream_name}.csv"
    with open(csv_filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Timestamp', 'Value'])  # Write header

        try:
            print(f"{new_stream_name} Stream is active.")
            while True:
                if keyboard.is_pressed('q'):
                    print(f"Quitting {new_stream_name} stream.")
                    break

                if recording_event.is_set():
                    sample, timestamp = inlet.pull_sample(timeout=5.0)
                    if sample:
                        # Forward the sample to the new stream
                        outlet.push_sample(sample)
                        # Write to CSV
                        csv_writer.writerow([timestamp, sample[0]])
                        csvfile.flush()
                    else:
                        print(f"No new sample available for {stream_name}.")
                else:
                    time.sleep(0.1)

        except KeyboardInterrupt:
            print(f"Stream reading for {stream_name} interrupted.")

def main():
    participant_id = input("Enter participant ID: ")
    
    streams = [
        ('RawECG', 'ExciteOMeter', 'RawECG', 'ExciteOMeter', 130, 'int32'),
        ('HeartRate', 'ExciteOMeter', 'HeartRate', 'ExciteOMeter', 10, 'float32'),
        ('RRinterval', 'ExciteOMeter', 'RRinterval', 'ExciteOMeter', 10, 'float32')
    ]

    recording_event = threading.Event()
    threads = []
    for stream in streams:
        thread = threading.Thread(target=restream, args=(*stream, participant_id, recording_event))
        threads.append(thread)
        thread.start()

    print("Press 'r' to start/stop recording, 'q' to quit.")
    try:
        while True:
            if keyboard.is_pressed('r'):
                if recording_event.is_set():
                    recording_event.clear()
                    print("Recording stopped.")
                else:
                    recording_event.set()
                    print("Recording started.")
                time.sleep(0.5)  # Debounce
            elif keyboard.is_pressed('q'):
                print("Quitting...")
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

    for thread in threads:
        thread.join()

if __name__ == '__main__':
    main()
