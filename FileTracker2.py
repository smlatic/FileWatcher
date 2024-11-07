import os
import time
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

class FileMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Monitor")
        
        self.folder_path = tk.StringVar()
        self.interval = tk.IntVar(value=10)
        self.files_info = {}
        self.monitoring = False
        self.file_extension_filter = tk.StringVar()  # New variable for extension filter
        
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self.root)
        frame.pack(padx=10, pady=10, fill='x', expand=True)
        
        ttk.Label(frame, text="Folder to Monitor:").grid(row=0, column=0, sticky='w')
        ttk.Entry(frame, textvariable=self.folder_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Browse", command=self.browse_folder).grid(row=0, column=2, padx=5)
        self.start_monitoring_button = ttk.Button(frame, text="Start Monitoring", command=self.toggle_monitoring)
        self.start_monitoring_button.grid(row=0, column=3, padx=5)
        
        ttk.Label(frame, text="Check Interval (sec):").grid(row=1, column=0, sticky='w')
        ttk.Entry(frame, textvariable=self.interval, width=10).grid(row=1, column=1, sticky='w')
        
        self.always_on_top = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Always on Top", variable=self.always_on_top, command=self.toggle_always_on_top).grid(row=1, column=2, sticky='w')
        
        # New ticker entry and label for extension filter
        ttk.Label(frame, text="File Extension Filter (e.g., mp4):").grid(row=2, column=0, sticky='w')
        filter_entry = ttk.Entry(frame, textvariable=self.file_extension_filter, width=10)
        filter_entry.grid(row=2, column=1, sticky='w')
        
        # Information for user about the filter
        ttk.Label(frame, text="Filter files by extension. Enter 'mp4' or '.mp4' to filter for video files.").grid(row=3, column=0, columnspan=3, sticky='w')
        
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(padx=10, pady=10, fill='both', expand=True)
        
        self.tree = ttk.Treeview(tree_frame, columns=("name", "size", "status"), show="headings")
        self.tree.heading("name", text="Name")
        self.tree.heading("size", text="Size (bytes)")
        self.tree.heading("status", text="Status")
        self.tree.pack(side="left", fill='both', expand=True)

        self.tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.pack(side="right", fill="y")

        # Define styles for status tags
        self.tree.tag_configure('logging', background='#FFFF99', font=('Helvetica', 10, 'bold'), foreground='black')  # Light yellow
        self.tree.tag_configure('idle', background='#99FF99', font=('Helvetica', 10, 'bold'), foreground='black')  # Light green

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)

    def toggle_monitoring(self):
        if self.monitoring:
            # Stop monitoring
            self.monitoring = False
            self.start_monitoring_button.config(text="Start Monitoring")
        else:
            # Start monitoring
            folder = self.folder_path.get()
            if not os.path.exists(folder):
                print("Invalid folder path")
                return
            
            self.monitoring = True
            self.start_monitoring_button.config(text="Stop Monitoring")
            self.monitor_folder(folder)

    def monitor_folder(self, folder):
        if not self.monitoring:
            return
        
        self.update_files_info(folder)
        self.update_treeview()
        # Schedule the next monitoring event
        self.root.after(self.interval.get() * 1000, lambda: self.monitor_folder(folder))

    def update_files_info(self, folder):
        current_files_info = {}
        for root, _, files in os.walk(folder):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                except OSError:
                    size = 0
                
                if file_path in self.files_info:
                    last_size, last_change_time = self.files_info[file_path]
                    if size != last_size:
                        current_files_info[file_path] = (size, time.time())
                    else:
                        current_files_info[file_path] = (last_size, last_change_time)
                else:
                    current_files_info[file_path] = (size, time.time())
                    print(f"New file detected: {file_path} with size {size} bytes")
        
        self.files_info = current_files_info

    def update_treeview(self):
        # Cache current scrollbar position
        current_scroll_position = self.tree.yview()
        
        # Get current items in TreeView for comparison
        current_items = set(self.tree.get_children())
        new_items = set()

        # Sort files so the latest are at the bottom
        sorted_files = sorted(self.files_info.items(), key=lambda x: x[1][1])

        # Filter by file extension if specified
        extension_filter = self.file_extension_filter.get().lstrip('.')
        
        for file_path, (size, last_change_time) in sorted_files:
            file_name = os.path.basename(file_path)
            
            # Check file extension if a filter is applied
            if extension_filter and not file_name.lower().endswith(f".{extension_filter.lower()}"):
                continue
            
            time_since_change = time.time() - last_change_time
            if time_since_change <= 10:
                status = "Logging..."
                tag = 'logging'
            else:
                status = "Idle"
                tag = 'idle'

            matching_item = None
            for item in current_items:
                if self.tree.item(item, "values")[0] == file_name:
                    matching_item = item
                    break

            if matching_item:
                self.tree.item(matching_item, values=(file_name, size, status), tags=(tag,))
                current_items.remove(matching_item)  # Remove from current_items since it is still relevant
            else:
                new_item = self.tree.insert("", "end", values=(file_name, size, status), tags=(tag,))
                new_items.add(new_item)

        # Remove old items no longer present
        for item in current_items:
            self.tree.delete(item)

        if len(new_items) > 0 and self.user_is_at_bottom(current_scroll_position):
            self.tree.yview_moveto(1.0)

    def user_is_at_bottom(self, current_scroll_position):
        return current_scroll_position[1] == 1.0

    def toggle_always_on_top(self):
        self.root.attributes("-topmost", self.always_on_top.get())

if __name__ == "__main__":
    root = tk.Tk()
    app = FileMonitorApp(root)
    root.mainloop()
