"""
This file contains the main application for the Polar H10 Recorder & Analyzer.

The application provides a Graphical User Interface (GUI) for:
- Connecting to Polar H10 devices via Bluetooth Low Energy (BLE).
- Recording physiological data (Heart Rate, RR intervals).
- Real-time plotting of incoming data.
- Saving recorded data to CSV files.
- Analyzing previously recorded data.
"""
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
from pylsl import local_clock

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
    """
    The main Tkinter application class for the Polar H10 Recorder & Analyzer.

    This class sets up the main application window, configures its theme, and
    arranges the primary user interface frames. It is responsible for
    instantiating and managing the `PolarStreamRecorder` (for data acquisition)
    and `LSLDataAnalyzer` (for data analysis) components, which form the
    core functionalities of the application.
    """
    def __init__(self, master):
        """
        Initializes the main application window and its components.

        This constructor sets up the main Tkinter window, configures the visual
        theme, creates the header (title and subtitle), and content frames.
        It then initializes the `PolarStreamRecorder` and `LSLDataAnalyzer`
        classes, placing them within their respective frames in the UI.
        It also sets up the handler for the window closing event.

        Parameters:
            master (tk.Tk): The root Tkinter window for the application.
        """
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
        """
        Configures the ttk theme for a modern look and feel.

        This method customizes the appearance of various ttk widgets to ensure
        a consistent and modern visual style throughout the application.
        It styles components such as TButton, TCombobox, TEntry, and TScrollbar,
        defining their background colors, foreground colors, borders, and other
        visual attributes to match the application's dark theme.
        """
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
        """
        Handles the window closing event (WM_DELETE_WINDOW protocol).

        This method is called when the user attempts to close the main application
        window. It first checks if the `PolarStreamRecorder` is connected to a
        Polar H10 device. If a connection is active, it attempts to gracefully
        disconnect the device to ensure proper termination of Bluetooth communications
        and data saving processes. After attempting disconnection (or if no
        connection was active), it destroys the main Tkinter window, closing the
        application.
        """
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
    """
    Manages the recording functionality of the Polar H10 Recorder & Analyzer.

    This class is responsible for:
    - Setting up the UI elements for participant ID, device scanning/selection,
      recording controls (connect, start/stop, mark timestamp), status display,
      console output, and real-time data plots.
    - Handling Bluetooth Low Energy (BLE) communication with the Polar H10
      device, including scanning for devices, establishing connections,
      managing disconnections, and receiving data.
    - Processing and displaying incoming heart rate (HR) and RR interval data.
    - Managing the recording of this data to CSV files in a participant-specific
      folder.
    - Updating a live plot to visualize the physiological data in real-time.
    """
    def __init__(self, parent):
        """
        Initializes the PolarStreamRecorder component.

        Sets up initial state variables such as recording status, data buffers for
        HR and RR intervals, and the BLE client. It also redirects stdout
        to the application's GUI console for in-app logging and calls the
        `setup_ui()` method to build the user interface for this recorder module.

        Parameters:
            parent (tk.Frame): The parent Tkinter frame in which this recorder's
                               UI elements will be built.
        """
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
        self.participant_folder = None
        self.loop = asyncio.new_event_loop()
        self.plot_update_scheduled = False  # Flag to track if plot updates are scheduled

        # Create a status label
        self.status_var = tk.StringVar()
        self.status_var.set("Status: Not connected")

        # Redirect stdout to our console
        self.stdout_original = sys.stdout
        sys.stdout = self

        self.setup_ui()

    def write(self, text):
        """
        Redirects stdout to the application's console display in the GUI.

        This method is part of the mechanism to show `print()` statements and
        other stdout messages within the Tkinter console widget.

        Parameters:
            text (str): The text string to be written to the console.

        Returns:
            The result of the original `stdout.write` method.
        """
        if hasattr(self, 'console'):
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.parent.after(0, lambda: self.console.insert(tk.END, f"[{timestamp}] {text}"))
            self.parent.after(0, lambda: self.console.see(tk.END))
        return self.stdout_original.write(text)

    def flush(self):
        """
        Provides the flush method required for stdout redirection.

        This method is part of the mechanism to ensure that `stdout` messages
        are properly handled when redirected to the GUI console.

        Returns:
            The result of the original `stdout.flush` method.
        """
        return self.stdout_original.flush()

    def setup_ui(self):
        """
        Creates and arranges all UI elements for the recording module.

        This includes setting up input fields for participant ID, buttons for
        device scanning, connection, starting/stopping recording, and marking
        timestamps. It also creates labels for status display, a scrolled text
        widget for console output, and a matplotlib canvas for plotting
        real-time physiological data.
        """
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

        # Console output with modern styling
        console_frame = tk.Frame(self.parent, bg=DARKER_BG, pady=10)
        console_frame.pack(fill=tk.X)

        console_header = tk.Label(
            console_frame, 
            text="CONSOLE OUTPUT", 
            font=("Segoe UI", 10), 
            bg=DARKER_BG, 
            fg=SECONDARY_TEXT,
            anchor="w"
        )
        console_header.pack(fill=tk.X)
        
        self.console = scrolledtext.ScrolledText(
            console_frame, 
            height=5, 
            font=("Cascadia Code", 9),
            bg=DARK_BG,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            relief=tk.FLAT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1
        )
        self.console.pack(fill=tk.X, expand=True, pady=(5, 0))

        print("Application started. Ready to connect to Polar H10.")

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
        """
        Initiates the BLE device scan.

        This method is called when the 'Scan' button is pressed. It disables the
        scan button to prevent multiple concurrent scans and starts the
        `_scan_devices_thread` in a new thread to perform the actual scanning
        asynchronously, keeping the GUI responsive.
        """
        self.scan_button.config(text="Scanning...", state=tk.DISABLED)
        threading.Thread(target=self._scan_devices_thread, daemon=True).start()

    def _scan_devices_thread(self):
        """
        Performs asynchronous BLE scanning for Polar devices.

        This method runs in a separate thread. It calls the asynchronous
        `_scan_for_polar_devices` method to discover nearby Polar H10 devices
        using `BleakScanner`. Upon completion, it updates the device dropdown
        list in the UI with the names and addresses of found devices. It also
        handles potential errors during the scanning process and re-enables the
        scan button.
        """
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
        """
        Performs the actual BLE scan for Polar devices.

        This asynchronous method uses `BleakScanner` to discover nearby Bluetooth
        Low Energy devices. It filters the discovered devices, looking for those
        whose names contain "Polar".

        Returns:
            list[str]: A list of strings, where each string represents a found
                       Polar device in the format "Device Name (Device Address)".
                       Example: "Polar H10 A1B2C3D4 (XX:XX:XX:XX:XX:XX)".
        """
        devices = []
        scanner = BleakScanner()
        discovered_devices = await scanner.discover(timeout=5.0)

        for device in discovered_devices:
            if device.name and ("Polar" in device.name or "polar" in device.name):
                devices.append(f"{device.name} ({device.address})")

        return devices

    def connect_to_device(self):
        """
        Initiates the connection to the selected Polar H10 device.

        This method is called when the 'Connect' button is pressed. It retrieves
        the participant ID from the input field and the selected device from the
        dropdown menu. It then sets up the participant-specific data folder,
        checking for necessary write permissions using `_check_folder_permissions`.
        If permissions are granted, it starts the `_connect_thread` in a new
        thread to handle the asynchronous BLE connection process.
        """
        participant_id = self.participant_id_entry.get().strip()
        if not participant_id:
            messagebox.showwarning("Participant ID Missing", "Please enter a Participant ID.")
            return

        selected_device = self.device_var.get()
        if not selected_device:
            messagebox.showwarning("Device Not Selected", "Please select a Polar device.")
            return

        self.participant_folder = os.path.join("Participant_Data", f"Participant_{participant_id}")

        # Check folder permissions before proceeding
        if not self._check_folder_permissions():
            return

        os.makedirs(self.participant_folder, exist_ok=True)

        # Extract device address from selection
        self.device_address = selected_device.split("(")[1].split(")")[0]

        # Start connection in a separate thread to avoid blocking the UI
        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _check_folder_permissions(self):
        """
        Checks if the application has write permissions to the target folder.

        This method attempts to create the participant-specific data directory
        (`Participant_Data/Participant_<ID>`) if it doesn't exist. It then
        tries to write and delete a temporary test file within this directory
        to confirm write permissions.

        Returns:
            bool: True if write permissions are confirmed, False otherwise.
                  If permissions are denied, an error message is shown to the user.
        """
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
        """
        Manages the asynchronous BLE connection process in a separate thread.

        This method calls `_connect_to_polar()` to perform the actual BLE
        connection. It updates UI elements (e.g., connect/disconnect button state
        and text, status label) based on the outcome of the connection attempt.
        If the connection is successful, it enables recording controls,
        starts periodic data requests (for preview), and schedules regular
        updates for the live data plot.
        """
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
            
            # Start updating the plot immediately
            self.update_plot()
            # Schedule regular plot updates
            self._schedule_plot_updates()

            messagebox.showinfo("Connected", "Connected to Polar H10 successfully! Data preview has started automatically.")
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
        """
        Schedules regular updates to the live data plot.

        If the device is connected, this method calls `update_plot()` to refresh
        the plot and then uses `self.parent.after()` to schedule itself to be
        called again after a short interval (e.g., 500ms), creating a loop
        for continuous plot updates.
        """
        if self.connected:
            self.update_plot()
            # Update plot every 500ms
            self.parent.after(500, self._schedule_plot_updates)

    def _periodic_data_request(self):
        """
        Periodically requests data to ensure continuous data flow for preview.

        This method runs in a separate thread while the device is connected.
        It checks if recent data has been received. If no data has arrived
        within a certain timeframe (e.g., 3 seconds), it attempts to force a
        test reading from the device. This helps maintain an active data flow,
        especially for the live preview before recording starts.
        """
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
        """
        Handles the core BLE connection logic to the Polar H10 device.

        This asynchronous method uses `BleakClient` to establish a connection
        to the specified Polar H10 device address. Upon successful connection,
        it attempts to:
        1. Read the device's battery level.
        2. Set up notifications for the Heart Rate characteristic (UUID `00002a37-xxxx`)
           to receive HR and RR interval data.
        3. Set up notifications for the PMD (Polar Measurement Data) characteristic
           (UUID `FB005C82-xxxx`) to potentially receive ECG data (which can also
           be a source for RR intervals).
        4. Start a data watchdog thread (`_data_watchdog`) to monitor data reception.

        Raises:
            Exception: If any part of the connection process (device connection,
                       characteristic discovery, notification setup) fails.
        """
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
        """
        Attempts to force an initial heart rate reading after connection.

        This method is typically called after setting up notifications. It waits
        briefly and, if no heart rate data has been received, calls
        `_force_heart_rate_reading_loop()` to try and elicit data from the device.
        This helps ensure that the connection is active and data is flowing.
        """
        try:
            time.sleep(2)  # Wait for notifications to be set up
            if not self.data_buffers['HeartRate']:
                print("No heart rate data received yet, forcing a reading...")
                self.loop.run_until_complete(self._force_heart_rate_reading_loop())
        except Exception as e:
            print(f"Error forcing initial reading: {str(e)}")

    async def _force_heart_rate_reading_loop(self):
        """
        Asynchronously tries multiple approaches to obtain heart rate data.

        This method attempts several strategies if initial data reception fails:
        1. Directly reads the heart rate characteristic.
        2. Tries to restart notifications (implementation might be in `_restart_notifications`).
        3. Reads the battery level to potentially keep the connection active.
        4. Writes to a control characteristic (PMD_CONTROL) to "wake up" the device.
        This is used to troubleshoot connections where data isn't flowing automatically.
        """
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
        """
        Monitors data reception and provides feedback if data flow stops.

        This method runs in a thread to monitor data reception. If no HR data
        is received shortly after connection or if data flow stops, it updates
        the status, prints troubleshooting tips, and may attempt to force a
        reading.
        """
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
        """
        Callback invoked when new data is received on the Heart Rate characteristic.

        Parses the HR data (HR value, RR intervals if present), updates data
        buffers, updates the status label, and if recording is active, writes
        data to CSV files using `_write_hr_data_to_file` and
        `_write_rr_data_to_file`.

        Parameters:
            sender: The sender of the notification (characteristic handle or similar).
            data (bytearray): The raw byte data received from the BLE device.
        """
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
        """
        Writes heart rate data to the `HeartRate_recording.csv` file.

        Manages file handle caching and error handling during writes.

        Parameters:
            timestamp (float): The LSL timestamp for the data point.
            hr_value (int): The heart rate value in BPM.
        """
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
        """
        Writes RR interval data to the `RRinterval_recording.csv` file.

        Manages file handle caching and error handling.

        Parameters:
            timestamp (float): The LSL timestamp for the data point.
            rr_value (float): The RR interval value in milliseconds.
        """
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
        """
        Callback for PMD (Polar Measurement Data), which could include ECG.

        Notes that the current implementation might be simplified and
        primarily relies on HR service for RR intervals.

        Parameters:
            sender: The sender of the notification.
            data (bytearray): The raw PMD data.
        """
        # This is a simplified handler - full implementation would parse the PMD data format
        # For now, we're focusing on heart rate and RR intervals from the standard BLE service
        pass

    def toggle_recording(self):
        """
        Starts or stops the data recording session.

        Updates UI elements (button text/state, status) accordingly.
        Calls `_setup_recording_files` when starting and `stop_recording`
        when stopping.
        """
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
                
                # Update button appearance for recording state
                self.start_button.config(
                    text="STOP RECORDING",
                    bg=ERROR_COLOR,
                    fg=DARKER_BG,
                    activebackground=DARK_BG,
                    activeforeground=ERROR_COLOR
                )
                
                # Update status with recording indicator
                self.status_var.set(f"Status: Connected | ● RECORDING")
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
            # Stop recording and update UI
            self.stop_recording()
            
            # Reset button appearance
            self.start_button.config(
                text="START RECORDING",
                bg=DARK_BG,
                fg=TEXT_COLOR,
                activebackground=DARKER_BG,
                activeforeground=TEXT_COLOR
            )
            
            self.status_var.set(f"Status: Connected | Recording stopped")

    def _setup_recording_files(self):
        """
        Prepares CSV files for the current recording session.

        Creates `HeartRate_recording.csv`, `RRinterval_recording.csv`, and
        `marked_timestamps.csv` in the participant's data folder.
        Writes headers and starts `_monitor_recording`.
        """
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

            print(f"Recording files created in {self.participant_folder}")

            # Start a thread to monitor recording
            threading.Thread(target=self._monitor_recording, daemon=True).start()

        except Exception as e:
            print(f"Error in setup_recording_files: {str(e)}")
            # Notify the user of the error
            self.parent.after(0, lambda: messagebox.showerror("Recording Error", 
                                                             f"Failed to set up recording files: {str(e)}"))

    def _monitor_recording(self):
        """
        Runs in a thread after recording starts to check data writing.

        Checks if data is actually being written to the files, providing
        a warning if not.
        """
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
        """
        Finalizes the recording session.

        Sets recording flag to False, closes recording file handles,
        saves marked timestamps, and verifies recorded files. Updates the plot.
        """
        # Store the recording stop time
        self.recording_stop_time = local_clock()
        print(f"Recording stop time: {self.recording_stop_time}")
        
        self.recording = False
        self.recording_event.clear()
        
        # Close file handles if they're open
        self._close_recording_files()

        self.save_marked_timestamps()

        # Verify the recording files
        self._verify_recording_files()
        
        # Force an immediate plot update to show the stop line
        self.update_plot()

    def _close_recording_files(self):
        """
        Safely closes any open recording file handles (`_hr_file`, `_rr_file`).
        """
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
        """
        Checks created recording files for existence and content.

        Verifies whether they contain data beyond just headers. Prints a
        summary and shows a message box to the user.
        """
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
        """
        Records the current `local_clock()` timestamp.

        This happens when the "Mark Timestamp" button is pressed during an
        active recording.
        """
        if self.recording:
            timestamp = local_clock()
            self.marked_timestamps.append(timestamp)
            messagebox.showinfo("Timestamp Marked", f"Marked timestamp at {timestamp}")
        else:
            messagebox.showwarning("Recording Not Active", "Start recording before marking timestamps.")

    def save_marked_timestamps(self):
        """
        Saves collected `marked_timestamps` to `marked_timestamps.csv`.

        This is for the current participant.
        """
        if not self.marked_timestamps:
            return

        marked_filename = os.path.join(self.participant_folder, "marked_timestamps.csv")
        with open(marked_filename, 'w', newline='') as marked_file:
            csv_writer = csv.writer(marked_file)
            csv_writer.writerow(['Timestamp'])
            csv_writer.writerows([[ts] for ts in self.marked_timestamps])

    def update_plot(self):
        """
        Redraws the Matplotlib plot with the latest HR and RR data.

        Handles different display styles for pre-recording, recording, and
        post-recording states. Shows marked timestamps and recording
        start/stop lines.
        """
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
                    self.ax1.axvline(x=ts, color='m', linestyle=':', alpha=0.7)

            # Draw the plot
            self.canvas_plot.draw()

        except Exception as e:
            print(f"Error updating plot: {str(e)}")

    def test_connection(self):
        """
        Performs checks for device connection, data reception, and file system.

        Provides feedback to the user via console and message boxes.
        May call `_force_test_reading`.
        """
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
        """
        Attempts to force a heart rate reading.

        Used by `test_connection` or `_periodic_data_request`. Can use
        different approaches based on `preview_mode`.

        Parameters:
            preview_mode (bool): If True, may use a lighter approach initially.
        """
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
        """
        Asynchronously attempts to read the heart rate characteristic directly.

        Returns:
            int or None: The heart rate value if read successfully, else None.
        """
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
        """
        Asynchronously tries more forceful methods to get HR data.

        This can include restarting notifications completely if initial
        attempts fail.
        """
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
        """
        Initiates disconnection from Polar device by starting _disconnect_thread.

        Stops recording if active.
        """
        if self.recording:
            self.stop_recording()

        threading.Thread(target=self._disconnect_thread, daemon=True).start()

    def _disconnect_thread(self):
        """
        Runs in a thread to handle asynchronous BLE disconnection.

        Uses `_disconnect_from_polar()` and updates UI elements.
        """
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
        """
        Asynchronously stops BLE notifications and disconnects the BleakClient.
        """
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


class LSLDataAnalyzer:
    """
    Manages the data analysis component of the Polar H10 Recorder & Analyzer.

    This class is responsible for:
    - Setting up the UI elements for selecting a participant ID and loading their
      recorded data.
    - Displaying analysis results in a text area.
    - Loading recorded heart rate, RR interval, and marked timestamp data from
      CSV files stored in participant-specific folders.
    - Performing statistical analysis on the loaded data. This includes
      calculating overall metrics for entire recording segments and also
      performing segment-based analysis using any timestamps that were marked
      during the recording session.
    - Calculating and displaying various metrics such as mean, median, min/max values,
      standard deviation, Interquartile Range (IQR), Root Mean Square of
      Successive Differences (RMSSD), and Standard Deviation of NN intervals (SDNN).
    """
    def __init__(self, parent):
        """
        Initializes the LSLDataAnalyzer component.

        This constructor calls the `setup_ui()` method to build the user
        interface for this data analysis module.

        Parameters:
            parent (tk.Frame): The parent Tkinter frame in which this analyzer's
                               UI elements will be built.
        """
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        """
        Creates and arranges all UI elements for the data analysis module.

        This includes setting up an input field for the participant ID, a
        "Load Data" button to trigger the data loading and analysis process,
        and a scrolled text area where the analysis results will be displayed.
        The UI elements are styled to match the application's theme.
        """
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
        """
        Loads recorded data for the specified participant ID from CSV files.

        This method is triggered by the "Load Data" button. It first clears any
        previous results from the results text area. It then reads the participant
        ID entered by the user.
        It constructs file paths to `HeartRate_recording.csv`,
        `RRinterval_recording.csv`, and `marked_timestamps.csv` within the
        participant's data folder (e.g., `Participant_Data/Participant_<ID>/`).
        Data is loaded from these CSV files. If files or the folder are not
        found, appropriate error messages are displayed to the user.
        Finally, if data is successfully loaded, it calls the `analyze_data()`
        method to perform and display the statistical analysis.
        """
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

        # Analysieren der Daten mit Episoden-Erkennung
        self.analyze_data(data_buffers, marked_timestamps)

    def analyze_data(self, data_buffers, marked_timestamps):
        """
        Performs and displays the statistical analysis of the loaded physiological data.

        This method processes the data for each stream ('HeartRate', 'RRinterval')
        found in the `data_buffers`.
        Data is first segmented based on significant pauses (defined as more than
        10 seconds between consecutive data points).
        For each identified segment, and also for specific 'episodes' within these
        segments (demarcated by the `marked_timestamps`), it calculates a suite of
        statistical metrics. These metrics include:
        - Mean, median, minimum, and maximum values.
        - Standard deviation and Interquartile Range (IQR).
        - For 'RRinterval' data, it also calculates RMSSD (Root Mean Square of
          Successive Differences) and SDNN (Standard Deviation of NN intervals).
        - Duration of each segment/episode.
        The calculated statistics are then formatted and displayed in the results
        text area of the UI.

        Parameters:
            data_buffers (dict): A dictionary where keys are stream names (e.g.,
                                 'HeartRate', 'RRinterval') and values are lists
                                 of tuples, each tuple being (timestamp, value).
            marked_timestamps (list): A list of float timestamps that were marked
                                      by the user during the recording session. These
                                      are used to define specific episodes for analysis.
        """
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