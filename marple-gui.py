import os
import gzip
import psutil
import shutil
import threading
import subprocess
import tkinter as tk
from PIL import Image
from pathlib import Path
import customtkinter as ctk
from tkinter import Menu, filedialog, ttk

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.tk.call('tk', 'scaling', 2.0)
        
        self.colmode = "light"
        self.colswitch = "#dbdbdb"
        self.update_mode()

        self.marpledir = os.path.join(os.path.join(Path.home(), 'marple'))
        self.marpleguidir = os.path.join(os.path.join(Path.home(), 'marple-gui-dev'))
        
        self.geometry("600x920")
        self.title("MARPLE")
        self.attributes('-alpha', 0.95)
        
        self.font = ctk.CTkFont(family="Helvetica", size=16)
        self.large_font = ctk.CTkFont(family="Helvetica", size=20)
        
        self.barcode_rows = []
        self.transfer_type = 'Pgt'
        self.minknow_dir = ""

        # Image setup
        
        logo_path = os.path.join(self.marpleguidir, "MARPLE_logo.png")
        try:
            logo_image = ctk.CTkImage(Image.open(logo_path), size=(600, 200))
        except Exception as e:
            print(f"Error loading image: {e}")
            logo_image = None
        
        self.logo_label = ctk.CTkLabel(self, image=logo_image, text="", bg_color=self.colswitch)
        self.logo_label.pack(pady=(20, 10))

        # Menu setup (Sandwich Menu)
        self.menu_bar = Menu(self)
        self.config(menu=self.menu_bar)

        self.marple_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Menu", menu=self.marple_menu)
        self.marple_menu.add_command(label="Run MARPLE", command=self.show_home)
        self.marple_menu.add_command(label="Transfer Reads", command=self.show_transfer_reads)
        self.marple_menu.add_command(label="Results", command=self.show_results)
        self.marple_menu.add_command(label="About", command=self.show_about)
        self.marple_menu.add_separator()
        self.marple_menu.add_command(label="Exit", command=self.quit)

        # Light/Dark mode toggle in the menu
        self.theme_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Settings", menu=self.theme_menu)
        self.theme_menu.add_command(label=f'{"Dark mode" if self.colmode == "light" else "Light mode"}', command=self.switch_mode)

        # Run MARPLE button (Home Page)
        self.run_marple_button = ctk.CTkButton(self, text="RUN MARPLE", command=self.run_marple, corner_radius=1, font=self.large_font)
        self.run_marple_button.pack(pady=(30, 30))
        
        self.stop_button = ctk.CTkButton(self, text="STOP MARPLE", command=self.stop_marple, corner_radius=1, font=self.large_font)
        self.stop_button.pack(pady=(10, 20))
        self.snakemake_process = None

        # Placeholder for dynamic content
        self.dynamic_frame = None

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, orientation="horizontal")
        
        # Notification frame
        self.notification_frame = ctk.CTkFrame(self, bg_color=self.colswitch)

    def update_mode(self):
        ctk.set_appearance_mode(self.colmode)
        self.colswitch = "#dbdbdb" if self.colmode == "light" else "#2b2b2b"

    def switch_mode(self):
        self.colmode = "dark" if self.colmode == "light" else "light"
        self.update_mode()
        self.update_ui()
        # Update the theme toggle text in the menu
        self.theme_menu.entryconfig(0, label=f'{"Dark mode" if self.colmode == "light" else "Light mode"}')

    def update_ui(self):
        self.logo_label.configure(bg_color=self.colswitch)
        if self.dynamic_frame:
            self.dynamic_frame.configure(bg_color=self.colswitch)

    def show_home(self):
        self.clear_dynamic_frame()
        self.run_marple_button.pack(pady=(30, 30))
        self.stop_button.pack(pady=(10, 20))

    def show_transfer_reads(self):
        self.clear_dynamic_frame()
        self.dynamic_frame = ctk.CTkFrame(self, bg_color=self.colswitch)
        self.dynamic_frame.pack(fill="both", expand=True, pady=20)

        # Transfer reads options
        self.select_dir_button = ctk.CTkButton(self.dynamic_frame, command=self.select_experiment, text="Select MinKNOW Directory", corner_radius=1, font=self.font)
        self.select_dir_button.pack(pady=(20, 10))

        self.expname_label = ctk.CTkLabel(self.dynamic_frame, text="Experiment Name: ", corner_radius=1, font=self.font)
        self.expname_label.pack(pady=(10, 20))

        self.segmented_button = ctk.CTkSegmentedButton(self.dynamic_frame, values=['Pgt', 'Pst'], command=self.on_segmented_button_click, corner_radius=1, font=self.font)
        self.segmented_button.set('Pgt')
        self.segmented_button.pack(pady=(10, 20))

        self.add_row_button = ctk.CTkButton(self.dynamic_frame, text="Add Barcode Row", command=self.add_barcode_row, corner_radius=1, font=self.font)
        self.add_row_button.pack(pady=(10, 20))

        self.transfer_reads_button = ctk.CTkButton(self.dynamic_frame, command=self.transfer_reads, text="Transfer Reads", corner_radius=1, font=self.large_font)
        self.transfer_reads_button.pack(pady=(10, 20))

        # Create a frame with a scrollbar
        self.canvas = ctk.CTkCanvas(self.dynamic_frame, bg=self.colswitch)
        self.scrollbar = ttk.Scrollbar(self.dynamic_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ctk.CTkFrame(self.canvas, bg_color=self.colswitch, corner_radius=1)

        # Configure the canvas and scrollbar
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Limit the height of the canvas (5 rows height)
        self.canvas.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=20)
        self.scrollbar.pack(side="right", fill="y")

    def add_barcode_row(self):
        row = ctk.CTkFrame(self.scrollable_frame, bg_color=self.colswitch, corner_radius=1)
        row.pack(fill="x", padx=5, pady=2)
        row.grid_columnconfigure(0, weight=1)

        barcode_label = ctk.CTkLabel(row, text="Barcode:", font=self.font)
        barcode_label.pack(side="left", padx=5)

        barcode_entry = ctk.CTkEntry(row, width=60, corner_radius=1, font=self.font)
        barcode_entry.pack(side="left", padx=5)

        sample_label = ctk.CTkLabel(row, text="Sample Name:", font=self.font)
        sample_label.pack(side="left", padx=5)

        sample_entry = ctk.CTkEntry(row, width=200, corner_radius=1, font=self.font)
        sample_entry.pack(side="left", padx=5)

        self.barcode_rows.append((barcode_entry, sample_entry))
        
        # Enable scrolling if more than 5 rows
        if len(self.barcode_rows) > 5:
            self.canvas.configure(height=5 * 40)

    def show_about(self):
        self.clear_dynamic_frame()
        self.dynamic_frame = ctk.CTkFrame(self, bg_color=self.colswitch)
        self.dynamic_frame.pack(fill="both", expand=True, pady=20)

        about_label = ctk.CTkLabel(self.dynamic_frame, text="MARPLE Diagnostics:\npoint-of-care, strain-level disease diagnostics and\nsurveillance tool for complex fungal pathogens\n\nVersion: 2.0-alpha", font=self.large_font)
        about_label.pack(pady=(20, 20))

        devs_label = ctk.CTkLabel(self.dynamic_frame, text="Software and Legacy Code Developers:\nLoizos Savva\nAnthony Bryan\nGuru V. Radhakrishnan")
        devs_label.pack(pady=(20, 20))
        
        copyright_label = ctk.CTkLabel(self.dynamic_frame, text="© 2024 Saunders Lab")
        copyright_label.pack()

    def clear_dynamic_frame(self):
        if self.dynamic_frame:
            self.dynamic_frame.destroy()
        self.run_marple_button.pack_forget()
        self.stop_button.pack_forget()
        
        # Clear output_text widget when switching pages
        if hasattr(self, 'output_text'):
            self.output_text.pack_forget()
            del self.output_text

    def on_segmented_button_click(self, choice):
        self.transfer_type = choice

    def select_experiment(self):
        default_dir = "/var/lib/minknow/data/"
        self.minknow_dir = filedialog.askdirectory(initialdir=default_dir)
        if self.minknow_dir:
            expname = os.path.basename(self.minknow_dir)
            self.expname_label.configure(text=f"Experiment Name: {expname}")

    def transfer_reads(self):
        if not self.minknow_dir:
            self.printin("MinKNOW directory not selected.")
            return

        # Start the progress bar
        self.progress_bar.pack(pady=(10, 20))
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()

        # Run the task in a separate thread to avoid freezing the UI
        thread = threading.Thread(target=self.process_reads)
        thread.start()

    def process_reads(self):
        try:
            total_barcodes = len(self.barcode_rows)
            if total_barcodes == 0:
                self.printin("No barcodes to process.")
                self.progress_bar.stop()
                self.progress_bar.pack_forget()
                return

            for barcode_entry, sample_entry in self.barcode_rows:
                barcode = format(int(barcode_entry.get().strip()), '02d')
                sample = sample_entry.get().strip()

                if not barcode:
                    continue  # Skip empty barcode entries

                for root, dirs, files in os.walk(self.minknow_dir):
                    for dir in dirs:
                        if dir == 'pass':
                            barcode_dir = os.path.join(root, dir, f'barcode{barcode}')
                            try:
                                output_file = os.path.join(self.marpledir, 'reads', self.transfer_type.lower(), f'{sample}.fastq.gz')
                                with gzip.open(output_file, 'wb') as fout:
                                    for file in os.listdir(barcode_dir):
                                        if file.endswith(".gz"):
                                            with gzip.open(os.path.join(barcode_dir, file), 'rb') as f:
                                                reads = f.readlines()
                                                fout.writelines(reads)
                                        elif file.endswith(".fastq"):
                                            with open(os.path.join(barcode_dir, file), 'rb') as f:
                                                reads = f.readlines()
                                                fout.writelines(reads)
                                self.printin(f"Successfully transferred reads for barcode{barcode} to {output_file}")
                            except Exception as e:
                                self.printin(f"An error occurred while processing barcode{barcode}: {e}")
        finally:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            
    def run_marple(self):
        # Start progress bar
        self.progress_bar.pack(pady=(10, 20))
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()

        # Ensure output_text exists
        if not hasattr(self, 'output_text'):
            self.output_text = ctk.CTkTextbox(self, width=600, height=400)
            self.output_text.pack(pady=(20, 20))
            self.output_text.configure(state="disabled")

        # Run the Snakemake process in a separate thread
        thread = threading.Thread(target=self.run_snakemake)
        thread.start()

    def run_snakemake(self):
        if shutil.which("mamba") is not None:
            try:
                env_list = subprocess.check_output(["mamba", "env", "list"], text=True)
                if "marple-env" in env_list:
                    self.stop_marple()
                    self.start_marple()
                else:
                    self.printin("mamba environment marple-env not found.")
            except subprocess.CalledProcessError as e:
                self.printin(f"Error running command: {e}")
        else:
            self.printin("mamba not found.")
        
        self.progress_bar.stop()
        self.progress_bar.pack_forget()

    def start_marple(self):
        try:
            # Start the Snakemake process with unbuffered output
            self.snakemake_process = subprocess.Popen(
                ["snakemake", "--cores", "all", "--rerun-incomplete"],
                cwd=self.marpledir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True
            )
            
            # Use a thread to capture output and display it in real-time
            threading.Thread(target=self.capture_output, args=(self.snakemake_process.stdout,), daemon=True).start()
            threading.Thread(target=self.capture_output, args=(self.snakemake_process.stderr,), daemon=True).start()
            
            self.printin("MARPLE Snakemake workflow started.")
        except Exception as e:
            self.printin(f"Failed to start Snakemake: {e}")

    def capture_output(self, stream):
        if not hasattr(self, 'output_text'):
            # Create output_text if it doesn't exist
            self.output_text = ctk.CTkTextbox(self, width=600, height=400)
            self.output_text.pack(pady=(20, 20))
            self.output_text.configure(state="disabled")
        
        # Display real-time output in the output_text widget
        for line in iter(stream.readline, ''):
            self.output_text.configure(state="normal")
            self.output_text.insert("end", line)
            self.output_text.see("end")
            self.output_text.configure(state="disabled")
        stream.close()

    def stop_marple(self):
        # Stop the Snakemake process if running
        if self.snakemake_process and self.snakemake_process.poll() is None:
            self.snakemake_process.terminate()
            self.printin("MARPLE process terminated.")
            
            # Kill child processes of Snakemake (if any)
            try:
                parent = psutil.Process(self.snakemake_process.pid)
                children = parent.children(recursive=True)  # Get child processes
                for child in children:
                    self.printin(f"Terminating child process: {child.name()} (PID {child.pid})")
                    child.terminate()
                    child.wait()
                self.printin("All child processes terminated.")
            except Exception as e:
                self.printin(f"Failed to terminate child processes: {e}")
        
        # Check for independent processes like FastTree
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = proc.info['cmdline']
                if cmdline and 'fasttree' in cmdline:
                    self.printin(f"Terminating FastTree process (PID {proc.info['pid']})")
                    proc.terminate()
                    proc.wait()
        except Exception as e:
            self.printin(f"Error terminating FastTree: {e}")
        
        self.unlock_snakemake()

    def unlock_snakemake(self):
        try:
            subprocess.run(["mamba", "run", "-n", "marple-env", "snakemake", "--unlock"], cwd=self.marpledir)
        except Exception as e:
            self.printin(f"Failed to unlock Snakemake: {e}")

    def toggle_output_display(self):
        if self.output_text.winfo_viewable():
            self.output_text.pack_forget()
        else:
            self.output_text.pack(pady=(20, 20))
    
    def check_process(self, process, log_file):
        if process.poll() is None:
            self.after(100, self.check_process, process, log_file)
        else:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            status = process.returncode
            if status != 0:
                self.printin(f"Command failed with exit status {status}. Error log:")
                with open(log_file, "r") as log:
                    self.printin(log.read())
            else:
                self.printin("MARPLE run completed successfully.")

    def printin(self, stdout):
        self.notification_frame.pack(side="bottom", fill="both", expand="True")
        for widget in self.notification_frame.winfo_children():
            widget.destroy()
        
        label = ctk.CTkLabel(self.notification_frame, text=stdout, bg_color=self.colswitch)
        label.pack(side="bottom", fill="both", expand="True")
        
        self.after(5000, self.clear_notification)
    
    def clear_notification(self):
        for widget in self.notification_frame.winfo_children():
            widget.destroy()
        self.notification_frame.pack_forget()

    def show_results(self):
        self.clear_dynamic_frame()
        self.dynamic_frame = ctk.CTkFrame(self, bg_color=self.colswitch)
        self.dynamic_frame.pack(fill="both", expand=True, pady=20)

        # Two columns
        self.dynamic_frame.grid_columnconfigure(0, weight=1)
        self.dynamic_frame.grid_columnconfigure(1, weight=1)

        # Pgt Column
        pgt_label = ctk.CTkLabel(self.dynamic_frame, text="Pgt", font=self.large_font, anchor="center")
        pgt_label.grid(row=0, column=0, pady=(10, 10))

        pgt_tree_button = ctk.CTkButton(self.dynamic_frame, text="Tree", command=lambda: self.open_file("pgt", "trees", "pgt_all.pdf"), corner_radius=1, font=self.font)
        pgt_tree_button.grid(row=1, column=0, pady=(10, 10))

        pgt_report_button = ctk.CTkButton(self.dynamic_frame, text="Report", command=lambda: self.open_file("pgt", "report", "pgt.multiqc.html"), corner_radius=1, font=self.font)
        pgt_report_button.grid(row=2, column=0, pady=(10, 10))

        # Pst Column
        pst_label = ctk.CTkLabel(self.dynamic_frame, text="Pst", font=self.large_font, anchor="center")
        pst_label.grid(row=0, column=1, pady=(10, 10))

        pst_tree_button = ctk.CTkButton(self.dynamic_frame, text="Tree", command=lambda: self.open_file("pst", "trees", "pst_all.pdf"), corner_radius=1, font=self.font)
        pst_tree_button.grid(row=1, column=1, pady=(10, 10))

        pst_report_button = ctk.CTkButton(self.dynamic_frame, text="Report", command=lambda: self.open_file("pst", "report", "pst.multiqc.html"), corner_radius=1, font=self.font)
        pst_report_button.grid(row=2, column=1, pady=(10, 10))

    def open_file(self, type, subdir, filename):
        file_path = os.path.join(self.marpledir, "results", type, subdir, filename)
        if filename.endswith(".pdf"):
            print(f'xdg-open {file_path}')
            os.system(f"xdg-open {file_path}")
        elif filename.endswith(".html"):
            os.system(f"xdg-open {file_path}")
        

app = App()
app.mainloop()
