import os
import tkinter as tk
from tkinter import messagebox, filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Monitor App")
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
        self.file_history = []  # Stores file history
        self.monitor_active = False

        # Create the observer to monitor folder changes
        self.observer = Observer()

        # Popup for file alarm
        self.alarm_popup = None

        # Ensure proper shutdown when the window is closed
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_config_window(self):
        # Open a new window to display and configure alarms
        config_window = tk.Toplevel(self.root)
        config_window.title("Configure Alarms")
        config_window.geometry("400x300")

        # Create a container frame to hold the alarms
        alarm_frame = tk.Frame(config_window)
        alarm_frame.pack(fill="both", expand=True)

        # If there are no alarms, display a message and the "Add Alarm" button
        if not self.alarms:
            no_alarm_label = tk.Label(alarm_frame, text="No alarms configured.")
            no_alarm_label.pack(pady=10)

        # Display existing alarms in rows
        for i, alarm in enumerate(self.alarms):
            alarm_label = tk.Label(alarm_frame, text=f"Alarm {i+1}: {alarm['folder']}")
            alarm_label.pack(side="left", padx=5, pady=5)

            # Checkbox (ticker) to toggle the alarm on/off
            alarm_checkbox = tk.Checkbutton(
                alarm_frame, 
                text="On/Off", 
                variable=alarm["active"], 
                command=lambda idx=i: self.toggle_alarm(idx)
            )
            alarm_checkbox.pack(side="right", padx=5, pady=5)

        # Add Alarm button at the bottom of the window to add new alarms
        add_alarm_button = tk.Button(alarm_frame, text="Add Alarm", command=self.add_alarm)
        add_alarm_button.pack(pady=10)

    def add_alarm(self):
        # Open a dialog to select a folder for the new alarm
        folder = filedialog.askdirectory(title="Select Folder to Monitor")
        if folder:
            # Add the selected folder as a new alarm
            new_alarm = {
                "folder": folder, 
                "active": tk.BooleanVar(value=False), 
                "popup": None
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
        # Start monitoring a specific folder
        event_handler = FileChangeHandler(self, alarm)
        self.observer.schedule(event_handler, alarm["folder"], recursive=False)
        self.observer.start()
        self.monitor_active = True

    def stop_monitoring(self, alarm):
        # Close the alarm popup and stop monitoring the folder
        if alarm["popup"]:
            alarm["popup"].destroy()
            alarm["popup"] = None
        if self.monitor_active:
            self.observer.stop()
            self.observer.join()  # Ensure the observer thread is properly stopped
            self.monitor_active = False

    def display_alarm(self, file_name, changing, alarm):
        # Display the alarm window for the current file
        if not alarm["popup"]:
            alarm["popup"] = tk.Toplevel(self.root)
            alarm["popup"].title("File Alarm")
            alarm["popup"].geometry("500x300")
            alarm["alarm_label"] = tk.Label(alarm["popup"], text=file_name, fg="white")
            alarm["alarm_label"].pack(expand=True)

            alarm["popup"].bind('<Configure>', lambda event, alrm=alarm: self.resize_alarm_text(event, alrm))

        # Update the label and background color
        alarm["alarm_label"].config(text=file_name)
        if changing:
            alarm["popup"].configure(bg="green")
        else:
            alarm["popup"].configure(bg="red")

    def resize_alarm_text(self, event, alarm):
        # Dynamically change the font size of the alarm based on window size
        new_size = int(event.width / 15)
        alarm["alarm_label"].config(font=("Arial", new_size))

    def show_file_history(self):
        # Display the file history in a popup window
        history_window = tk.Toplevel(self.root)
        history_window.title("File History")
        history_window.geometry("300x200")

        if not self.file_history:
            no_history_label = tk.Label(history_window, text="No files in history.")
            no_history_label.pack(pady=10)
        else:
            for i, file in enumerate(self.file_history):
                file_label = tk.Label(history_window, text=f"{i+1}: {file}")
                file_label.pack(pady=5)

    def save_setup(self):
        # Placeholder for saving the current setup
        messagebox.showinfo("Save Setup", "This will save the setup in future steps.")

    def on_closing(self):
        """Handle the app shutdown cleanly when the window is closed."""
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

    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            file_name = os.path.basename(file_path)
            self.file_sizes[file_path] = os.path.getsize(file_path)
            self.app.file_history.append(file_name)  # Add to file history
            self.app.display_alarm(file_name, changing=True, alarm=self.alarm)

    def on_modified(self, event):
        if not event.is_directory:
            file_path = event.src_path
            current_size = os.path.getsize(file_path)

            if file_path in self.file_sizes:
                if self.file_sizes[file_path] != current_size:
                    self.file_sizes[file_path] = current_size
                    self.app.display_alarm(os.path.basename(file_path), changing=True, alarm=self.alarm)
                else:
                    # If file size hasn't changed, mark as stopped (red background)
                    self.app.display_alarm(os.path.basename(file_path), changing=False, alarm=self.alarm)


# Main function to run the app
def main():
    root = tk.Tk()
    app = FileMonitorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
