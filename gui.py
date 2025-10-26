import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
import threading
import compressor
import os

class ImageCompressorApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly")

        self.title("Image Compressor")
        self.geometry("600x550")

        # --- Widgets ---
        self.main_frame = ttk.Frame(self, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Input/Output
        self.input_dir_label = ttk.Label(self.main_frame, text="Input Directory:")
        self.input_dir_entry = ttk.Entry(self.main_frame, width=50)
        self.input_dir_button = ttk.Button(self.main_frame, text="Browse...", command=self.browse_input_dir, style="outline")

        self.output_dir_label = ttk.Label(self.main_frame, text="Output Directory:")
        self.output_dir_entry = ttk.Entry(self.main_frame, width=50)
        self.output_dir_button = ttk.Button(self.main_frame, text="Browse...", command=self.browse_output_dir, style="outline")

        # Settings
        self.quality_label = ttk.Label(self.main_frame, text="Quality:")
        self.quality_value_label = ttk.Label(self.main_frame, text="60")
        self.quality_scale = ttk.Scale(self.main_frame, from_=1, to=100, orient=tk.HORIZONTAL, command=self.update_quality_label)
        self.quality_scale.set(60)
        self.keep_originals_var = tk.BooleanVar()
        self.keep_originals_check = ttk.Checkbutton(self.main_frame, text="Keep original files", variable=self.keep_originals_var, style="round-toggle")

        # Action Button
        self.compress_button = ttk.Button(self.main_frame, text="Compress Images", command=self.start_compression, style="success")

        # Progress Bar
        self.progress_bar = ttk.Progressbar(self.main_frame, orient="horizontal", mode="determinate")

        # Log Area
        self.log_frame = ttk.LabelFrame(self.main_frame, text="Log", padding="10")
        self.log_text = tk.Text(self.log_frame, height=10, state="disabled", relief="flat", borderwidth=0)
        self.log_scroll = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview, style="round")
        self.log_text.config(yscrollcommand=self.log_scroll.set)

        # --- Layout ---
        self.input_dir_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.input_dir_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 10))
        self.input_dir_button.grid(row=1, column=2)

        self.output_dir_label.grid(row=2, column=0, sticky="w", pady=(10, 5))
        self.output_dir_entry.grid(row=3, column=0, columnspan=2, sticky="ew", padx=(0, 10))
        self.output_dir_button.grid(row=3, column=2)

        self.quality_label.grid(row=4, column=0, sticky="w", pady=(20, 5))
        self.quality_value_label.grid(row=4, column=1, sticky="w", pady=(20, 5))
        self.quality_scale.grid(row=5, column=0, columnspan=3, sticky="ew")

        self.keep_originals_check.grid(row=6, column=0, columnspan=3, sticky="w", pady=15)

        self.compress_button.grid(row=7, column=0, columnspan=3, pady=10, ipady=5)

        self.progress_bar.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(5, 15))

        self.log_frame.grid(row=9, column=0, columnspan=3, sticky="nsew", pady=5)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10))

        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(9, weight=1)

    def update_quality_label(self, value):
        self.quality_value_label.config(text=f"{int(float(value))}")

    def browse_input_dir(self):
        directory = filedialog.askdirectory(title="Select Input Directory")
        if directory:
            self.input_dir_entry.delete(0, tk.END)
            self.input_dir_entry.insert(0, directory)

    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, directory)

    def log_message(self, message, level="info"):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"""[{level.upper()}] {message}
""")
        self.log_text.config(state="disabled")
        self.log_text.see(tk.END)
        self.update_idletasks()

    def start_compression(self):
        input_dir = self.input_dir_entry.get()
        output_dir = self.output_dir_entry.get()
        quality = int(self.quality_scale.get())
        keep_originals = self.keep_originals_var.get()

        if not input_dir or not output_dir:
            messagebox.showerror("Error", "Please select both input and output directories.")
            return

        self.compress_button.config(state="disabled")
        self.progress_bar["value"] = 0
        self.log_message("--- Starting compression ---", "info")

        thread = threading.Thread(
            target=self.run_compression,
            args=(input_dir, output_dir, quality, keep_originals)
        )
        thread.start()

    def run_compression(self, input_dir, output_dir, quality, keep_originals):
        try:
            image_files = [os.path.join(root, f) for root, _, files in os.walk(input_dir) for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            total_files = len(image_files)
            self.progress_bar["maximum"] = total_files

            def log_and_update(message, level="info"):
                self.log_message(message, level)
                self.progress_bar["value"] += 1

            compressor.process_directory(
                input_dir,
                output_dir,
                quality,
                keep_originals,
                log_callback=lambda msg: log_and_update(msg, "info"),
                warning_callback=lambda msg: self.log_message(msg, "warning"),
                error_callback=lambda msg: self.log_message(msg, "error")
            )
            self.log_message("--- Compression finished ---", "info")
            messagebox.showinfo("Success", "Image compression completed successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self.log_message(f"--- Compression failed: {e} ---", "error")
        finally:
            self.compress_button.config(state="normal")
            self.progress_bar["value"] = 0

if __name__ == "__main__":
    app = ImageCompressorApp()
    app.mainloop()
