import os
import tkinter as tk
from tkinter import messagebox, filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time
import json
from datetime import datetime

SETUP_FILE = "setup.json"  # Define the file name for storing setup

class FileMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FileMonitorOI")
        self.root.geometry("400x300")

        # Create and position buttons
        self.config_button = tk.Button(root, text="Config", command=self.open_config_window)
        self.config_button.pack(pady=10)

        self.history_button = tk.Button(root, text="File History", command=self.show_file_history)
        self.history_button.pack(pady=10)

        self.save_button = tk.Button(root, text="Save Setup", command=self.save_setup)
        self.save_button.pack(pady=10)

        # Variables to store alarms and file history
        self.folder_to_watch = None
        self.alarms = []  # List to store alarms
        self.file_history = []  # Stores file history (filename, timestamp, file size)
        self.config_window_open = False  # Track if config window is open
        self.config_window = None  # Track the actual config window instance

        # Load setup if available
        self.load_setup()

        # Ensure proper shutdown when the window is closed
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_config_window(self):
        if self.config_window_open and self.config_window is not None:
            self.config_window.destroy()  # Close any existing config window

        # Open a new window to display and configure alarms
        self.config_window_open = True
        self.config_window = tk.Toplevel(self.root)
        self.config_window.title("Configure Alarms")
        self.config_window.geometry("400x300")
        self.config_window.protocol("WM_DELETE_WINDOW", lambda: self.close_config_window(self.config_window))

        # Create a container frame to hold the alarms
        alarm_frame = tk.Frame(self.config_window)
        alarm_frame.pack(fill="both", expand=True)

        # If there are no alarms, display a message and the "Add Alarm" button
        if not self.alarms:
            no_alarm_label = tk.Label(alarm_frame, text="No alarms configured.")
            no_alarm_label.pack(pady=10)

        # Display existing alarms in rows (stack vertically)
        for i, alarm in enumerate(self.alarms):
            alarm_row = tk.Frame(alarm_frame)  # Create a frame for each alarm row
            alarm_row.pack(fill="x", pady=5)  # Stack vertically

            # Checkbox (ticker) to toggle the alarm on/off
            alarm_checkbox = tk.Checkbutton(
                alarm_row,
                text="On/Off",
                variable=alarm["active"],
                command=lambda idx=i: self.toggle_alarm(idx)
            )
            alarm_checkbox.pack(side="left", padx=5)

            # Delete Button
            delete_button = tk.Button(
                alarm_row,
                text="Delete",
                command=lambda idx=i: self.delete_alarm(idx)
            )
            delete_button.pack(side="left", padx=5)

            # Alarm Label
            alarm_label = tk.Label(alarm_row, text=f"{alarm['folder']}")
            alarm_label.pack(side="left", padx=5)

        # Add Alarm button at the bottom of the window to add new alarms
        add_alarm_button = tk.Button(alarm_frame, text="Add Alarm", command=self.add_alarm)
        add_alarm_button.pack(pady=10)

    def delete_alarm(self, alarm_index):
        """Delete an alarm and refresh the config window."""
        alarm = self.alarms[alarm_index]
        self.stop_monitoring(alarm)
        del self.alarms[alarm_index]  # Remove the alarm from the list
        self.open_config_window()  # Refresh the config window

    def close_config_window(self, config_window):
        """Close the config window and reset the state."""
        config_window.destroy()
        self.config_window_open = False

    def add_alarm(self):
        # Open a dialog to select a folder for the new alarm
        folder = filedialog.askdirectory(title="Select Folder to Monitor")
        if folder:
            # Add the selected folder as a new alarm
            new_alarm = {
                "folder": folder,
                "active": tk.BooleanVar(value=False),
                "popup": None,
                "observer": Observer(),  # Create a new observer for each alarm
                "files": {}  # Dictionary to track files and their sizes
            }
            self.alarms.append(new_alarm)
            messagebox.showinfo("Alarm Added", f"Alarm for folder '{folder}' added.")
            self.open_config_window()  # Reopen the config window to refresh the list of alarms

    def toggle_alarm(self, alarm_index):
        # Toggle the monitoring for the specified alarm based on the checkbox state
        alarm = self.alarms[alarm_index]
        if alarm["active"].get():
            self.start_monitoring(alarm)
        else:
            self.stop_monitoring(alarm)

    def start_monitoring(self, alarm):
        # Show the alarm popup immediately, even if no file is present
        self.show_alarm_popup(alarm, "No file yet", changing=True)

        # Start monitoring the folder with the alarm's observer
        event_handler = FileChangeHandler(self, alarm)
        alarm["observer"].schedule(event_handler, alarm["folder"], recursive=True)

        # Start the observer (each alarm has its own observer)
        if not alarm["observer"].is_alive():
            alarm["observer"].start()

    def stop_monitoring(self, alarm):
        # Close the alarm popup and stop monitoring the folder
        if alarm["popup"]:
            alarm["popup"].destroy()
            alarm["popup"] = None

        # Stop and join the observer (if active)
        if alarm["observer"].is_alive():
            alarm["observer"].stop()
            alarm["observer"].join()

    def show_alarm_popup(self, alarm, file_name, changing):
        # Display the alarm window
        if not alarm["popup"]:
            alarm["popup"] = tk.Toplevel(self.root)
            alarm["popup"].title("File Alarm")
            alarm["popup"].geometry("500x300")
            alarm["popup"].attributes('-topmost', True)  # Keep the popup on top
            alarm["popup"].overrideredirect(True)  # Remove title bar to hide header

            # Enable manual resizing by right-clicking and dragging
            self.enable_resizing_on_right_click(alarm["popup"])

            # Enable dragging with left-click
            self.enable_dragging_on_left_click(alarm["popup"])

            # Create a canvas for drawing text with outline
            alarm["canvas"] = tk.Canvas(alarm["popup"], bg="green")
            alarm["canvas"].pack(fill="both", expand=True)
            alarm["popup"].bind('<Configure>', lambda event, alrm=alarm: self.resize_alarm_text(event, alrm))

        # Update background color based on file change
        if changing:
            alarm["canvas"].configure(bg="#007600")
        else:
            alarm["canvas"].configure(bg="#8B0000")

        # Draw the white text with a black outline
        self.draw_text_with_outline(alarm["canvas"], file_name)

    def enable_dragging_on_left_click(self, window):
        """Allow the window to be dragged with left click."""
        def start_drag(event):
            window._drag_data = {'x': event.x, 'y': event.y}

        def do_drag(event):
            delta_x = event.x - window._drag_data['x']
            delta_y = event.y - window._drag_data['y']
            window.geometry(f"+{window.winfo_x() + delta_x}+{window.winfo_y() + delta_y}")

        window.bind("<Button-1>", start_drag)
        window.bind("<B1-Motion>", do_drag)

    def enable_resizing_on_right_click(self, window):
        """Allow the window to be resized with right click."""
        def start_resize(event):
            window._resize_data = {
                'x': event.x_root,
                'y': event.y_root,
                'width': window.winfo_width(),
                'height': window.winfo_height()
            }

        def do_resize(event):
            delta_x = event.x_root - window._resize_data['x']
            delta_y = event.y_root - window._resize_data['y']
            new_width = max(100, window._resize_data['width'] + delta_x)
            new_height = max(50, window._resize_data['height'] + delta_y)
            window.geometry(f"{new_width}x{new_height}")

        window.bind("<Button-3>", start_resize)
        window.bind("<B3-Motion>", do_resize)

    def draw_text_with_outline(self, canvas, text):
        canvas.delete("all")  # Clear the canvas first
        width, height = canvas.winfo_width(), canvas.winfo_height()
        font_size = max(int(width / 20), 10)  # Ensure a minimum font size

        # Coordinates for text placement (center)
        x = width / 2
        y = height / 2

        # Draw outline by drawing the text multiple times shifted by 1 pixel
        outline_color = "black"
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            canvas.create_text(x + dx, y + dy, text=text, font=("Arial", font_size), fill=outline_color, tags="outline", width=width)

        # Draw the main text
        main_text_color = "white"
        canvas.create_text(x, y, text=text, font=("Arial", font_size), fill=main_text_color, tags="text", width=width)

    def resize_alarm_text(self, event, alarm):
        # Redraw the text whenever the window is resized
        current_text = alarm["canvas"].itemcget("text", "text")
        self.draw_text_with_outline(alarm["canvas"], current_text)

    def show_file_history(self):
        # Display the file history in a popup window
        history_window = tk.Toplevel(self.root)
        history_window.title("File History")
        history_window.geometry("400x300")

        if not self.file_history:
            no_history_label = tk.Label(history_window, text="No files in history.")
            no_history_label.pack(pady=10)
        else:
            scrollbar = tk.Scrollbar(history_window)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            history_listbox = tk.Listbox(history_window, yscrollcommand=scrollbar.set)
            for i, file_entry in enumerate(self.file_history):
                history_listbox.insert(tk.END, f"{i+1}: {file_entry}")
            history_listbox.pack(fill="both", expand=True, padx=10, pady=10)

            scrollbar.config(command=history_listbox.yview)

    def save_setup(self):
        """Save the current setup to a JSON file."""
        setup_data = []
        for alarm in self.alarms:
            setup_data.append({
                "folder": alarm["folder"],
                "active": alarm["active"].get()
            })
        with open(SETUP_FILE, 'w') as setup_file:
            json.dump(setup_data, setup_file, indent=4)
        messagebox.showinfo("Save Setup", "Setup saved successfully.")

    def load_setup(self):
        """Load the setup from the JSON file if it exists."""
        if os.path.exists(SETUP_FILE):
            with open(SETUP_FILE, 'r') as setup_file:
                setup_data = json.load(setup_file)
                for alarm_data in setup_data:
                    new_alarm = {
                        "folder": alarm_data["folder"],
                        "active": tk.BooleanVar(value=alarm_data["active"]),
                        "popup": None,
                        "observer": Observer(),
                        "files": {}
                    }
                    self.alarms.append(new_alarm)
                    if alarm_data["active"]:
                        self.start_monitoring(new_alarm)

    def on_closing(self):
        """Handle the app shutdown cleanly when the window is closed."""
        self.save_setup()  # Automatically save the setup when closing
        for alarm in self.alarms:
            self.stop_monitoring(alarm)
        self.root.quit()  # Stops the main loop
        self.root.destroy()  # Closes the window


# Custom event handler to monitor file system events
class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, app, alarm):
        self.app = app
        self.alarm = alarm
        self.file_sizes = {}
        self.lock = threading.Lock()
        self.check_intervals = {}

    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Get current timestamp

            with self.lock:
                self.file_sizes[file_path] = file_size
                self.alarm["files"][file_path] = {
                    "name": file_name,
                    "size": self.file_sizes[file_path],
                    "timer": None
                }

            # Add file history with timestamp and size
            history_entry = f"File: {file_name}, Size: {file_size} bytes, Timestamp: {timestamp}"
            self.app.file_history.append(history_entry)

            # Show the alarm popup with green background
            self.app.root.after(0, lambda: self.app.show_alarm_popup(self.alarm, file_name, changing=True))

            # Start the size check timer
            self.start_size_check(file_path)

    def on_modified(self, event):
        if not event.is_directory:
            file_path = event.src_path
            with self.lock:
                if file_path in self.file_sizes:
                    current_size = os.path.getsize(file_path)
                    previous_size = self.file_sizes[file_path]
                    if current_size != previous_size:
                        self.file_sizes[file_path] = current_size
                        self.alarm["files"][file_path]["size"] = current_size
                        # Reset the size check timer
                        if self.alarm["files"][file_path]["timer"]:
                            self.alarm["files"][file_path]["timer"].cancel()
                        self.start_size_check(file_path)
                        # Update the popup to green
                        self.app.root.after(0, lambda: self.app.show_alarm_popup(self.alarm, os.path.basename(file_path), changing=True))

    def start_size_check(self, file_path):
        # Schedule a check after 5 seconds
        timer = threading.Timer(5.0, self.check_size, args=(file_path,))
        self.alarm["files"][file_path]["timer"] = timer
        timer.start()

    def check_size(self, file_path):
        with self.lock:
            if file_path in self.file_sizes:
                try:
                    current_size = os.path.getsize(file_path)
                    previous_size = self.file_sizes[file_path]
                    if current_size == previous_size:
                        # Size hasn't changed; stop monitoring this file
                        file_name = os.path.basename(file_path)
                        # Update the popup to red
                        self.app.root.after(0, lambda: self.app.show_alarm_popup(self.alarm, file_name, changing=False))
                        # Remove from tracking
                        del self.file_sizes[file_path]
                        del self.alarm["files"][file_path]
                    else:
                        # Size has changed; update and restart timer
                        self.file_sizes[file_path] = current_size
                        self.alarm["files"][file_path]["size"] = current_size
                        self.start_size_check(file_path)
                except FileNotFoundError:
                    # File might have been deleted before the check
                    file_name = os.path.basename(file_path)
                    self.app.root.after(0, lambda: self.app.show_alarm_popup(self.alarm, file_name, changing=False))
                    del self.file_sizes[file_path]
                    del self.alarm["files"][file_path]


# Main function to run the app
def main():
    root = tk.Tk()
    app = FileMonitorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
