import threading
import csv
import time
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import os
import asyncio
import struct
import sys
from datetime import datetime
from bleak import BleakClient, BleakScanner
from pylsl import local_clock, StreamInfo, StreamOutlet

# Polar H10 UUIDs
HEART_RATE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
HEART_RATE_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
PMD_SERVICE = "FB005C80-02E7-F387-1CAD-8ACD2D8DF0C8"
PMD_CONTROL = "FB005C81-02E7-F387-1CAD-8ACD2D8DF0C8"
PMD_DATA = "FB005C82-02E7-F387-1CAD-8ACD2D8DF0C8"
BATTERY_SERVICE = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"

# Client Configuration Descriptor UUID (for enabling notifications)
CLIENT_CHAR_CONFIG = "00002902-0000-1000-8000-00805f9b34fb"

# PMD Control Commands
PMD_COMMAND = bytearray([0x01, 0x00, 0x00, 0x01, 0x82, 0x00, 0x01, 0x01, 0x0E, 0x00])

# Theme colors
DARK_BG = "#1E1E2E"  # Dark background
DARKER_BG = "#181825"  # Darker background for contrast
ACCENT_COLOR = "#89B4FA"  # Accent color for highlights
TEXT_COLOR = "#CDD6F4"  # Main text color
SECONDARY_TEXT = "#A6ADC8"  # Secondary text color
SUCCESS_COLOR = "#A6E3A1"  # Success color
WARNING_COLOR = "#F9E2AF"  # Warning color
ERROR_COLOR = "#F38BA8"  # Error color
BORDER_COLOR = "#313244"  # Border color

class LSLGui:
    def __init__(self, master):
        self.master = master
        self.master.title("Polar H10 Recorder & Analyzer")
        self.master.geometry("2100x1050")
        self.master.configure(bg=DARK_BG)
        
        # Configure the theme
        self.configure_theme()
        
        # Create a main container with padding
        self.main_container = tk.Frame(master, bg=DARK_BG, padx=20, pady=20)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create a header with app title
        self.header = tk.Frame(self.main_container, bg=DARK_BG, pady=10)
        self.header.pack(fill=tk.X)
        
        self.title_label = tk.Label(
            self.header, 
            text="POLAR H10 RECORDER & ANALYZER", 
            font=("Segoe UI", 24, "bold"),
            bg=DARK_BG,
            fg=ACCENT_COLOR
        )
        self.title_label.pack()
        
        self.subtitle_label = tk.Label(
            self.header,
            text="Scientific Data Acquisition System",
            font=("Segoe UI", 12),
            bg=DARK_BG,
            fg=SECONDARY_TEXT
        )
        self.subtitle_label.pack(pady=(0, 10))
        
        # Separator
        self.separator = ttk.Separator(self.main_container, orient='horizontal')
        self.separator.pack(fill=tk.X, pady=10)

        # Set up the main frames with modern styling
        self.content_frame = tk.Frame(self.main_container, bg=DARK_BG)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.left_frame = tk.Frame(self.content_frame, bg=DARKER_BG, padx=15, pady=15, 
                                  highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.right_frame = tk.Frame(self.content_frame, bg=DARKER_BG, padx=15, pady=15,
                                   highlightbackground=BORDER_COLOR, highlightthickness=1)

        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create the recorder and analyzer components
        self.recorder = PolarStreamRecorder(self.left_frame)
        self.analyzer = LSLDataAnalyzer(self.right_frame)
        
        # Set up window close handler
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def configure_theme(self):
        """Configure the ttk theme for a modern look"""
        style = ttk.Style()
        
        # Configure TButton style
        style.configure(
            "TButton",
            background=DARKER_BG,
            foreground=TEXT_COLOR,
            borderwidth=0,
            focusthickness=3,
            focuscolor=ACCENT_COLOR,
            padding=(10, 5)
        )
        
        # Configure TCombobox style
        style.configure(
            "TCombobox",
            background=DARKER_BG,
            fieldbackground=DARKER_BG,
            foreground=TEXT_COLOR,
            arrowcolor=ACCENT_COLOR,
            borderwidth=1,
            padding=5
        )
        
        # Configure TEntry style
        style.configure(
            "TEntry",
            fieldbackground=DARKER_BG,
            foreground=TEXT_COLOR,
            borderwidth=1,
            padding=5
        )
        
        # Configure TScrollbar style
        style.configure(
            "TScrollbar",
            background=DARKER_BG,
            troughcolor=DARK_BG,
            borderwidth=0,
            arrowsize=13
        )
        
    def on_closing(self):
        """Handle window closing event"""
        try:
            # Disconnect from device if connected
            if hasattr(self.recorder, 'connected') and self.recorder.connected:
                self.recorder.disconnect_from_device()
                
            # Wait a moment for disconnection to complete
            time.sleep(0.5)
        except Exception as e:
            print(f"Error during shutdown: {str(e)}")
        finally:
            # Destroy the window
            self.master.destroy()


class PolarStreamRecorder:
    def __init__(self, parent):
        self.parent = parent
        self.recording = False
        self.recording_event = threading.Event()
        self.data_received = False  # Flag to track if data is being received
        self.stop_event = threading.Event()
        self.recording_start_time = None  # Track when recording started
        self.connected = False
        self.client = None
        self.device_address = None
        self.data_buffers = {
            'HeartRate': [],
            'RRinterval': []
        }
        self.marked_timestamps = []
        self.intervals = []  # Store completed intervals as (start, end) pairs
        self.current_interval_start = None  # Track if we're in the middle of creating an interval
        self.participant_folder = None
        self.current_participant_id = None  # Track current participant ID
        self.loop = asyncio.new_event_loop()
        self.plot_update_scheduled = False  # Flag to track if plot updates are scheduled
        
        # LSL streaming
        self.hr_outlet = None
        self.rr_outlet = None

        # Create a status label
        self.status_var = tk.StringVar()
        self.status_var.set("Status: Not connected")



        self.setup_ui()



    def setup_ui(self):
        # Section title with icon-like prefix
        title_frame = tk.Frame(self.parent, bg=DARKER_BG)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        section_title = tk.Label(
            title_frame, 
            text="◉ RECORDING MODULE", 
            font=("Segoe UI", 16, "bold"), 
            fg=ACCENT_COLOR, 
            bg=DARKER_BG,
            anchor="w"
        )
        section_title.pack(fill=tk.X)

        # Participant ID section with modern styling
        participant_frame = tk.Frame(self.parent, bg=DARKER_BG, pady=10)
        participant_frame.pack(fill=tk.X)
        
        self.participant_id_label = tk.Label(
            participant_frame, 
            text="PARTICIPANT ID", 
            font=("Segoe UI", 10), 
            bg=DARKER_BG, 
            fg=SECONDARY_TEXT,
            anchor="w"
        )
        self.participant_id_label.pack(fill=tk.X)
        
        # Entry and button container
        id_input_frame = tk.Frame(participant_frame, bg=DARKER_BG)
        id_input_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.participant_id_entry = tk.Entry(
            id_input_frame, 
            font=("Segoe UI", 14),
            bg=DARK_BG,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,  # Cursor color
            relief=tk.FLAT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1
        )
        self.participant_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Bind Enter key to set participant ID
        self.participant_id_entry.bind('<Return>', lambda event: self.set_participant_id())
        
        self.set_id_button = tk.Button(
            id_input_frame, 
            text="SET ID", 
            font=("Segoe UI", 10, "bold"),
            bg=ACCENT_COLOR,
            fg=DARKER_BG,
            activebackground=DARK_BG,
            activeforeground=ACCENT_COLOR,
            relief=tk.FLAT,
            padx=15,
            pady=5,
            command=self.set_participant_id
        )
        self.set_id_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Current session indicator
        self.session_status_label = tk.Label(
            participant_frame,
            text="No active session",
            font=("Segoe UI", 9, "italic"),
            bg=DARKER_BG,
            fg=SECONDARY_TEXT,
            anchor="w"
        )
        self.session_status_label.pack(fill=tk.X, pady=(5, 0))

        # Device selection frame with modern styling
        self.device_frame = tk.Frame(self.parent, bg=DARKER_BG, pady=10)
        self.device_frame.pack(fill=tk.X)

        self.device_label = tk.Label(
            self.device_frame, 
            text="POLAR DEVICE", 
            font=("Segoe UI", 10), 
            bg=DARKER_BG, 
            fg=SECONDARY_TEXT,
            anchor="w"
        )
        self.device_label.pack(fill=tk.X)

        device_selection_frame = tk.Frame(self.device_frame, bg=DARKER_BG)
        device_selection_frame.pack(fill=tk.X)
        
        self.device_var = tk.StringVar()
        self.device_dropdown = ttk.Combobox(
            device_selection_frame, 
            textvariable=self.device_var, 
            state="readonly", 
            font=("Segoe UI", 12), 
            width=30
        )
        self.device_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.scan_button = tk.Button(
            device_selection_frame, 
            text="SCAN", 
            font=("Segoe UI", 10, "bold"),
            bg=ACCENT_COLOR,
            fg=DARKER_BG,
            activebackground=DARK_BG,
            activeforeground=ACCENT_COLOR,
            relief=tk.FLAT,
            padx=15,
            pady=5,
            command=self.scan_devices
        )
        self.scan_button.pack(side=tk.RIGHT, padx=(10, 0))

        # Action buttons with modern styling
        button_frame = tk.Frame(self.parent, bg=DARKER_BG, pady=10)
        button_frame.pack(fill=tk.X)
        
        self.connect_button = tk.Button(
            button_frame, 
            text="CONNECT", 
            font=("Segoe UI", 12, "bold"),
            bg=ACCENT_COLOR,
            fg=DARKER_BG,
            activebackground=DARK_BG,
            activeforeground=ACCENT_COLOR,
            relief=tk.FLAT,
            padx=20,
            pady=10,
            command=self.connect_to_device
        )
        self.connect_button.pack(fill=tk.X, pady=5)

        self.start_button = tk.Button(
            button_frame, 
            text="START RECORDING", 
            font=("Segoe UI", 12, "bold"),
            bg=DARK_BG,
            fg=TEXT_COLOR,
            activebackground=DARKER_BG,
            activeforeground=TEXT_COLOR,
            relief=tk.FLAT,
            padx=20,
            pady=10,
            state=tk.DISABLED,
            command=self.toggle_recording
        )
        self.start_button.pack(fill=tk.X, pady=5)

        self.mark_button = tk.Button(
            button_frame, 
            text="MARK TIMESTAMP", 
            font=("Segoe UI", 12, "bold"),
            bg=DARK_BG,
            fg=TEXT_COLOR,
            activebackground=DARKER_BG,
            activeforeground=TEXT_COLOR,
            relief=tk.FLAT,
            padx=20,
            pady=10,
            state=tk.DISABLED,
            command=self.mark_timestamp
        )
        self.mark_button.pack(fill=tk.X, pady=5)

        # Interval buttons
        interval_frame = tk.Frame(button_frame, bg=DARKER_BG)
        interval_frame.pack(fill=tk.X, pady=5)

        self.start_interval_button = tk.Button(
            interval_frame, 
            text="START INTERVAL", 
            font=("Segoe UI", 10, "bold"),
            bg=DARK_BG,
            fg=TEXT_COLOR,
            activebackground=DARKER_BG,
            activeforeground=TEXT_COLOR,
            relief=tk.FLAT,
            padx=15,
            pady=8,
            state=tk.DISABLED,
            command=self.start_interval
        )
        self.start_interval_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.end_interval_button = tk.Button(
            interval_frame, 
            text="END INTERVAL", 
            font=("Segoe UI", 10, "bold"),
            bg=DARK_BG,
            fg=TEXT_COLOR,
            activebackground=DARKER_BG,
            activeforeground=TEXT_COLOR,
            relief=tk.FLAT,
            padx=15,
            pady=8,
            state=tk.DISABLED,
            command=self.end_interval
        )
        self.end_interval_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Status indicator with modern styling
        status_frame = tk.Frame(self.parent, bg=DARKER_BG, pady=5)
        status_frame.pack(fill=tk.X)
        
        self.status_label = tk.Label(
            status_frame, 
            textvariable=self.status_var, 
            font=("Segoe UI", 10), 
            bg=DARKER_BG,
            fg=SECONDARY_TEXT,
            anchor="w"
        )
        self.status_label.pack(fill=tk.X)



        # Plot with dark theme
        plt.style.use('dark_background')
        self.figure, self.ax1 = plt.subplots(figsize=(8, 4))
        self.figure.patch.set_facecolor(DARKER_BG)
        
        self.ax1.set_facecolor(DARK_BG)
        self.ax1.tick_params(colors=SECONDARY_TEXT)
        self.ax1.spines['bottom'].set_color(BORDER_COLOR)
        self.ax1.spines['top'].set_color(BORDER_COLOR) 
        self.ax1.spines['right'].set_color(BORDER_COLOR)
        self.ax1.spines['left'].set_color(BORDER_COLOR)
        
        self.ax2 = self.ax1.twinx()  # Create a second y-axis
        self.ax2.tick_params(colors=SECONDARY_TEXT)
        self.ax2.spines['bottom'].set_color(BORDER_COLOR)
        self.ax2.spines['top'].set_color(BORDER_COLOR) 
        self.ax2.spines['right'].set_color(BORDER_COLOR)
        self.ax2.spines['left'].set_color(BORDER_COLOR)
        
        self.figure.suptitle("Live HR & RR Data", fontsize=14, color=TEXT_COLOR)
        
        # Add a grid with low opacity
        self.ax1.grid(True, linestyle='--', alpha=0.2)

        self.canvas_plot = FigureCanvasTkAgg(self.figure, master=self.parent)
        self.canvas_widget = self.canvas_plot.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.update_plot()

    def scan_devices(self):
        self.scan_button.config(text="Scanning...", state=tk.DISABLED)
        threading.Thread(target=self._scan_devices_thread, daemon=True).start()

    def _scan_devices_thread(self):
        try:
            devices = self.loop.run_until_complete(self._scan_for_polar_devices())
            self.device_dropdown['values'] = devices
            if devices:
                self.device_dropdown.current(0)
            messagebox.showinfo("Scan Complete", f"Found {len(devices)} Polar devices")
        except Exception as e:
            messagebox.showerror("Scan Error", f"Error scanning for devices: {str(e)}")
        finally:
            self.scan_button.config(text="Scan", state=tk.NORMAL)

    async def _scan_for_polar_devices(self):
        devices = []
        scanner = BleakScanner()
        discovered_devices = await scanner.discover(timeout=5.0)

        for device in discovered_devices:
            if device.name and ("Polar" in device.name or "polar" in device.name):
                devices.append(f"{device.name} ({device.address})")

        return devices

    def set_participant_id(self):
        """Set or change the participant ID and start a new session"""
        new_id = self.participant_id_entry.get().strip()
        
        if not new_id:
            messagebox.showwarning("Invalid ID", "Please enter a valid Participant ID.")
            return
            
        # Check if this is the same as current ID
        if new_id == self.current_participant_id:
            return
            
        # Check if recording is active
        if self.recording:
            response = messagebox.askyesnocancel(
                "Recording in Progress", 
                f"A recording is currently active for participant '{self.current_participant_id}'.\n\n"
                f"Do you want to:\n"
                f"• Yes: Stop current recording and start new session for '{new_id}'\n"
                f"• No: Continue current recording\n"
                f"• Cancel: Abort changing participant ID"
            )
            
            if response is None:  # Cancel
                # Reset entry to current ID
                if self.current_participant_id:
                    self.participant_id_entry.delete(0, tk.END)
                    self.participant_id_entry.insert(0, self.current_participant_id)
                return
            elif response:  # Yes - stop recording and start new session
                print(f"Stopping current recording for participant '{self.current_participant_id}' and starting new session for '{new_id}'")
                self.stop_recording()
                # Wait a moment for recording to fully stop, then check for existing data
                self.parent.after(100, lambda: self._check_existing_data_and_start_session(new_id))
            else:  # No - continue current recording
                # Reset entry to current ID
                if self.current_participant_id:
                    self.participant_id_entry.delete(0, tk.END)
                    self.participant_id_entry.insert(0, self.current_participant_id)
                return
        else:
            # No recording active, check for existing data and start new session
            self._check_existing_data_and_start_session(new_id)
            
    def _check_existing_data_and_start_session(self, participant_id):
        """Check if participant data already exists and handle accordingly"""
        participant_folder = os.path.join("Participant_Data", f"Participant_{participant_id}")
        
        # Check if participant folder exists and contains data files
        existing_files = self._get_existing_recording_files(participant_folder)
        
        if existing_files:
            # Show detailed information about existing files
            file_info = self._get_file_info(existing_files)
            
            response = messagebox.askyesnocancel(
                "Existing Data Found",
                f"Participant '{participant_id}' already has recorded data:\n\n"
                f"{file_info}\n\n"
                f"Do you want to:\n"
                f"• Yes: Overwrite existing data (PERMANENT DELETION)\n"
                f"• No: Enter a different participant ID\n"
                f"• Cancel: Keep current session"
            )
            
            if response is None:  # Cancel
                # Reset entry to current ID
                if self.current_participant_id:
                    self.participant_id_entry.delete(0, tk.END)
                    self.participant_id_entry.insert(0, self.current_participant_id)
                else:
                    self.participant_id_entry.delete(0, tk.END)
                return
            elif response:  # Yes - overwrite existing data
                response_confirm = messagebox.askyesno(
                    "Confirm Data Overwrite",
                    f"⚠️ WARNING ⚠️\n\n"
                    f"This will PERMANENTLY DELETE all existing data for participant '{participant_id}'.\n\n"
                    f"This action CANNOT be undone!\n\n"
                    f"Are you absolutely sure you want to proceed?"
                )
                
                if response_confirm:
                    try:
                        # Delete existing data files
                        self._delete_existing_data(participant_folder)
                        print(f"Deleted existing data for participant '{participant_id}'")
                        self.start_new_session(participant_id)
                    except Exception as e:
                        messagebox.showerror("Error Deleting Data", 
                                           f"Failed to delete existing data:\n{str(e)}")
                        # Reset entry
                        if self.current_participant_id:
                            self.participant_id_entry.delete(0, tk.END)
                            self.participant_id_entry.insert(0, self.current_participant_id)
                        else:
                            self.participant_id_entry.delete(0, tk.END)
                else:
                    # User changed their mind, reset entry
                    if self.current_participant_id:
                        self.participant_id_entry.delete(0, tk.END)
                        self.participant_id_entry.insert(0, self.current_participant_id)
                    else:
                        self.participant_id_entry.delete(0, tk.END)
            else:  # No - enter different ID
                # Clear entry to let user enter new ID
                self.participant_id_entry.delete(0, tk.END)
                self.participant_id_entry.focus_set()
                messagebox.showinfo("Enter New ID", "Please enter a different participant ID.")
        else:
            # No existing data, proceed with new session
            self.start_new_session(participant_id)
            
    def _get_existing_recording_files(self, participant_folder):
        """Get list of existing recording files for a participant"""
        if not os.path.exists(participant_folder):
            return []
            
        recording_files = []
        potential_files = [
            "HeartRate_recording.csv",
            "RRinterval_recording.csv", 
            "marked_timestamps.csv",
            "intervals.csv"
        ]
        
        for filename in potential_files:
            file_path = os.path.join(participant_folder, filename)
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                recording_files.append(file_path)
                
        return recording_files
        
    def _get_file_info(self, file_paths):
        """Get readable information about existing files"""
        if not file_paths:
            return "No files found"
            
        info_lines = []
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Get creation/modification time
            mod_time = os.path.getmtime(file_path)
            mod_date = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
            
            # Count lines for CSV files
            if filename.endswith('.csv'):
                try:
                    with open(file_path, 'r') as f:
                        line_count = sum(1 for line in f) - 1  # Subtract header
                    info_lines.append(f"• {filename}: {line_count} data points ({file_size} bytes, {mod_date})")
                except:
                    info_lines.append(f"• {filename}: {file_size} bytes ({mod_date})")
            else:
                info_lines.append(f"• {filename}: {file_size} bytes ({mod_date})")
                
        return "\n".join(info_lines)
        
    def _delete_existing_data(self, participant_folder):
        """Delete all existing data for a participant"""
        if not os.path.exists(participant_folder):
            return
            
        # Delete all files in the participant folder
        for filename in os.listdir(participant_folder):
            file_path = os.path.join(participant_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted: {file_path}")
                
        # Remove the empty directory
        try:
            os.rmdir(participant_folder)
            print(f"Removed directory: {participant_folder}")
        except OSError:
            # Directory not empty or other issue, but files are deleted
            pass

    def start_new_session(self, participant_id):
        """Start a new session with the given participant ID"""
        # Reset all session data
        self.reset_session_data()
        
        # Set new participant ID
        self.current_participant_id = participant_id
        self.participant_folder = os.path.join("Participant_Data", f"Participant_{participant_id}")
        
        # Update UI
        self.session_status_label.config(
            text=f"Active session: {participant_id}",
            fg=SUCCESS_COLOR
        )
        
        # Check folder permissions
        if not self._check_folder_permissions():
            # Reset if folder check fails
            self.current_participant_id = None
            self.participant_folder = None
            self.session_status_label.config(
                text="No active session",
                fg=SECONDARY_TEXT
            )
            return False
            
        # Create folder if it doesn't exist
        os.makedirs(self.participant_folder, exist_ok=True)
        
        print(f"Started new session for participant: {participant_id}")
        print(f"Data will be saved to: {self.participant_folder}")
        
        return True
        
    def reset_session_data(self):
        """Reset all session-related data"""
        # Clear data buffers
        self.data_buffers = {
            'HeartRate': [],
            'RRinterval': []
        }
        
        # Clear timestamps and intervals
        self.marked_timestamps = []
        self.intervals = []
        self.current_interval_start = None
        
        # Reset interval button states if they exist
        if hasattr(self, 'start_interval_button'):
            self.start_interval_button.config(
                bg=DARK_BG,
                fg=TEXT_COLOR if self.connected else SECONDARY_TEXT,
                text="START INTERVAL"
            )
        if hasattr(self, 'end_interval_button'):
            self.end_interval_button.config(
                bg=DARK_BG,
                fg=TEXT_COLOR if self.connected else SECONDARY_TEXT
            )
        
        # Close any open file handles
        self._close_recording_files()
        
        # Ensure recording UI is reset
        if hasattr(self, 'start_button'):
            self._update_recording_ui_state(False)
        
        print("Session data reset")

    def connect_to_device(self):
        # Check if we have an active session
        if not self.current_participant_id:
            messagebox.showwarning("No Active Session", "Please set a Participant ID first.")
            return

        selected_device = self.device_var.get()
        if not selected_device:
            messagebox.showwarning("Device Not Selected", "Please select a Polar device.")
            return

        # Extract device address from selection
        self.device_address = selected_device.split("(")[1].split(")")[0]

        # Start connection in a separate thread to avoid blocking the UI
        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _check_folder_permissions(self):
        """Check if we have permission to write to the participant folder"""
        try:
            # First check if the parent directory exists and is writable
            parent_dir = os.path.dirname(self.participant_folder)
            if not os.path.exists(parent_dir):
                try:
                    os.makedirs(parent_dir, exist_ok=True)
                    print(f"Created parent directory: {parent_dir}")
                except Exception as e:
                    print(f"Error creating parent directory: {str(e)}")
                    messagebox.showerror("Permission Error",
                                        f"Cannot create the directory {parent_dir}.\n"
                                        f"Please check if you have write permissions to the application folder.")
                    return False

            # Check if we can write to the parent directory
            test_file = os.path.join(parent_dir, "permission_test.txt")
            try:
                with open(test_file, 'w') as f:
                    f.write("Permission test")
                os.remove(test_file)
                print(f"Write permission test passed for {parent_dir}")
            except Exception as e:
                print(f"Error writing to parent directory: {str(e)}")
                messagebox.showerror("Permission Error",
                                    f"Cannot write to the directory {parent_dir}.\n"
                                    f"Please check if you have write permissions to the application folder.")
                return False

            # Now check/create the participant folder
            if not os.path.exists(self.participant_folder):
                try:
                    os.makedirs(self.participant_folder, exist_ok=True)
                    print(f"Created participant directory: {self.participant_folder}")
                except Exception as e:
                    print(f"Error creating participant directory: {str(e)}")
                    messagebox.showerror("Permission Error",
                                        f"Cannot create the directory {self.participant_folder}.\n"
                                        f"Please check if you have write permissions.")
                    return False

            # Check if we can write to the participant folder
            test_file = os.path.join(self.participant_folder, "permission_test.txt")
            try:
                with open(test_file, 'w') as f:
                    f.write("Permission test")
                os.remove(test_file)
                print(f"Write permission test passed for {self.participant_folder}")
                return True
            except Exception as e:
                print(f"Error writing to participant folder: {str(e)}")
                messagebox.showerror("Permission Error",
                                    f"Cannot write to the directory {self.participant_folder}.\n"
                                    f"Please check if you have write permissions.")
                return False

        except Exception as e:
            print(f"Error checking folder permissions: {str(e)}")
            messagebox.showerror("Permission Error",
                                f"An error occurred while checking folder permissions: {str(e)}")
            return False

    def _connect_thread(self):
        try:
            # Update button appearance for connecting state
            self.connect_button.config(
                text="CONNECTING...", 
                state=tk.DISABLED,
                bg=WARNING_COLOR,
                fg=DARKER_BG
            )
            
            self.loop.run_until_complete(self._connect_to_polar())
            
            # Enable recording button and mark button with dark theme styling
            self.start_button.config(
                state=tk.NORMAL,
                bg=DARK_BG,
                fg=TEXT_COLOR,
                activebackground=DARKER_BG,
                activeforeground=TEXT_COLOR
            )
            
            self.mark_button.config(
                state=tk.NORMAL,
                bg=DARK_BG,
                fg=TEXT_COLOR,
                activebackground=DARKER_BG,
                activeforeground=TEXT_COLOR
            )
            
            # Enable interval buttons
            self.start_interval_button.config(
                state=tk.NORMAL,
                bg=DARK_BG,
                fg=TEXT_COLOR,
                activebackground=DARKER_BG,
                activeforeground=TEXT_COLOR
            )
            
            self.end_interval_button.config(
                state=tk.NORMAL,
                bg=DARK_BG,
                fg=TEXT_COLOR,
                activebackground=DARKER_BG,
                activeforeground=TEXT_COLOR
            )
            
            # Update connect button to disconnect button with dark theme styling
            self.connect_button.config(
                text="DISCONNECT", 
                state=tk.NORMAL,
                command=self.disconnect_from_device,
                bg=ERROR_COLOR,
                fg=DARKER_BG,
                activebackground=DARK_BG,
                activeforeground=ERROR_COLOR
            )

            # Start a periodic data request to ensure preview data is continuously received
            threading.Thread(target=self._periodic_data_request, daemon=True).start()
            
            # Update session status
            if self.current_participant_id:
                self.session_status_label.config(
                    text=f"Session: {self.current_participant_id} (connected)",
                    fg=SUCCESS_COLOR
                )
            
            # Set up LSL streams for real-time streaming
            self._setup_lsl_streams()

            # Start updating the plot immediately
            self.update_plot()
            # Schedule regular plot updates
            self._schedule_plot_updates()

            messagebox.showinfo("Connected", "Connected to Polar H10 successfully! Data preview and LSL streaming have started automatically.")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            # Reset connect button with dark theme styling
            self.connect_button.config(
                text="CONNECT", 
                state=tk.NORMAL,
                bg=ACCENT_COLOR,
                fg=DARKER_BG,
                activebackground=DARK_BG,
                activeforeground=ACCENT_COLOR
            )
            
    def _schedule_plot_updates(self):
        """Schedule regular plot updates"""
        if self.connected:
            self.update_plot()
            # Update plot every 500ms
            self.parent.after(500, self._schedule_plot_updates)

    def _setup_lsl_streams(self):
        """Set up LSL streams for heart rate and RR intervals"""
        try:
            # Create HeartRate stream
            hr_info = StreamInfo('HeartRate', 'ExciteOMeter', 1, 10, 'float32', 'HeartRateStream')
            self.hr_outlet = StreamOutlet(hr_info)
            print("✓ Created LSL stream: HeartRate")
            
            # Create RRinterval stream  
            rr_info = StreamInfo('RRinterval', 'ExciteOMeter', 1, 10, 'float32', 'RRintervalStream')
            self.rr_outlet = StreamOutlet(rr_info)
            print("✓ Created LSL stream: RRinterval")
            
        except Exception as e:
            print(f"Error setting up LSL streams: {str(e)}")

    def _cleanup_lsl_streams(self):
        """Clean up LSL streams"""
        if self.hr_outlet:
            try:
                del self.hr_outlet
                self.hr_outlet = None
                print("✓ Cleaned up HeartRate LSL stream")
            except Exception as e:
                print(f"Error cleaning up HR LSL stream: {str(e)}")
                
        if self.rr_outlet:
            try:
                del self.rr_outlet  
                self.rr_outlet = None
                print("✓ Cleaned up RRinterval LSL stream")
            except Exception as e:
                print(f"Error cleaning up RR LSL stream: {str(e)}")

    def _periodic_data_request(self):
        """Periodically request data to ensure continuous data flow"""
        while self.connected:
            current_time = time.time()

            # Check if we have recent data (within the last 3 seconds)
            has_recent_data = False
            if self.data_buffers['HeartRate']:
                last_timestamp = self.data_buffers['HeartRate'][-1][0]
                if current_time - last_timestamp < 3:
                    has_recent_data = True

            # If no recent data, request it
            if not has_recent_data:
                try:
                    print("Requesting heart rate data...")
                    threading.Thread(target=lambda: self._force_test_reading(preview_mode=True), daemon=True).start()
                except Exception as e:
                    print(f"Error requesting data: {str(e)}")

            # Wait before next check
            time.sleep(2)  # Check every 2 seconds

    async def _connect_to_polar(self):
        # Connect to the Polar H10
        try:
            print(f"Attempting to connect to device at address: {self.device_address}")

            # Use a longer timeout for connection
            self.client = BleakClient(self.device_address, timeout=20.0)
            connected = await self.client.connect()

            if not connected or not self.client.is_connected:
                raise Exception("Failed to connect to device")

            self.connected = True
            self.status_var.set(f"Status: Connected to {self.device_address}")
            print(f"Successfully connected to device at {self.device_address}")

            # Get device info and services
            try:
                services = await self.client.get_services()
                print(f"Available services:")
                for service in services.services.values():
                    print(f"Service: {service.uuid}")
                    for char in service.characteristics:
                        print(f"  Characteristic: {char.uuid}, Properties: {char.properties}")
            except Exception as e:
                print(f"Error getting device info: {str(e)}")

            # Check battery level
            try:
                battery = await self.client.read_gatt_char(BATTERY_LEVEL)
                battery_level = int(battery[0])
                print(f"Battery level: {battery_level}%")
                if battery_level < 15:
                    print("WARNING: Battery level is low. This may affect data transmission.")
                    # Show warning to user
                    self.parent.after(0, lambda: messagebox.showwarning(
                        "Low Battery",
                        f"The Polar H10 battery level is low ({battery_level}%).\n"
                        "This may affect data transmission. Consider charging the device."
                    ))
            except Exception as e:
                print(f"Could not read battery level: {str(e)}")

            # Set up notifications for heart rate using the proper approach
            try:
                print("Setting up heart rate notifications...")

                # First, enable notifications by writing to the Client Characteristic Configuration Descriptor
                # This is the proper way to enable notifications according to the Bluetooth GATT specification
                hr_service = None
                hr_char = None

                # Find the heart rate service and characteristic
                for service in services.services.values():
                    if service.uuid.lower() == HEART_RATE_SERVICE.lower():
                        hr_service = service
                        for char in service.characteristics:
                            if char.uuid.lower() == HEART_RATE_UUID.lower():
                                hr_char = char
                                break
                        break

                if hr_service and hr_char:
                    print(f"Found heart rate service: {hr_service.uuid}")
                    print(f"Found heart rate characteristic: {hr_char.uuid}")

                    # Find the Client Characteristic Configuration Descriptor
                    for descriptor in hr_char.descriptors:
                        if descriptor.uuid.lower() == CLIENT_CHAR_CONFIG.lower():
                            # Write 0x0100 to enable notifications (little endian)
                            await self.client.write_gatt_descriptor(descriptor.handle, bytearray([0x01, 0x00]))
                            print("Enabled heart rate notifications via descriptor")
                            break

                    # Register notification handler
                    await self.client.start_notify(HEART_RATE_UUID, self._heart_rate_handler)
                    print("Heart rate notifications enabled successfully")

                    # Force an initial heart rate reading to verify connection
                    threading.Thread(target=self._force_initial_reading, daemon=True).start()
                else:
                    print("Could not find heart rate service or characteristic")
                    raise Exception("Heart rate service not found")

            except Exception as e:
                print(f"Error setting up heart rate notifications: {str(e)}")
                print("Trying alternative approach...")

                try:
                    # Try the direct approach as fallback
                    await self.client.start_notify(HEART_RATE_UUID, self._heart_rate_handler)
                    print("Heart rate notifications enabled via direct method")

                    # Force an initial heart rate reading to verify connection
                    threading.Thread(target=self._force_initial_reading, daemon=True).start()
                except Exception as e2:
                    print(f"Alternative approach also failed: {str(e2)}")
                    print("Please ensure the Polar H10 is properly worn and the chest strap is moistened")

            # Enable ECG streaming (for RR intervals) - optional, don't fail if this doesn't work
            try:
                print("Setting up PMD data notifications...")
                await self.client.write_gatt_char(PMD_CONTROL, PMD_COMMAND)
                await self.client.start_notify(PMD_DATA, self._pmd_data_handler)
                print("PMD data notifications enabled")
            except Exception as e:
                print(f"Error setting up PMD data: {str(e)}")
                print("RR intervals may still be available from the heart rate service")

            # Start a watchdog to check if we're receiving data
            threading.Thread(target=self._data_watchdog, daemon=True).start()

        except Exception as e:
            self.connected = False
            print(f"Connection failed: {str(e)}")
            raise e

    def _force_initial_reading(self):
        """Force an initial heart rate reading to verify connection"""
        try:
            time.sleep(2)  # Wait for notifications to be set up
            if not self.data_buffers['HeartRate']:
                print("No heart rate data received yet, forcing a reading...")
                self.loop.run_until_complete(self._force_heart_rate_reading_loop())
        except Exception as e:
            print(f"Error forcing initial reading: {str(e)}")

    async def _force_heart_rate_reading_loop(self):
        """Try multiple approaches to get heart rate data"""
        try:
            # Try reading the heart rate characteristic directly
            try:
                hr_value = await self._read_heart_rate()
                if hr_value:
                    print(f"Successfully read heart rate directly: {hr_value} bpm")
                    return
            except Exception as e:
                print(f"Could not read heart rate directly: {str(e)}")

            # Try restarting notifications
            try:
                await self._restart_notifications()
            except Exception as e:
                print(f"Error restarting notifications: {str(e)}")

            # Try reading battery level to keep connection active
            try:
                battery = await self.client.read_gatt_char(BATTERY_LEVEL)
                print(f"Read battery level to keep connection active: {int(battery[0])}%")
            except Exception as e:
                print(f"Error reading battery: {str(e)}")

            # Try writing to the control characteristic to wake up the device
            try:
                # Write a dummy value to the control characteristic
                await self.client.write_gatt_char(PMD_CONTROL, bytearray([0x01, 0x00]))
                print("Wrote to control characteristic to wake up device")
            except Exception as e:
                print(f"Error writing to control: {str(e)}")

        except Exception as e:
            print(f"Error in force heart rate reading loop: {str(e)}")

    def _data_watchdog(self):
        """Check if we're receiving data from the device"""
        time.sleep(5)  # Wait for initial connection

        if not self.data_buffers['HeartRate']:
            # No heart rate data received after 5 seconds
            self.parent.after(0, lambda: self.status_var.set("Status: Connected but no data received. Check device placement."))
            print("No heart rate data received after 5 seconds. Please check:")
            print("1. Is the chest strap properly positioned and moistened?")
            print("2. Is the Polar H10 sensor firmly attached to the strap?")
            print("3. Is the battery level sufficient?")

            # Try to force a reading
            try:
                print("Attempting to force a heart rate reading...")
                threading.Thread(target=lambda: self._force_test_reading(preview_mode=False), daemon=True).start()
            except Exception as e:
                print(f"Error forcing heart rate reading: {str(e)}")

        # Check every 15 seconds if data is still coming in (increased from 10 to reduce false warnings)
        last_check_time = time.time()
        last_data_count = len(self.data_buffers['HeartRate'])
        consecutive_no_data = 0  # Count consecutive checks with no new data

        while self.connected:
            time.sleep(15)  # Increased from 10 seconds
            current_time = time.time()
            current_data_count = len(self.data_buffers['HeartRate'])

            if current_data_count == last_data_count:
                consecutive_no_data += 1

                # Only show warning after 2 consecutive checks with no data (30 seconds total)
                if consecutive_no_data >= 2:
                    # No new data in the last 30 seconds
                    self.parent.after(0, lambda: self.status_var.set("Status: No new data in the last 30 seconds. Check device."))
                    print("No new data received in the last 30 seconds. Troubleshooting steps:")
                    print("1. Make sure the chest strap is properly moistened and positioned")
                    print("2. Try disconnecting and reconnecting the device")
                    print("3. Check if the Polar H10 needs to be recharged")
                    print("4. Ensure the Polar H10 is not connected to another device/app")

                    # Try to force a reading
                    try:
                        print("Attempting to force a heart rate reading...")
                        threading.Thread(target=lambda: self._force_test_reading(preview_mode=False), daemon=True).start()
                    except Exception as e:
                        print(f"Error forcing heart rate reading: {str(e)}")
            else:
                # Data is coming in
                self.data_received = True
                last_data_count = current_data_count
                last_check_time = current_time
                consecutive_no_data = 0  # Reset counter

                # If we're getting data but not recording, remind the user
                if self.data_received and not self.recording:
                    print("Data is being received. Click 'Start Recording' to save the data.")

    def _heart_rate_handler(self, sender, data):
        """Handle incoming heart rate data"""
        if not data:
            return

        try:
            # Heart rate data format: https://www.bluetooth.com/specifications/specs/gatt-specification-supplement-3/
            flags = data[0]
            hr_format = (flags & 0x01) == 0x01  # 0 = UINT8, 1 = UINT16
            has_rr = (flags & 0x10) == 0x10     # Check if RR intervals are present

            if hr_format:
                # UINT16 format
                hr_value = struct.unpack('<H', data[1:3])[0]
            else:
                # UINT8 format
                hr_value = data[1]

            timestamp = local_clock()

            # Set flag that data is being received
            self.data_received = True

            # Update status with latest heart rate
            if self.recording:
                self.status_var.set(f"Status: RECORDING | HR: {hr_value} bpm")
            else:
                self.status_var.set(f"Status: Connected | HR: {hr_value} bpm")

            # Always add to data buffer for display purposes
            self.data_buffers['HeartRate'].append((timestamp, hr_value))

            # Push to LSL stream if available
            if self.hr_outlet:
                try:
                    self.hr_outlet.push_sample([float(hr_value)])
                except Exception as e:
                    print(f"Error pushing HR to LSL stream: {str(e)}")

            # Limit buffer size to prevent memory issues
            if len(self.data_buffers['HeartRate']) > 1000:
                # Keep only the most recent 1000 points
                self.data_buffers['HeartRate'] = self.data_buffers['HeartRate'][-1000:]

            # If first data point, log it
            if len(self.data_buffers['HeartRate']) == 1:
                print(f"First heart rate data received: {hr_value} bpm")

            # Only save to file if recording
            if self.recording:
                # Use a more efficient approach to file writing
                self._write_hr_data_to_file(timestamp, hr_value)

            # Check for RR intervals
            if has_rr:
                # RR intervals are in 1/1024 second format
                rr_count = (len(data) - 2) // 2  # Each RR interval is 2 bytes
                rr_offset = 2
                if hr_format:
                    rr_offset = 3  # RR values start after the 2-byte heart rate value

                for i in range(rr_count):
                    rr_value = struct.unpack('<H', data[rr_offset + i*2:rr_offset + i*2 + 2])[0]
                    # Convert to milliseconds
                    rr_ms = (rr_value / 1024) * 1000

                    # Always add to data buffer for display
                    self.data_buffers['RRinterval'].append((timestamp, rr_ms))

                    # Push to LSL stream if available
                    if self.rr_outlet:
                        try:
                            self.rr_outlet.push_sample([float(rr_ms)])
                        except Exception as e:
                            print(f"Error pushing RR to LSL stream: {str(e)}")

                    # Limit buffer size
                    if len(self.data_buffers['RRinterval']) > 1000:
                        self.data_buffers['RRinterval'] = self.data_buffers['RRinterval'][-1000:]

                    # Only save to file if recording
                    if self.recording:
                        # Use a more efficient approach to file writing
                        self._write_rr_data_to_file(timestamp, rr_ms)

        except Exception as e:
            print(f"Error processing heart rate data: {str(e)}")

    def _write_hr_data_to_file(self, timestamp, hr_value):
        """Write heart rate data to file with better error handling"""
        try:
            # Check if we have a cached file handle
            if not hasattr(self, '_hr_file') or self._hr_file is None:
                # Create the file if it doesn't exist
                csv_filename = os.path.join(self.participant_folder, "HeartRate_recording.csv")
                if not os.path.exists(csv_filename):
                    # Create directory if needed
                    os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
                    # Create file with header
                    with open(csv_filename, 'w', newline='') as csvfile:
                        csv_writer = csv.writer(csvfile)
                        csv_writer.writerow(['Timestamp', 'Value'])

                # Open file for appending
                self._hr_file = open(csv_filename, 'a', newline='')
                self._hr_writer = csv.writer(self._hr_file)
                print(f"Opened HR file for writing: {csv_filename}")

            # Write data
            self._hr_writer.writerow([timestamp, hr_value])
            self._hr_file.flush()  # Ensure data is written immediately

        except Exception as e:
            print(f"Error writing HR data to file: {str(e)}")
            # Close file handle if there was an error
            if hasattr(self, '_hr_file') and self._hr_file is not None:
                try:
                    self._hr_file.close()
                    self._hr_file = None
                except:
                    pass

    def _write_rr_data_to_file(self, timestamp, rr_value):
        """Write RR interval data to file with better error handling"""
        try:
            # Check if we have a cached file handle
            if not hasattr(self, '_rr_file') or self._rr_file is None:
                # Create the file if it doesn't exist
                csv_filename = os.path.join(self.participant_folder, "RRinterval_recording.csv")
                if not os.path.exists(csv_filename):
                    # Create directory if needed
                    os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
                    # Create file with header
                    with open(csv_filename, 'w', newline='') as csvfile:
                        csv_writer = csv.writer(csvfile)
                        csv_writer.writerow(['Timestamp', 'Value'])

                # Open file for appending
                self._rr_file = open(csv_filename, 'a', newline='')
                self._rr_writer = csv.writer(self._rr_file)
                print(f"Opened RR file for writing: {csv_filename}")

            # Write data
            self._rr_writer.writerow([timestamp, rr_value])
            self._rr_file.flush()  # Ensure data is written immediately

        except Exception as e:
            print(f"Error writing RR data to file: {str(e)}")
            # Close file handle if there was an error
            if hasattr(self, '_rr_file') and self._rr_file is not None:
                try:
                    self._rr_file.close()
                    self._rr_file = None
                except:
                    pass

    def _pmd_data_handler(self, sender, data):
        """Handle PMD data (ECG and other raw data)"""
        # This is a simplified handler - full implementation would parse the PMD data format
        # For now, we're focusing on heart rate and RR intervals from the standard BLE service
        pass

    def toggle_recording(self):
        if not self.recording:
            # Start recording
            try:
                # Set up recording files
                threading.Thread(target=self._setup_recording_files, daemon=True).start()

                # Mark the start of recording time
                self.recording_start_time = local_clock()
                print(f"Recording start time: {self.recording_start_time}")

                # Set recording flags
                self.recording = True
                self.recording_event.set()
                
                # Update UI to reflect recording started
                self._update_recording_ui_state(True)
                print("Recording started successfully")

                # Force an immediate plot update to show recording state
                self.update_plot()
            except Exception as e:
                print(f"Error starting recording: {str(e)}")
                messagebox.showerror("Recording Error", f"Failed to start recording: {str(e)}")
                self.recording = False
                self.recording_event.clear()
                
                # Reset button appearance
                self.start_button.config(
                    text="START RECORDING",
                    bg=DARK_BG,
                    fg=TEXT_COLOR,
                    activebackground=DARKER_BG,
                    activeforeground=TEXT_COLOR
                )
        else:
            # Stop recording (UI will be updated in stop_recording method)
            self.stop_recording()

    def _setup_recording_files(self):
        """Set up recording files in a separate thread"""
        try:
            # Ensure the participant folder exists
            if not os.path.exists(self.participant_folder):
                os.makedirs(self.participant_folder, exist_ok=True)

            # Create CSV files with headers
            for stream_name in self.data_buffers.keys():
                csv_filename = os.path.join(self.participant_folder, f"{stream_name}_recording.csv")
                with open(csv_filename, 'w', newline='') as csvfile:
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerow(['Timestamp', 'Value'])
                print(f"Created file: {csv_filename}")

            # Create a file for marked timestamps
            marked_filename = os.path.join(self.participant_folder, "marked_timestamps.csv")
            with open(marked_filename, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['Timestamp'])
                print(f"Created file: {marked_filename}")
                
            # Create a file for intervals
            intervals_filename = os.path.join(self.participant_folder, "intervals.csv")
            with open(intervals_filename, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['Start_Timestamp', 'End_Timestamp', 'Duration'])
                print(f"Created file: {intervals_filename}")

            print(f"Recording files created in {self.participant_folder}")

            # Start a thread to monitor recording
            threading.Thread(target=self._monitor_recording, daemon=True).start()

        except Exception as e:
            print(f"Error in setup_recording_files: {str(e)}")
            # Notify the user of the error
            self.parent.after(0, lambda: messagebox.showerror("Recording Error", 
                                                             f"Failed to set up recording files: {str(e)}"))

    def _monitor_recording(self):
        """Monitor the recording process to ensure data is being saved"""
        if not self.recording:
            return

        # Wait a few seconds for data to start coming in
        time.sleep(5)

        # Check if any data has been recorded
        try:
            hr_filename = os.path.join(self.participant_folder, "HeartRate_recording.csv")
            if os.path.exists(hr_filename):
                file_size = os.path.getsize(hr_filename)
                if file_size <= 20:  # Only header line
                    print("WARNING: No heart rate data has been recorded after 5 seconds")
                    self.parent.after(0, lambda: messagebox.showwarning(
                        "No Data Recorded",
                        "No heart rate data has been recorded after 5 seconds. Check that the device is properly positioned."
                    ))
                else:
                    print(f"Recording is working. File size: {file_size} bytes")
        except Exception as e:
            print(f"Error monitoring recording: {str(e)}")

    def stop_recording(self):
        # Store the recording stop time
        self.recording_stop_time = local_clock()
        print(f"Recording stop time: {self.recording_stop_time}")
        
        # Handle incomplete interval
        if self.current_interval_start is not None:
            response = messagebox.askyesno("Incomplete Interval", 
                                         "You have an active interval. Do you want to end it automatically when stopping recording?")
            if response:
                self.end_interval()
            else:
                # Reset interval state without saving
                self.current_interval_start = None
                self.start_interval_button.config(
                    bg=DARK_BG,
                    fg=TEXT_COLOR,
                    text="START INTERVAL"
                )
                self.end_interval_button.config(
                    bg=DARK_BG,
                    fg=TEXT_COLOR
                )
        
        self.recording = False
        self.recording_event.clear()
        
        # Close file handles if they're open
        self._close_recording_files()

        self.save_marked_timestamps()

        # Verify the recording files
        self._verify_recording_files()
        
        # Update UI to reflect recording stopped
        self._update_recording_ui_state(False)
        
        # Force an immediate plot update to show the stop line
        self.update_plot()

    def _update_recording_ui_state(self, is_recording):
        """Update UI elements to reflect current recording state"""
        if is_recording:
            # Update button appearance for recording state
            self.start_button.config(
                text="STOP RECORDING",
                bg=ERROR_COLOR,
                fg=DARKER_BG,
                activebackground=DARK_BG,
                activeforeground=ERROR_COLOR
            )
            
            # Update status with recording indicator
            if hasattr(self, 'status_var'):
                current_status = self.status_var.get()
                if "RECORDING" not in current_status:
                    self.status_var.set(f"{current_status} | ● RECORDING")
        else:
            # Reset button appearance for stopped state
            self.start_button.config(
                text="START RECORDING",
                bg=DARK_BG,
                fg=TEXT_COLOR,
                activebackground=DARKER_BG,
                activeforeground=TEXT_COLOR
            )
            
            # Update status to remove recording indicator
            if hasattr(self, 'status_var'):
                current_status = self.status_var.get()
                if "● RECORDING" in current_status:
                    self.status_var.set(current_status.replace(" | ● RECORDING", ""))

    def _close_recording_files(self):
        """Close any open file handles"""
        # Close heart rate file
        if hasattr(self, '_hr_file') and self._hr_file is not None:
            try:
                self._hr_file.close()
                print("Closed heart rate recording file")
            except Exception as e:
                print(f"Error closing heart rate file: {str(e)}")
            finally:
                self._hr_file = None

        # Close RR interval file
        if hasattr(self, '_rr_file') and self._rr_file is not None:
            try:
                self._rr_file.close()
                print("Closed RR interval recording file")
            except Exception as e:
                print(f"Error closing RR interval file: {str(e)}")
            finally:
                self._rr_file = None

    def _verify_recording_files(self):
        """Verify that the recording files exist and contain data"""
        try:
            print("\n--- Verifying Recording Files ---")

            for stream_name in self.data_buffers.keys():
                csv_filename = os.path.join(self.participant_folder, f"{stream_name}_recording.csv")

                if not os.path.exists(csv_filename):
                    print(f"WARNING: File does not exist: {csv_filename}")
                    continue

                file_size = os.path.getsize(csv_filename)
                print(f"File: {csv_filename}, Size: {file_size} bytes")

                # Check if file contains data beyond the header
                if file_size <= 20:  # Only header line
                    print(f"WARNING: File appears to be empty (only header): {csv_filename}")
                else:
                    # Count the number of lines in the file
                    line_count = 0
                    with open(csv_filename, 'r') as f:
                        for line in f:
                            line_count += 1

                    print(f"File contains {line_count} lines (including header)")

                    if line_count <= 1:
                        print(f"WARNING: No data rows in file: {csv_filename}")
                    else:
                        print(f"✓ File contains {line_count-1} data rows")

            print("--- Recording Files Verification Complete ---\n")

            # Show a summary to the user
            if len(self.data_buffers['HeartRate']) > 0:
                hr_filename = os.path.join(self.participant_folder, f"HeartRate_recording.csv")
                if os.path.exists(hr_filename) and os.path.getsize(hr_filename) > 20:
                    messagebox.showinfo("Recording Complete", f"Recording completed successfully.\nData saved to {self.participant_folder}")
                else:
                    messagebox.showwarning("Recording Issue", "Recording completed, but the heart rate file may not contain data.\nCheck the console for details.")
            else:
                messagebox.showwarning("No Data", "Recording completed, but no heart rate data was collected.\nCheck the device positioning and connection.")

        except Exception as e:
            print(f"Error verifying recording files: {str(e)}")

    def mark_timestamp(self):
        if self.recording:
            timestamp = local_clock()
            self.marked_timestamps.append(timestamp)
            messagebox.showinfo("Timestamp Marked", f"Marked timestamp at {timestamp:.2f}")
        else:
            messagebox.showwarning("Recording Not Active", "Start recording before marking timestamps.")

    def start_interval(self):
        if not self.recording:
            messagebox.showwarning("Recording Not Active", "Start recording before creating intervals.")
            return
            
        if self.current_interval_start is not None:
            messagebox.showwarning("Interval Already Started", "You have already started an interval. End it before starting a new one.")
            return
            
        self.current_interval_start = local_clock()
        
        # Update button states to show interval is active
        self.start_interval_button.config(
            bg=WARNING_COLOR,
            fg=DARKER_BG,
            text="INTERVAL ACTIVE"
        )
        self.end_interval_button.config(
            bg=SUCCESS_COLOR,
            fg=DARKER_BG
        )
        
        messagebox.showinfo("Interval Started", f"Interval started at {self.current_interval_start:.2f}")
        print(f"Interval started at {self.current_interval_start:.2f}")

    def end_interval(self):
        if not self.recording:
            messagebox.showwarning("Recording Not Active", "Start recording before creating intervals.")
            return
            
        if self.current_interval_start is None:
            messagebox.showwarning("No Active Interval", "Start an interval before ending it.")
            return
            
        end_time = local_clock()
        interval_duration = end_time - self.current_interval_start
        
        # Store the completed interval
        self.intervals.append((self.current_interval_start, end_time))
        
        # Reset interval state
        self.current_interval_start = None
        
        # Reset button states
        self.start_interval_button.config(
            bg=DARK_BG,
            fg=TEXT_COLOR,
            text="START INTERVAL"
        )
        self.end_interval_button.config(
            bg=DARK_BG,
            fg=TEXT_COLOR
        )
        
        messagebox.showinfo("Interval Completed", 
                          f"Interval completed!\nDuration: {interval_duration:.2f} seconds\nTotal intervals: {len(self.intervals)}")
        print(f"Interval completed: {self.current_interval_start:.2f} - {end_time:.2f} (duration: {interval_duration:.2f}s)")
        print(f"Total intervals created: {len(self.intervals)}")

    def save_marked_timestamps(self):
        # Save timestamps
        if self.marked_timestamps:
            marked_filename = os.path.join(self.participant_folder, "marked_timestamps.csv")
            with open(marked_filename, 'w', newline='') as marked_file:
                csv_writer = csv.writer(marked_file)
                csv_writer.writerow(['Timestamp'])
                csv_writer.writerows([[ts] for ts in self.marked_timestamps])
                
        # Save intervals
        if self.intervals:
            intervals_filename = os.path.join(self.participant_folder, "intervals.csv")
            with open(intervals_filename, 'w', newline='') as intervals_file:
                csv_writer = csv.writer(intervals_file)
                csv_writer.writerow(['Start_Timestamp', 'End_Timestamp', 'Duration'])
                for start, end in self.intervals:
                    duration = end - start
                    csv_writer.writerow([start, end, duration])
                    
        # Handle incomplete interval
        if self.current_interval_start is not None:
            print(f"Warning: Incomplete interval detected (started at {self.current_interval_start:.2f})")
            # Optionally, you could auto-complete it here or save it separately

    def update_plot(self):
        try:
            self.ax1.clear()
            self.ax2.clear()
            has_hr_data = False
            has_rr_data = False
            current_time = local_clock()

            # Set dark theme styling for the plot
            self.ax1.set_facecolor(DARK_BG)
            self.ax2.set_facecolor(DARK_BG)
            
            self.ax1.tick_params(colors=SECONDARY_TEXT)
            self.ax2.tick_params(colors=SECONDARY_TEXT)
            
            for spine in ['bottom', 'top', 'right', 'left']:
                self.ax1.spines[spine].set_color(BORDER_COLOR)
                self.ax2.spines[spine].set_color(BORDER_COLOR)

            # Plot heart rate data
            if 'HeartRate' in self.data_buffers and self.data_buffers['HeartRate']:
                # Limit to last 100 seconds of data
                hr_data = [(ts, val) for ts, val in self.data_buffers['HeartRate'] if current_time - ts <= 100]

                if hr_data:
                    # If recording, split data into pre-recording and recording data
                    if self.recording and hasattr(self, 'recording_start_time'):
                        pre_recording_hr = [(ts, val) for ts, val in hr_data if ts < self.recording_start_time]
                        recording_hr = [(ts, val) for ts, val in hr_data if ts >= self.recording_start_time]

                        # Plot pre-recording data in lighter color
                        if pre_recording_hr:
                            timestamps_pre, values_pre = zip(*pre_recording_hr)
                            self.ax1.plot(timestamps_pre, values_pre, color=SECONDARY_TEXT, alpha=0.3, linewidth=1.0, label='Preview HR')

                        # Plot recording data in bold
                        if recording_hr:
                            timestamps_rec, values_rec = zip(*recording_hr)
                            self.ax1.plot(timestamps_rec, values_rec, color=ACCENT_COLOR, linewidth=2.0, label='Recording HR')
                            has_hr_data = True
                    else:
                        # Regular display for preview mode
                        timestamps_hr, values_hr = zip(*hr_data)
                        self.ax1.plot(timestamps_hr, values_hr, color=ACCENT_COLOR, label='Heart Rate', linewidth=1.5)
                        has_hr_data = True

                    # Set y-axis limits with some padding to prevent jumping
                    if has_hr_data:
                        all_values = [val for _, val in hr_data]
                        if all_values:
                            min_val = max(0, min(all_values) - 5)
                            max_val = max(all_values) + 5
                            self.ax1.set_ylim(min_val, max_val)

                self.ax1.set_ylabel('Heart Rate (bpm)', color=ACCENT_COLOR, labelpad=15, va='center', fontsize=10)
                self.ax1.tick_params(axis='y', labelcolor=ACCENT_COLOR)

            # Plot RR interval data
            if 'RRinterval' in self.data_buffers and self.data_buffers['RRinterval']:
                # Limit to last 100 seconds of data
                rr_data = [(ts, val) for ts, val in self.data_buffers['RRinterval'] if current_time - ts <= 100]

                if rr_data:
                    # If recording, split data into pre-recording and recording data
                    if self.recording and hasattr(self, 'recording_start_time'):
                        pre_recording_rr = [(ts, val) for ts, val in rr_data if ts < self.recording_start_time]
                        recording_rr = [(ts, val) for ts, val in rr_data if ts >= self.recording_start_time]

                        # Plot pre-recording data in lighter color
                        if pre_recording_rr:
                            timestamps_pre, values_pre = zip(*pre_recording_rr)
                            self.ax2.plot(timestamps_pre, values_pre, color=SECONDARY_TEXT, alpha=0.3, linewidth=1.0, label='Preview RR')

                        # Plot recording data in bold
                        if recording_rr:
                            timestamps_rec, values_rec = zip(*recording_rr)
                            self.ax2.plot(timestamps_rec, values_rec, color=SUCCESS_COLOR, linewidth=2.0, label='Recording RR')
                            has_rr_data = True
                    else:
                        # Regular display for preview mode
                        timestamps_rr, values_rr = zip(*rr_data)
                        self.ax2.plot(timestamps_rr, values_rr, color=SUCCESS_COLOR, label='RR Interval', linewidth=1.5)
                        has_rr_data = True

                    # Set y-axis limits with some padding to prevent jumping
                    if has_rr_data:
                        all_values = [val for _, val in rr_data]
                        if all_values:
                            min_val = max(0, min(all_values) - 50)
                            max_val = max(all_values) + 50
                            self.ax2.set_ylim(min_val, max_val)

                self.ax2.set_ylabel('RR Interval (ms)', color=SUCCESS_COLOR, labelpad=15, ha='right', va='center', fontsize=10)
                self.ax2.yaxis.set_label_position("right")
                self.ax2.tick_params(axis='y', labelcolor=SUCCESS_COLOR)

            # Set x-axis limits to prevent horizontal jumping
            if has_hr_data or has_rr_data:
                self.ax1.set_xlim(current_time - 100, current_time)

            self.ax1.set_xlabel("Time (Last 100s)", color=SECONDARY_TEXT, fontsize=10)
            self.ax1.grid(True, linestyle='--', alpha=0.2, color=BORDER_COLOR)

            # Create combined legend with both HR and RR data
            if self.recording:
                # Create a list of legend handles and labels from both axes
                handles1, labels1 = self.ax1.get_legend_handles_labels()
                handles2, labels2 = self.ax2.get_legend_handles_labels()
                
                # Combine them and create a single legend
                legend = self.ax1.legend(
                    handles1 + handles2, 
                    labels1 + labels2, 
                    loc='upper left', 
                    facecolor=DARKER_BG, 
                    edgecolor=BORDER_COLOR
                )
                
                for text in legend.get_texts():
                    text.set_color(TEXT_COLOR)
            else:
                # For preview mode, also show both HR and RR in legend
                handles1, labels1 = self.ax1.get_legend_handles_labels()
                handles2, labels2 = self.ax2.get_legend_handles_labels()
                
                if handles1 or handles2:
                    legend = self.ax1.legend(
                        handles1 + handles2, 
                        labels1 + labels2, 
                        loc='upper left', 
                        facecolor=DARKER_BG, 
                        edgecolor=BORDER_COLOR
                    )
                    
                    for text in legend.get_texts():
                        text.set_color(TEXT_COLOR)

            # Add a vertical line at recording start time if recording
            if self.recording and hasattr(self, 'recording_start_time'):
                if current_time - self.recording_start_time <= 100:  # Only if recording start is within view
                    self.ax1.axvline(
                        x=self.recording_start_time, 
                        color=SUCCESS_COLOR, 
                        linestyle='--', 
                        alpha=0.8,
                        label='Recording Start'
                    )
            
            # Add a vertical line at recording stop time if available
            if hasattr(self, 'recording_stop_time') and not self.recording:
                if current_time - self.recording_stop_time <= 100:  # Only if stop time is within view
                    self.ax1.axvline(
                        x=self.recording_stop_time, 
                        color=ERROR_COLOR, 
                        linestyle='--', 
                        alpha=0.8,
                        label='Recording Stop'
                    )

            # Add marked timestamps as vertical lines
            for ts in self.marked_timestamps:
                if current_time - ts <= 100:  # Only if timestamp is within view
                    self.ax1.axvline(x=ts, color='m', linestyle=':', alpha=0.7, label='Marked Timestamp' if ts == self.marked_timestamps[0] else "")
                    
            # Add completed intervals as shaded regions
            for i, (start, end) in enumerate(self.intervals):
                if current_time - end <= 100:  # Only if interval end is within view
                    self.ax1.axvspan(start, end, alpha=0.2, color='cyan', 
                                   label='Completed Intervals' if i == 0 else "")
                    
            # Add current active interval as shaded region
            if self.current_interval_start is not None:
                if current_time - self.current_interval_start <= 100:  # Only if interval start is within view
                    self.ax1.axvspan(self.current_interval_start, current_time, alpha=0.3, color='yellow',
                                   label='Active Interval')

            # Draw the plot
            self.canvas_plot.draw()

        except Exception as e:
            print(f"Error updating plot: {str(e)}")

    def test_connection(self):
        """Test the connection to the Polar H10 device"""
        if not self.connected or not self.client:
            messagebox.showwarning("Not Connected", "Please connect to a Polar H10 device first.")
            return

        print("\n--- Starting Connection Test ---")
        print("1. Testing device connection...")

        if self.client.is_connected:
            print("✓ Device is connected")
        else:
            print("✗ Device is NOT connected")
            messagebox.showerror("Connection Test", "Device is not connected. Please reconnect.")
            return

        print("2. Testing data reception...")
        if len(self.data_buffers['HeartRate']) > 0:
            last_hr = self.data_buffers['HeartRate'][-1][1]
            print(f"✓ Heart rate data is being received (last value: {last_hr} bpm)")
        else:
            print("✗ No heart rate data has been received")
            print("Troubleshooting tips:")
            print("- Make sure the chest strap is properly moistened")
            print("- Ensure the Polar H10 is firmly attached to the strap")
            print("- Check that the strap is positioned correctly on your chest")
            print("- Try removing and reinserting the Polar H10 from the strap")

            # Try to force a heart rate reading
            print("Attempting to force a heart rate reading...")
            threading.Thread(target=self._force_test_reading, daemon=True).start()

        if len(self.data_buffers['RRinterval']) > 0:
            last_rr = self.data_buffers['RRinterval'][-1][1]
            print(f"✓ RR interval data is being received (last value: {last_rr} ms)")
        else:
            print("ℹ No RR interval data has been received (this is optional)")

        print("3. Testing file system...")
        try:
            test_file_path = os.path.join(self.participant_folder, "test_file.txt")
            with open(test_file_path, 'w') as test_file:
                test_file.write("Test file write successful")
            os.remove(test_file_path)
            print("✓ File system is working correctly")
        except Exception as e:
            print(f"✗ File system test failed: {str(e)}")
            print("This may cause issues when recording data")

        print("\nTest Summary:")
        if self.client.is_connected and len(self.data_buffers['HeartRate']) > 0:
            print("Connection is working correctly. You can start recording data.")
            messagebox.showinfo("Connection Test", "Connection test passed! You can start recording data.")
        elif self.client.is_connected and len(self.data_buffers['HeartRate']) == 0:
            print("Device is connected but no data is being received.")
            print("Please check the positioning of the Polar H10 and chest strap.")
            messagebox.showwarning("Connection Test", "Device is connected but no data is being received. Please check the positioning of the Polar H10 and chest strap.")
        else:
            print("Connection test failed. Please reconnect the device.")
            messagebox.showerror("Connection Test", "Connection test failed. Please reconnect the device.")

        print("--- Connection Test Complete ---\n")

    def _force_test_reading(self, preview_mode=False):
        """Force a heart rate reading during the connection test or preview mode"""
        try:
            # For preview mode, use a lighter approach first
            if preview_mode:
                try:
                    # Just try to read heart rate directly
                    hr_value = self.loop.run_until_complete(self._read_heart_rate())
                    if hr_value:
                        return
                except Exception as e:
                    # If that fails, continue with standard approach
                    pass

            # Standard approach
            self.loop.run_until_complete(self._force_heart_rate_reading_loop())

            # Wait a moment to see if data arrives
            time.sleep(1 if preview_mode else 2)

            # If still no data and not in preview mode, try a more aggressive approach
            if not self.data_buffers['HeartRate'] and not preview_mode:
                print("Standard approach failed. Trying more aggressive methods...")
                self.loop.run_until_complete(self._aggressive_heart_rate_test())
        except Exception as e:
            print(f"Error in force test reading: {str(e)}")

    async def _read_heart_rate(self):
        """Read heart rate characteristic directly"""
        try:
            hr_data = await self.client.read_gatt_char(HEART_RATE_UUID)
            if hr_data and len(hr_data) > 0:
                flags = hr_data[0]
                hr_format = (flags & 0x01) == 0x01

                if hr_format:
                    hr_value = struct.unpack('<H', hr_data[1:3])[0]
                else:
                    hr_value = hr_data[1]

                # Manually call the handler with this data to process it
                self._heart_rate_handler(None, hr_data)
                return hr_value
        except Exception as e:
            print(f"Error reading heart rate directly: {str(e)}")
        return None

    async def _aggressive_heart_rate_test(self):
        """Try more aggressive methods to get heart rate data"""
        try:
            # Try to restart the entire connection
            print("Attempting to restart notifications completely...")

            # Stop all notifications
            try:
                await self.client.stop_notify(HEART_RATE_UUID)
                await self.client.stop_notify(PMD_DATA)
            except Exception as e:
                print(f"Error stopping notifications: {str(e)}")

            # Wait a moment
            await asyncio.sleep(1)

            # Try to write to the Client Characteristic Configuration Descriptor directly
            try:
                services = await self.client.get_services()
                for service in services.services.values():
                    if service.uuid.lower() == HEART_RATE_SERVICE.lower():
                        for char in service.characteristics:
                            if char.uuid.lower() == HEART_RATE_UUID.lower():
                                for descriptor in char.descriptors:
                                    if descriptor.uuid.lower() == CLIENT_CHAR_CONFIG.lower():
                                        # Write 0x0100 to enable notifications (little endian)
                                        await self.client.write_gatt_descriptor(descriptor.handle, bytearray([0x01, 0x00]))
                                        print("Enabled heart rate notifications via descriptor")
                                        break
            except Exception as e:
                print(f"Error writing to descriptor: {str(e)}")

            # Restart notifications
            await self.client.start_notify(HEART_RATE_UUID, self._heart_rate_handler)
            print("Restarted heart rate notifications")

            # Try to read heart rate directly
            try:
                hr_value = await self._read_heart_rate()
                if hr_value:
                    print(f"Direct heart rate reading: {hr_value} bpm")
            except Exception as e:
                print(f"Error reading heart rate directly: {str(e)}")

            # Wait a moment to see if data arrives
            await asyncio.sleep(2)

            # Check if we have data now
            if self.data_buffers['HeartRate']:
                print("Successfully received heart rate data after aggressive methods")
            else:
                print("Still no heart rate data received. The device may need to be reset or recharged.")
                print("Try the following:")
                print("1. Remove the Polar H10 from the strap and reinsert it")
                print("2. Ensure the battery is charged (current level: low)")
                print("3. Make sure the chest strap is properly moistened and positioned")
                print("4. Try restarting the application")

        except Exception as e:
            print(f"Error in aggressive heart rate test: {str(e)}")

    def disconnect_from_device(self):
        """Disconnect from the Polar device"""
        if self.recording:
            self.stop_recording()

        threading.Thread(target=self._disconnect_thread, daemon=True).start()

    def _disconnect_thread(self):
        try:
            # Update button appearance for disconnecting state
            self.connect_button.config(
                text="DISCONNECTING...", 
                state=tk.DISABLED,
                bg=WARNING_COLOR,
                fg=DARKER_BG
            )

            if self.client and self.client.is_connected:
                self.loop.run_until_complete(self._disconnect_from_polar())

            self.connected = False
            
            # Disable buttons with dark theme styling
            self.start_button.config(
                state=tk.DISABLED,
                bg=DARK_BG,
                fg=SECONDARY_TEXT
            )
            
            self.mark_button.config(
                state=tk.DISABLED,
                bg=DARK_BG,
                fg=SECONDARY_TEXT
            )
            
            # Disable interval buttons
            self.start_interval_button.config(
                state=tk.DISABLED,
                bg=DARK_BG,
                fg=SECONDARY_TEXT,
                text="START INTERVAL"
            )
            
            self.end_interval_button.config(
                state=tk.DISABLED,
                bg=DARK_BG,
                fg=SECONDARY_TEXT
            )
            
            # Reset interval state
            self.current_interval_start = None
            
            # Update session status if we have one
            if self.current_participant_id:
                self.session_status_label.config(
                    text=f"Session: {self.current_participant_id} (disconnected)",
                    fg=WARNING_COLOR
                )
            
            # Reset connect button with dark theme styling
            self.connect_button.config(
                text="CONNECT", 
                state=tk.NORMAL, 
                command=self.connect_to_device,
                bg=ACCENT_COLOR,
                fg=DARKER_BG,
                activebackground=DARK_BG,
                activeforeground=ACCENT_COLOR
            )
            
            self.status_var.set("Status: Disconnected")
            
            # Close any open file handles
            self._close_recording_files()
            
            messagebox.showinfo("Disconnected", "Disconnected from Polar H10")
        except Exception as e:
            messagebox.showerror("Disconnection Error", f"Error during disconnection: {str(e)}")
            # Reset connect button with dark theme styling
            self.connect_button.config(
                text="CONNECT", 
                state=tk.NORMAL, 
                command=self.connect_to_device,
                bg=ACCENT_COLOR,
                fg=DARKER_BG,
                activebackground=DARK_BG,
                activeforeground=ACCENT_COLOR
            )

    async def _disconnect_from_polar(self):
        """Disconnect from the Polar device"""
        if self.client:
            # Stop notifications
            try:
                await self.client.stop_notify(HEART_RATE_UUID)
                await self.client.stop_notify(PMD_DATA)
            except Exception as e:
                print(f"Error stopping notifications: {str(e)}")

            # Disconnect
            try:
                await self.client.disconnect()
                print("Disconnected from Polar device")
            except Exception as e:
                print(f"Error disconnecting: {str(e)}")
            
            # Clear the client
            self.client = None
            
        # Clean up LSL streams
        self._cleanup_lsl_streams()


class LSLDataAnalyzer:
    def __init__(self, parent):
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        # Section title with icon-like prefix
        title_frame = tk.Frame(self.parent, bg=DARKER_BG)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        section_title = tk.Label(
            title_frame, 
            text="◉ ANALYSIS MODULE", 
            font=("Segoe UI", 16, "bold"), 
            fg=ACCENT_COLOR, 
            bg=DARKER_BG,
            anchor="w"
        )
        section_title.pack(fill=tk.X)

        # Participant ID section with modern styling
        participant_frame = tk.Frame(self.parent, bg=DARKER_BG, pady=10)
        participant_frame.pack(fill=tk.X)
        
        self.participant_id_label = tk.Label(
            participant_frame, 
            text="PARTICIPANT ID", 
            font=("Segoe UI", 10), 
            bg=DARKER_BG, 
            fg=SECONDARY_TEXT,
            anchor="w"
        )
        self.participant_id_label.pack(fill=tk.X)
        
        self.participant_id_entry = tk.Entry(
            participant_frame, 
            font=("Segoe UI", 14),
            bg=DARK_BG,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,  # Cursor color
            relief=tk.FLAT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1
        )
        self.participant_id_entry.pack(fill=tk.X, pady=(5, 0))
        
        # Bind Enter key to load data
        self.participant_id_entry.bind('<Return>', lambda event: self.load_data())

        # Load Data Button with modern styling
        button_frame = tk.Frame(self.parent, bg=DARKER_BG, pady=10)
        button_frame.pack(fill=tk.X)
        
        self.load_button = tk.Button(
            button_frame, 
            text="LOAD DATA", 
            font=("Segoe UI", 12, "bold"),
            bg=ACCENT_COLOR,
            fg=DARKER_BG,
            activebackground=DARK_BG,
            activeforeground=ACCENT_COLOR,
            relief=tk.FLAT,
            padx=20,
            pady=10,
            command=self.load_data
        )
        self.load_button.pack(fill=tk.X, pady=5)

        # Results Display with modern styling
        results_frame = tk.Frame(self.parent, bg=DARKER_BG, pady=10)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        results_header = tk.Label(
            results_frame, 
            text="ANALYSIS RESULTS", 
            font=("Segoe UI", 10), 
            bg=DARKER_BG, 
            fg=SECONDARY_TEXT,
            anchor="w"
        )
        results_header.pack(fill=tk.X)
        
        self.results_text = tk.Text(
            results_frame, 
            wrap=tk.WORD, 
            font=("Segoe UI", 12),
            bg=DARK_BG,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            relief=tk.FLAT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=10,
            pady=10
        )
        self.results_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

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
                
        # Laden der Intervalle
        intervals = []
        intervals_filename = os.path.join(participant_folder, "intervals.csv")
        if os.path.exists(intervals_filename):
            with open(intervals_filename, 'r') as intervals_file:
                reader = csv.reader(intervals_file)
                next(reader)  # Header überspringen
                intervals = [(float(row[0]), float(row[1]), float(row[2])) for row in reader]

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

        # Analysieren der Daten mit Episoden-Erkennung
        self.analyze_data(data_buffers, marked_timestamps, intervals)

    def analyze_data(self, data_buffers, marked_timestamps, intervals):
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
                    
                # Analyse der Intervalle innerhalb dieses Segments
                if intervals:
                    segment_intervals = []
                    for start_interval, end_interval, duration in intervals:
                        # Check if interval overlaps with this segment
                        if (start_interval <= timestamps[-1] and end_interval >= timestamps[0]):
                            # Get data within this interval
                            interval_values = [value for ts, value in segment if start_interval <= ts <= end_interval]
                            if interval_values:
                                mean_interval = np.mean(interval_values)
                                median_interval = np.median(interval_values)
                                min_interval = np.min(interval_values)
                                max_interval = np.max(interval_values)
                                std_dev_interval = np.std(interval_values)
                                iqr_interval = np.percentile(interval_values, 75) - np.percentile(interval_values, 25)
                                rmssd_interval = None
                                sdnn_interval = None
                                if stream == "RRinterval" and len(interval_values) > 1:
                                    rr_diff = np.diff(interval_values)
                                    rmssd_interval = np.sqrt(np.mean(rr_diff ** 2)) if len(rr_diff) > 0 else None
                                    sdnn_interval = np.std(interval_values, ddof=1)
                                
                                segment_intervals.append((start_interval, end_interval, duration, mean_interval, 
                                                       median_interval, min_interval, max_interval, std_dev_interval, 
                                                       iqr_interval, rmssd_interval, sdnn_interval))
                    
                    # Output interval results
                    if segment_intervals:
                        self.results_text.insert(tk.END, f"  Interval Analysis:\n")
                        for i, (start_interval, end_interval, duration, mean_interval, median_interval, min_interval, 
                               max_interval, std_dev_interval, iqr_interval, rmssd_interval, sdnn_interval) in enumerate(segment_intervals):
                            self.results_text.insert(tk.END, f"    Interval {i + 1} ({start_interval:.2f} - {end_interval:.2f}s):\n")
                            self.results_text.insert(tk.END, f"      Duration: {duration:.2f} seconds\n")
                            self.results_text.insert(tk.END, f"      Mean: {mean_interval:.2f}\n")
                            self.results_text.insert(tk.END, f"      Median: {median_interval:.2f}\n")
                            self.results_text.insert(tk.END, f"      Min: {min_interval:.2f}\n")
                            self.results_text.insert(tk.END, f"      Max: {max_interval:.2f}\n")
                            self.results_text.insert(tk.END, f"      Variability (Standard Deviation): {std_dev_interval:.2f}\n")
                            self.results_text.insert(tk.END, f"      Interquartile Range (IQR): {iqr_interval:.2f}\n")
                            if rmssd_interval is not None:
                                self.results_text.insert(tk.END, f"      RMSSD: {rmssd_interval:.2f}\n")
                            if sdnn_interval is not None:
                                self.results_text.insert(tk.END, f"      SDNN: {sdnn_interval:.2f}\n")
                            self.results_text.insert(tk.END, f"\n")
                    else:
                        self.results_text.insert(tk.END, f"  No Intervals Available for This Segment\n\n")
                else:
                    self.results_text.insert(tk.END, f"  No Intervals Available for This Segment\n\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = LSLGui(root)
    root.mainloop()