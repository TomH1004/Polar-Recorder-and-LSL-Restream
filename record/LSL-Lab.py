import threading
import csv
import time
import tkinter as tk
from tkinter import messagebox, ttk
from pylsl import StreamInlet, resolve_stream, local_clock
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import os


class LSLGui:
    def __init__(self, master):
        self.master = master
        self.master.title("LSL Recorder & Analyzer")
        self.master.geometry("2100x1050")
        self.master.configure(bg="#eaeaea")

        self.left_frame = tk.Frame(master, padx=10, pady=10, bg="#f0f0f0")
        self.right_frame = tk.Frame(master, padx=10, pady=10, bg="#ffffff")

        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.recorder = LSLStreamRecorder(self.left_frame)
        self.analyzer = LSLDataAnalyzer(self.right_frame)


class LSLStreamRecorder:
    def __init__(self, parent):
        self.parent = parent
        self.recording = False
        self.recording_event = threading.Event()
        self.stop_event = threading.Event()
        self.streams = [
            ('HeartRate', 'ExciteOMeter', 10, 'float32'),
            ('RRinterval', 'ExciteOMeter', 10, 'float32')
        ]
        self.inlets = {}
        self.data_buffers = {stream[0]: [] for stream in self.streams}
        self.marked_timestamps = []
        self.participant_folder = None

        self.setup_ui()

    def setup_ui(self):
        tk.Label(self.parent, text="LSL Stream Recorder", font=("Helvetica", 48, "bold"), bg="#f0f0f0").pack(pady=10)

        self.participant_id_label = tk.Label(self.parent, text="Participant ID:", bg="#f0f0f0")
        self.participant_id_label.pack()
        self.participant_id_entry = tk.Entry(self.parent, font=("Helvetica", 32))
        self.participant_id_entry.pack(pady=5)

        self.connect_button = tk.Button(self.parent, text="Connect", font=("Helvetica", 32),
                                        command=self.connect_to_device)
        self.connect_button.pack(pady=5, fill=tk.X)

        self.start_button = tk.Button(self.parent, text="Start Recording", font=("Helvetica", 32), state=tk.DISABLED,
                                      command=self.toggle_recording)
        self.start_button.pack(pady=5, fill=tk.X)

        self.mark_button = tk.Button(self.parent, text="Mark Timestamp", font=("Helvetica", 32), state=tk.DISABLED,
                                     command=self.mark_timestamp)
        self.mark_button.pack(pady=5, fill=tk.X)

        self.figure, self.ax1 = plt.subplots(figsize=(8, 6))
        self.ax2 = self.ax1.twinx()  # Create a second y-axis
        self.figure.suptitle("Live HR & RR Data", fontsize=28)

        self.canvas_plot = FigureCanvasTkAgg(self.figure, master=self.parent)
        self.canvas_widget = self.canvas_plot.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.update_plot()

    def connect_to_device(self):
        participant_id = self.participant_id_entry.get().strip()
        if not participant_id:
            messagebox.showwarning("Participant ID Missing", "Please enter a Participant ID.")
            return

        self.participant_folder = os.path.join("Participant_Data", f"Participant_{participant_id}")
        os.makedirs(self.participant_folder, exist_ok=True)

        # Resolve all available LSL streams
        available_streams = resolve_stream()

        for stream_name, stream_type, _, _ in self.streams:
            for stream in available_streams:
                inlet = StreamInlet(stream)
                stream_info = inlet.info()

                # Match both the type and name to ensure correctness
                if stream_info.type() == stream_type and stream_info.name() == stream_name:
                    self.inlets[stream_name] = inlet
                    break  # Stop searching once we find the correct stream

        if not self.inlets:
            messagebox.showerror("No Streams Found", "No matching LSL streams were found.")
            return

        self.start_button.config(state=tk.NORMAL)
        self.mark_button.config(state=tk.NORMAL)
        messagebox.showinfo("Connected", "Device connected successfully!")

    def toggle_recording(self):
        if not self.recording:
            self.recording = True
            self.recording_event.set()
            self.start_button.config(text="Stop Recording")
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        for stream_name in self.inlets.keys():
            thread = threading.Thread(target=self.record_stream, args=(stream_name,))
            thread.daemon = True
            thread.start()

    def stop_recording(self):
        self.recording = False
        self.recording_event.clear()
        self.start_button.config(text="Start Recording")
        self.save_marked_timestamps()

    def mark_timestamp(self):
        if self.recording:
            timestamp = local_clock()
            self.marked_timestamps.append(timestamp)
            messagebox.showinfo("Timestamp Marked", f"Marked timestamp at {timestamp}")
        else:
            messagebox.showwarning("Recording Not Active", "Start recording before marking timestamps.")

    def save_marked_timestamps(self):
        if not self.marked_timestamps:
            return

        marked_filename = os.path.join(self.participant_folder, "marked_timestamps.csv")
        with open(marked_filename, 'w', newline='') as marked_file:
            csv_writer = csv.writer(marked_file)
            csv_writer.writerow(['Timestamp'])
            csv_writer.writerows([[ts] for ts in self.marked_timestamps])

    def record_stream(self, stream_name):
        csv_filename = os.path.join(self.participant_folder, f"{stream_name}_recording.csv")
        with open(csv_filename, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Timestamp', 'Value'])

            while self.recording:
                sample, _ = self.inlets[stream_name].pull_sample(timeout=1.0)
                if sample:
                    value = sample[0]
                    timestamp = local_clock()
                    self.data_buffers[stream_name].append((timestamp, value))
                    csv_writer.writerow([timestamp, value])
                    csvfile.flush()
                time.sleep(0.001)

    def update_plot(self):
        self.ax1.clear()
        self.ax2.clear()
        has_hr_data = False
        has_rr_data = False

        if 'HeartRate' in self.data_buffers and self.data_buffers['HeartRate']:
            timestamps_hr, values_hr = zip(*self.data_buffers['HeartRate'])
            self.ax1.plot(timestamps_hr, values_hr, 'b-', label='Heart Rate', linewidth=1.5)
            self.ax1.set_ylabel('Heart Rate (bpm)', color='b', labelpad=15, va='center')  # Center label
            self.ax1.tick_params(axis='y', labelcolor='b')
            has_hr_data = True

        if 'RRinterval' in self.data_buffers and self.data_buffers['RRinterval']:
            timestamps_rr, values_rr = zip(*self.data_buffers['RRinterval'])
            self.ax2.plot(timestamps_rr, values_rr, 'r-', label='RR Interval', linewidth=1.5)

            # Move the RR Interval label to the right and center it properly
            self.ax2.set_ylabel('RR Interval (ms)', color='r', labelpad=15, ha='right', va='center')
            self.ax2.yaxis.set_label_position("right")  # Ensure label is on the right
            self.ax2.tick_params(axis='y', labelcolor='r')
            has_rr_data = True

        self.ax1.set_xlabel("Time (Last 100s)")
        self.ax1.grid(True, linestyle='--', alpha=0.6)

        # Only add legend if data exists
        if has_hr_data:
            self.ax1.legend(loc='upper left')
        if has_rr_data:
            self.ax2.legend(loc='upper right')

        self.canvas_plot.draw()
        self.parent.after(100, self.update_plot)


class LSLDataAnalyzer:
    def __init__(self, parent):
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        tk.Label(self.parent, text="LSL Data Analyzer", font=("Helvetica", 32, "bold"), bg="#ffffff").pack(pady=10)

        # Participant ID
        self.participant_id_label = tk.Label(self.parent, text="Participant ID:", bg="#ffffff")
        self.participant_id_label.pack()
        self.participant_id_entry = tk.Entry(self.parent, font=("Helvetica", 24))
        self.participant_id_entry.pack(pady=5)

        # Load Data Button
        self.load_button = tk.Button(self.parent, text="Load Data", font=("Helvetica", 24), command=self.load_data)
        self.load_button.pack(pady=5, fill=tk.X)

        # Results Display
        self.results_text = tk.Text(self.parent, wrap=tk.WORD, font=("Helvetica", 24), height=15)
        self.results_text.pack(pady=5, fill=tk.BOTH, expand=True)

    def load_data(self):
        self.results_text.delete(1.0, tk.END)

        participant_id = self.participant_id_entry.get().strip()
        if not participant_id:
            messagebox.showwarning("Participant ID Missing", "Please enter a Participant ID.")
            return

        participant_folder = os.path.join("Participant_Data", f"Participant_{participant_id}")
        if not os.path.exists(participant_folder):
            messagebox.showerror("Folder Not Found",
                                 f"The folder for Participant ID '{participant_id}' does not exist.")
            return

        # Laden der markierten Zeitstempel
        marked_timestamps = []
        marked_filename = os.path.join(participant_folder, "marked_timestamps.csv")
        if os.path.exists(marked_filename):
            with open(marked_filename, 'r') as marked_file:
                reader = csv.reader(marked_file)
                next(reader)  # Header überspringen
                marked_timestamps = [float(row[0]) for row in reader]

        # Laden der Daten
        streams = ["HeartRate", "RRinterval"]
        data_buffers = {}

        for stream in streams:
            csv_filename = os.path.join(participant_folder, f"{stream}_recording.csv")
            if os.path.exists(csv_filename):
                with open(csv_filename, 'r') as csvfile:
                    reader = csv.reader(csvfile)
                    next(reader)  # Header überspringen
                    data_buffers[stream] = [(float(row[0]), float(row[1])) for row in reader]
            else:
                data_buffers[stream] = []

        # Analysieren der Daten mit Episoden-Erkennung
        self.analyze_data(data_buffers, marked_timestamps)

    def analyze_data(self, data_buffers, marked_timestamps):
        self.results_text.delete(1.0, tk.END)
        streams = ["HeartRate", "RRinterval"]

        for stream in streams:
            data = data_buffers.get(stream, [])
            if not data:
                self.results_text.insert(tk.END, f"{stream} Data: No Data Available\n\n")
                continue

            # Segmentierung anhand von Pausen (wenn Timestamp-Differenz > 10 Sek.)
            segments = []
            current_segment = []
            for i in range(1, len(data)):
                timestamp_diff = data[i][0] - data[i - 1][0]
                if timestamp_diff > 10:  # Wenn mehr als 10 Sek. Pause, dann neue Episode
                    if current_segment:
                        segments.append(current_segment)
                        current_segment = []
                current_segment.append(data[i])

            if current_segment:
                segments.append(current_segment)

            # Analysieren der Segmente
            for idx, segment in enumerate(segments):
                if not segment:
                    continue

                timestamps, values = zip(*segment)
                values = np.array(values)

                # Grundlegende Statistiken
                mean_value = np.mean(values)
                median_value = np.median(values)
                min_value = np.min(values)
                max_value = np.max(values)
                std_dev = np.std(values)
                iqr_value = np.percentile(values, 75) - np.percentile(values, 25)
                duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0

                rmssd = None
                sdnn = None
                if stream == "RRinterval":
                    rr_diff = np.diff(values)
                    rmssd = np.sqrt(np.mean(rr_diff ** 2)) if len(rr_diff) > 0 else None
                    sdnn = np.std(values, ddof=1)

                self.results_text.insert(tk.END, f"Segment {idx + 1} ({stream} Data):\n")
                self.results_text.insert(tk.END, f"  Mean: {mean_value:.2f}\n")
                self.results_text.insert(tk.END, f"  Median: {median_value:.2f}\n")
                self.results_text.insert(tk.END, f"  Min: {min_value:.2f}\n")
                self.results_text.insert(tk.END, f"  Max: {max_value:.2f}\n")
                self.results_text.insert(tk.END, f"  Variability (Standard Deviation): {std_dev:.2f}\n")
                self.results_text.insert(tk.END, f"  Interquartile Range (IQR): {iqr_value:.2f}\n")
                if rmssd is not None:
                    self.results_text.insert(tk.END, f"  RMSSD: {rmssd:.2f}\n")
                if sdnn is not None:
                    self.results_text.insert(tk.END, f"  SDNN: {sdnn:.2f}\n")
                self.results_text.insert(tk.END, f"  Duration: {duration:.2f} seconds\n\n")

                # Analyse zwischen markierten Zeitpunkten innerhalb dieses Segments
                if marked_timestamps:
                    segment_episodes = []
                    segment_boundaries = [ts for ts in marked_timestamps if timestamps[0] <= ts <= timestamps[-1]]
                    all_boundaries = [timestamps[0]] + segment_boundaries + [timestamps[-1]]

                    for i in range(len(all_boundaries) - 1):
                        start_ts = all_boundaries[i]
                        end_ts = all_boundaries[i + 1]
                        episode_values = [value for ts, value in segment if start_ts <= ts <= end_ts]
                        if episode_values:
                            mean_episode = np.mean(episode_values)
                            median_episode = np.median(episode_values)
                            min_episode = np.min(episode_values)
                            max_episode = np.max(episode_values)
                            std_dev_episode = np.std(episode_values)
                            iqr_episode = np.percentile(episode_values, 75) - np.percentile(episode_values, 25)
                            duration_episode = end_ts - start_ts
                            rmssd_episode = None
                            sdnn_episode = None
                            if stream == "RRinterval" and len(episode_values) > 1:
                                rr_diff = np.diff(episode_values)
                                rmssd_episode = np.sqrt(np.mean(rr_diff ** 2)) if len(rr_diff) > 0 else None
                                sdnn_episode = np.std(episode_values, ddof=1)

                            segment_episodes.append((mean_episode, median_episode, min_episode, max_episode,
                                                     std_dev_episode, iqr_episode, duration_episode, rmssd_episode))

                    # Ergebnisse der Episoden ausgeben
                    for i, (mean_episode, median_episode, min_episode, max_episode, std_dev_episode, iqr_episode,
                            duration_episode, rmssd_episode) in enumerate(segment_episodes):
                        self.results_text.insert(tk.END, f"    Episode {i + 1}:\n")
                        self.results_text.insert(tk.END, f"      Mean: {mean_episode:.2f}\n")
                        self.results_text.insert(tk.END, f"      Median: {median_episode:.2f}\n")
                        self.results_text.insert(tk.END, f"      Min: {min_episode:.2f}\n")
                        self.results_text.insert(tk.END, f"      Max: {max_episode:.2f}\n")
                        self.results_text.insert(tk.END,
                                                 f"      Variability (Standard Deviation): {std_dev_episode:.2f}\n")
                        self.results_text.insert(tk.END, f"      Interquartile Range (IQR): {iqr_episode:.2f}\n")
                        if rmssd_episode is not None:
                            self.results_text.insert(tk.END, f"      RMSSD: {rmssd_episode:.2f}\n")
                        if sdnn_episode is not None:
                            self.results_text.insert(tk.END, f"      SDNN: {sdnn_episode:.2f}\n")
                        self.results_text.insert(tk.END, f"      Duration: {duration_episode:.2f} seconds\n\n")

                else:
                    self.results_text.insert(tk.END, "  No Marked Timestamps Available for This Segment\n\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = LSLGui(root)
    root.mainloop()