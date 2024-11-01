import tkinter as tk
from tkinter import messagebox, ttk
import os
import csv
import numpy as np


class LSLDataAnalyzer:
    def __init__(self, master):
        self.master = master
        self.master.title("LSL Data Analyzer")
        self.master.geometry("500x600")

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

        # Participant ID Field
        self.participant_id_label = tk.Label(self.scrollable_frame, text="Participant ID:", font=("Helvetica", 10))
        self.participant_id_label.grid(row=0, column=0, pady=2, padx=5, sticky='e')
        self.participant_id_entry = tk.Entry(self.scrollable_frame, font=("Helvetica", 10))
        self.participant_id_entry.grid(row=0, column=1, pady=2, padx=5, sticky='w')

        # Load Data Button
        self.load_button = tk.Button(self.scrollable_frame, text="Load and Analyze Data", command=self.load_data, padx=5, pady=2, bg="#f0f0f0", font=("Helvetica", 10), relief="raised")
        self.load_button.grid(row=1, column=0, columnspan=2, pady=5)

        # Analysis Results Text Widget
        self.results_text = tk.Text(self.scrollable_frame, wrap=tk.WORD, width=70, height=30, font=("Helvetica", 10))
        self.results_text.grid(row=2, column=0, columnspan=2, pady=5, padx=5)

    def load_data(self):
        participant_id = self.participant_id_entry.get().strip()
        if not participant_id:
            messagebox.showwarning("Participant ID Missing", "Please enter a Participant ID.")
            return

        # Load data from participant folder
        participant_folder = f"Participant_{participant_id}"
        if not os.path.exists(participant_folder):
            messagebox.showerror("Folder Not Found", f"The folder for Participant ID '{participant_id}' does not exist.")
            return

        # Load marked timestamps
        marked_timestamps = []
        marked_filename = os.path.join(participant_folder, "marked_timestamps.csv")
        if os.path.exists(marked_filename):
            with open(marked_filename, 'r') as marked_file:
                reader = csv.reader(marked_file)
                next(reader)  # Skip header
                marked_timestamps = [float(row[0]) for row in reader]

        # Load and analyze each stream
        streams = ["HeartRate", "RRinterval", "RawECG"]
        data_buffers = {}
        for stream in streams:
            csv_filename = os.path.join(participant_folder, f"{stream}_recording.csv")
            if os.path.exists(csv_filename):
                with open(csv_filename, 'r') as csvfile:
                    reader = csv.reader(csvfile)
                    next(reader)  # Skip header
                    data_buffers[stream] = [(float(row[0]), float(row[1])) for row in reader]
            else:
                data_buffers[stream] = []

        # Analyze data
        self.analyze_data(data_buffers, marked_timestamps)

    def analyze_data(self, data_buffers, marked_timestamps):
        self.results_text.delete(1.0, tk.END)
        streams = ["HeartRate", "RRinterval"]

        for stream in streams:
            data = data_buffers.get(stream, [])
            if not data:
                self.results_text.insert(tk.END, f"{stream} Data: No Data Available\n\n")
                continue

            timestamps, values = zip(*data)
            values = np.array(values)

            # Basic statistics
            mean_value = np.mean(values)
            min_value = np.min(values)
            max_value = np.max(values)
            median_value = np.median(values)
            std_dev = np.std(values)  # Variability
            iqr_value = np.percentile(values, 75) - np.percentile(values, 25)  # Interquartile Range (IQR)
            duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0

            # RMSSD Calculation (only for RRinterval)
            rmssd = None
            if stream == "RRinterval":
                rr_diff = np.diff(values)
                rmssd = np.sqrt(np.mean(rr_diff ** 2)) if len(rr_diff) > 0 else None

            self.results_text.insert(tk.END, f"{stream} Data:\n")
            self.results_text.insert(tk.END, f"  Mean: {mean_value:.2f}\n")
            self.results_text.insert(tk.END, f"  Median: {median_value:.2f}\n")
            self.results_text.insert(tk.END, f"  Min: {min_value:.2f}\n")
            self.results_text.insert(tk.END, f"  Max: {max_value:.2f}\n")
            self.results_text.insert(tk.END, f"  Variability (Standard Deviation): {std_dev:.2f}\n")
            self.results_text.insert(tk.END, f"  Interquartile Range (IQR): {iqr_value:.2f}\n")
            if rmssd is not None:
                self.results_text.insert(tk.END, f"  RMSSD: {rmssd:.2f}\n")
            self.results_text.insert(tk.END, f"  Duration: {duration:.2f} seconds\n")

            # Analyze data between marked timestamps if available
            if marked_timestamps:
                self.results_text.insert(tk.END, "  Episodes between Marked Timestamps:\n\n\n")
                episodes = []

                # Add start and end of recording as additional boundaries
                all_boundaries = [timestamps[0]] + marked_timestamps + [timestamps[-1]]

                for i in range(len(all_boundaries) - 1):
                    start_ts = all_boundaries[i]
                    end_ts = all_boundaries[i + 1]
                    episode_values = [value for ts, value in data if start_ts <= ts <= end_ts]
                    if episode_values:
                        mean_episode = np.mean(episode_values)
                        min_episode = np.min(episode_values)
                        max_episode = np.max(episode_values)
                        median_episode = np.median(episode_values)
                        std_dev_episode = np.std(episode_values)
                        iqr_episode = np.percentile(episode_values, 75) - np.percentile(episode_values, 25)
                        duration_episode = end_ts - start_ts
                        rmssd_episode = None
                        if stream == "RRinterval" and len(episode_values) > 1:
                            rr_diff = np.diff(episode_values)
                            rmssd_episode = np.sqrt(np.mean(rr_diff ** 2)) if len(rr_diff) > 0 else None

                        episodes.append((mean_episode, median_episode, min_episode, max_episode, std_dev_episode, iqr_episode, duration_episode, rmssd_episode))

                for i, (mean_episode, median_episode, min_episode, max_episode, std_dev_episode, iqr_episode, duration_episode, rmssd_episode) in enumerate(episodes):
                    self.results_text.insert(tk.END, f"    Episode {i + 1}:\n")
                    self.results_text.insert(tk.END, f"      Mean: {mean_episode:.2f}\n")
                    self.results_text.insert(tk.END, f"      Median: {median_episode:.2f}\n")
                    self.results_text.insert(tk.END, f"      Min: {min_episode:.2f}\n")
                    self.results_text.insert(tk.END, f"      Max: {max_episode:.2f}\n")
                    self.results_text.insert(tk.END, f"      Variability (Standard Deviation): {std_dev_episode:.2f}\n")
                    self.results_text.insert(tk.END, f"      Interquartile Range (IQR): {iqr_episode:.2f}\n")
                    if rmssd_episode is not None:
                        self.results_text.insert(tk.END, f"      RMSSD: {rmssd_episode:.2f}\n")
                    self.results_text.insert(tk.END, f"      Duration: {duration_episode:.2f} seconds\n\n")
                self.results_text.insert(tk.END, "\n")
            else:
                self.results_text.insert(tk.END, "  No Marked Timestamps Available\n\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = LSLDataAnalyzer(root)
    root.mainloop()
