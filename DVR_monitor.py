import os
import time
import threading
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
        
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self.root)
        frame.pack(padx=10, pady=10, fill='x', expand=True)
        
        ttk.Label(frame, text="Folder to Monitor:").grid(row=0, column=0, sticky='w')
        ttk.Entry(frame, textvariable=self.folder_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Browse", command=self.browse_folder).grid(row=0, column=2, padx=5)
        ttk.Button(frame, text="Start Monitoring", command=self.start_monitoring).grid(row=0, column=3, padx=5)
        
        ttk.Label(frame, text="Check Interval (sec):").grid(row=1, column=0, sticky='w')
        ttk.Entry(frame, textvariable=self.interval, width=10).grid(row=1, column=1, sticky='w')
        
        self.always_on_top = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Always on Top", variable=self.always_on_top, command=self.toggle_always_on_top).grid(row=1, column=2, sticky='w')
        
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

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)

    def start_monitoring(self):
        folder = self.folder_path.get()
        if not os.path.exists(folder):
            print("Invalid folder path")
            return
        
        self.monitoring = True
        threading.Thread(target=self.monitor_folder, args=(folder,), daemon=True).start()

    def monitor_folder(self, folder):
        while self.monitoring:
            self.update_files_info(folder)
            self.update_treeview()
            time.sleep(self.interval.get())

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
        
        self.files_info = current_files_info

    def update_treeview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        sorted_files = sorted(self.files_info.items(), key=lambda x: x[1][1], reverse=True)
        
        for file_path, (size, last_change_time) in sorted_files:
            file_name = os.path.basename(file_path)
            if time.time() - last_change_time > 10:
                status = "Finished"
                tags = ('finished',)
            else:
                status = "Checking..."
                tags = ('checking',)
            
            self.tree.insert("", "end", values=(file_name, size, status), tags=tags)
        
        # Scroll to the top to show the latest files
        if len(sorted_files) > 0:
            self.tree.yview_moveto(0)

        # Style tags for coloring only in the status column
        self.tree.tag_configure('checking', font=('Helvetica', 10), foreground='black')
        self.tree.tag_configure('finished', font=('Helvetica', 10), foreground='black')
        for item in self.tree.get_children():
            status = self.tree.item(item, "values")[2]
            if status == "Checking...":
                self.tree.item(item, tags=('checking',))
                self.tree.tag_configure('checking', background='yellow', font=('Helvetica', 10, 'bold'), foreground='black')
            elif status == "Finished":
                self.tree.item(item, tags=('finished',))
                self.tree.tag_configure('finished', background='green', font=('Helvetica', 10, 'bold'), foreground='black')

    def toggle_always_on_top(self):
        self.root.attributes("-topmost", self.always_on_top.get())

if __name__ == "__main__":
    root = tk.Tk()
    app = FileMonitorApp(root)
    root.mainloop()
