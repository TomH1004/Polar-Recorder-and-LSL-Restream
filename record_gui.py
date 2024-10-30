import threading
import csv
import time
import tkinter as tk
from tkinter import messagebox, ttk
from pylsl import StreamInlet, resolve_stream
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np


class LSLStreamRecorder:
    def __init__(self, master):
        self.master = master
        self.master.title("LSL Stream Recorder")
        self.master.geometry("600x900")  # Set initial window size to be wider

        # Make window scrollable
        self.main_frame = tk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.recording = False
        self.marked_timestamps = []
        self.recording_event = threading.Event()
        self.stop_event = threading.Event()
        self.streams = [
            ('HeartRate', 'ExciteOMeter', 10, 'float32'),
            ('RRinterval', 'ExciteOMeter', 10, 'float32'),
            ('RawECG', 'ExciteOMeter', 130, 'int32')
        ]

        self.stream_threads = []
        self.inlets = []
        self.data_buffers = {stream[0]: [] for stream in self.streams}

        # UI Components
        button_style = {"padx": 5, "pady": 2, "bg": "#f0f0f0", "font": ("Helvetica", 10), "relief": "raised"}
        checkbox_style = {"anchor": 'w', "font": ("Helvetica", 9)}

        self.connect_button = tk.Button(self.scrollable_frame, text="Connect to Device", command=self.connect_to_device, **button_style)
        self.connect_button.grid(row=0, column=0, pady=2, padx=5)

        self.start_button = tk.Button(self.scrollable_frame, text="Start Recording", state=tk.DISABLED, command=self.toggle_recording, **button_style)
        self.start_button.grid(row=1, column=0, pady=2, padx=5)

        self.mark_button = tk.Button(self.scrollable_frame, text="Mark Timestamp", state=tk.DISABLED, command=self.mark_timestamp, **button_style)
        self.mark_button.grid(row=2, column=0, pady=2, padx=5)

        self.stream_checkboxes = {}
        self.checkbox_frame = tk.Frame(self.scrollable_frame)
        self.checkbox_frame.grid(row=0, column=1, rowspan=3, pady=2, padx=5, sticky='n')
        for stream in self.streams:
            var = tk.BooleanVar()
            checkbox = tk.Checkbutton(self.checkbox_frame, text=stream[0], variable=var, **checkbox_style)
            checkbox.pack(anchor='w')
            self.stream_checkboxes[stream[0]] = var

        self.figure, self.axes = plt.subplots(len(self.streams), 1, figsize=(6, 3 * len(self.streams)))
        plt.subplots_adjust(hspace=0.5, left=0.15)

        for ax in self.axes:
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.set_facecolor('#f0f0f0')

        self.canvas_plot = FigureCanvasTkAgg(self.figure, master=self.scrollable_frame)
        self.canvas_widget = self.canvas_plot.get_tk_widget()
        self.canvas_widget.grid(row=3, column=0, columnspan=2, pady=5)

        self.update_plot()

    def connect_to_device(self):
        # Determine streams to connect
        self.stream_selection = []
        for stream_name, var in self.stream_checkboxes.items():
            if var.get():
                for stream in self.streams:
                    if stream[0] == stream_name:
                        self.stream_selection.append(stream)

        if not self.stream_selection:
            messagebox.showwarning("No Streams Selected", "Please select at least one stream to connect.")
            return

        self.setup_threads()

        # Update UI components
        self.connect_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.NORMAL)
        self.mark_button.config(state=tk.NORMAL)
        self.start_button.config(text="Start Recording")

    def setup_threads(self):
        # Resolve streams and create inlets
        self.stop_event.set()  # Stop any existing threads
        self.stop_event = threading.Event()  # Reset stop event
        self.stream_threads = []  # Clear existing threads
        self.inlets = []  # Clear existing inlets
        self.data_buffers = {stream[0]: [] for stream in self.streams}  # Clear data buffers

        for stream in self.stream_selection:
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

        self.canvas_plot.draw()
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
