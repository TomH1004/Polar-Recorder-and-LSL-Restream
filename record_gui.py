import threading
import csv
import time
import tkinter as tk
from tkinter import messagebox
from pylsl import StreamInlet, resolve_stream
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np


class LSLStreamRecorder:
    def __init__(self, master):
        self.master = master
        self.master.title("LSL Stream Recorder")

        self.recording = False
        self.marked_timestamps = []
        self.recording_event = threading.Event()
        self.stop_event = threading.Event()
        self.streams = [
            ('RawECG', 'ExciteOMeter', 130, 'int32'),
            ('HeartRate', 'ExciteOMeter', 10, 'float32'),
            ('RRinterval', 'ExciteOMeter', 10, 'float32')
        ]

        self.stream_threads = []
        self.inlets = []
        self.data_buffers = {stream[0]: [] for stream in self.streams}

        # UI Components
        self.start_button = tk.Button(master, text="Start Recording", command=self.toggle_recording)
        self.start_button.pack(pady=5)

        self.reconnect_button = tk.Button(master, text="Reconnect Streams", command=self.setup_threads)
        self.reconnect_button.pack(pady=5)

        self.mark_button = tk.Button(master, text="Mark Timestamp", command=self.mark_timestamp)
        self.mark_button.pack(pady=5)

        self.figure, self.axes = plt.subplots(len(self.streams), 1, figsize=(6, 5 * len(self.streams)))
        plt.subplots_adjust(hspace=0.5, left=0.15)

        for ax in self.axes:
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.set_facecolor('#f0f0f0')

        self.canvas = FigureCanvasTkAgg(self.figure, master=master)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(pady=10)

        self.update_plot()

    def setup_threads(self):
        # Resolve streams and create inlets
        self.stop_event.set()  # Stop any existing threads
        self.stop_event = threading.Event()  # Reset stop event
        self.stream_threads = []  # Clear existing threads
        self.inlets = []  # Clear existing inlets
        self.data_buffers = {stream[0]: [] for stream in self.streams}  # Clear data buffers

        for stream in self.streams:
            name, stream_type, _, _ = stream
            resolved_streams = resolve_stream('name', name)
            if resolved_streams:
                inlet = StreamInlet(resolved_streams[0])
                self.inlets.append((name, inlet))
                thread = threading.Thread(target=self.record_stream, args=(name, inlet))
                thread.daemon = True
                self.stream_threads.append(thread)
                thread.start()
            else:
                messagebox.showwarning("Stream Not Found", f"No stream named '{name}' found.")

    def toggle_recording(self):
        if not self.recording:
            self.recording = True
            self.recording_event.set()
            self.start_button.config(text="Stop Recording")
        else:
            self.recording = False
            self.recording_event.clear()
            self.start_button.config(text="Start Recording")
            self.save_marked_timestamps()

    def mark_timestamp(self):
        if self.recording:
            current_time = time.time()
            self.marked_timestamps.append(current_time)
            messagebox.showinfo("Timestamp Marked", f"Marked timestamp at {current_time}")
        else:
            messagebox.showwarning("Recording Not Active", "You can only mark timestamps while recording.")

    def record_stream(self, stream_name, inlet):
        csv_filename = f"{stream_name}_recording.csv"
        with open(csv_filename, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Timestamp', 'Value'])  # Write header
            while not self.stop_event.is_set():
                if self.recording_event.is_set():
                    sample, timestamp = inlet.pull_sample(timeout=1.0)
                    if sample:
                        value = sample[0]
                        self.data_buffers[stream_name].append(value)
                        csv_writer.writerow([timestamp, value])
                        csvfile.flush()
                time.sleep(0.05)

    def update_plot(self):
        # Update the graphs
        for idx, (stream_name, _, _, _) in enumerate(self.streams):
            data = self.data_buffers[stream_name]
            if len(data) > 100:
                data = data[-100:]  # Limit the buffer size for plotting
            else:
                data = np.pad(data, (100 - len(data), 0), 'constant', constant_values=(0,))
            self.axes[idx].clear()
            self.axes[idx].plot(data, color='b', linewidth=1.5)
            self.axes[idx].set_title(stream_name, fontsize=14)
            self.axes[idx].set_xlabel("Time", fontsize=12)
            self.axes[idx].set_ylabel("Value", fontsize=12)
            self.axes[idx].grid(True, linestyle='--', alpha=0.6)

        self.canvas.draw()
        self.master.after(100, self.update_plot)  # Update every 100 ms

    def save_marked_timestamps(self):
        marked_filename = f"marked_timestamps.csv"
        with open(marked_filename, 'w', newline='') as marked_file:
            marked_writer = csv.writer(marked_file)
            marked_writer.writerow(['Marked Timestamp'])
            for ts in self.marked_timestamps:
                marked_writer.writerow([ts])
        print(f"Marked timestamps saved to {marked_filename}")


if __name__ == "__main__":
    root = tk.Tk()
    app = LSLStreamRecorder(root)
    root.mainloop()
