import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
import threading
import queue
import json
import time
import os
from pathlib import Path
import compressor


class ImageCompressorApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly")

        self.title("Image Compressor")
        self.geometry("620x580")
        self.minsize(520, 480)

        # Thread-safe UI updates are marshalled to the main thread via a queue.
        self._ui_queue = queue.Queue()
        self.after(100, self._process_ui_queue)

        self._settings_path = Path.home() / ".config" / "image-compressor" / "settings.json"
        self._settings = self._load_settings()
        self._start_time = None

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
        self.quality_value_label = ttk.Label(self.main_frame, text=str(compressor.DEFAULT_QUALITY))
        self.quality_scale = ttk.Scale(self.main_frame, from_=1, to=100, orient=tk.HORIZONTAL, command=self.update_quality_label)
        self.keep_originals_var = tk.BooleanVar()
        self.keep_originals_check = ttk.Checkbutton(self.main_frame, text="Keep original files", variable=self.keep_originals_var, style="round-toggle")

        # Action Button
        self.compress_button = ttk.Button(self.main_frame, text="Compress Images", command=self.start_compression, style="success")

        # Progress Bar
        self.progress_bar = ttk.Progressbar(self.main_frame, orient="horizontal", mode="determinate")

        # Status Label
        self.status_label = ttk.Label(self.main_frame, text="Ready.", anchor="w")

        # Log Area
        self.log_frame = ttk.Labelframe(self.main_frame, text="Log")
        self.log_text = tk.Text(self.log_frame, height=10, state="disabled", relief="flat", borderwidth=0)
        self.log_text.tag_configure("info", foreground="#c1d0d6")
        self.log_text.tag_configure("warning", foreground="#f0ad4e")
        self.log_text.tag_configure("error", foreground="#e56b6f")
        self.log_scroll = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview, style="round")
        self.log_text.config(yscrollcommand=self.log_scroll.set)

        # Restore saved preferences
        self._restore_settings()

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

        self.progress_bar.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(5, 5))

        self.status_label.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self.log_frame.grid(row=10, column=0, columnspan=3, sticky="nsew", pady=5)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10))

        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(10, weight=1)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- Settings persistence ---

    def _load_settings(self):
        try:
            with open(self._settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_settings(self):
        try:
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._settings_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
        except OSError:
            pass

    def _restore_settings(self):
        input_dir = self._settings.get("input_dir", "")
        output_dir = self._settings.get("output_dir", "")
        quality = self._settings.get("quality", compressor.DEFAULT_QUALITY)
        keep_originals = self._settings.get("keep_originals", False)

        self.input_dir_entry.insert(0, input_dir)
        self.output_dir_entry.insert(0, output_dir)
        if isinstance(quality, int) and 1 <= quality <= 100:
            self.quality_scale.set(quality)
        self.keep_originals_var.set(bool(keep_originals))

    def _capture_settings(self):
        self._settings["input_dir"] = self.input_dir_entry.get()
        self._settings["output_dir"] = self.output_dir_entry.get()
        self._settings["quality"] = int(self.quality_scale.get())
        self._settings["keep_originals"] = bool(self.keep_originals_var.get())

    def on_close(self):
        self._capture_settings()
        self._save_settings()
        self.destroy()

    # --- Thread-safe UI helpers ---

    def _process_ui_queue(self):
        """Drains thread-safe UI updates on the main thread."""
        try:
            while True:
                func = self._ui_queue.get_nowait()
                func()
        except queue.Empty:
            pass
        self.after(100, self._process_ui_queue)

    def _on_main_thread(self, func):
        self._ui_queue.put(func)

    def _format_elapsed(self):
        elapsed = time.time() - self._start_time if self._start_time else 0
        return time.strftime("%M:%S", time.gmtime(elapsed))

    # --- Widget handlers ---

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
        def _update():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, f"[{level.upper()}] {message}\n", (level,))
            self.log_text.config(state="disabled")
            self.log_text.see(tk.END)
            self.update_idletasks()
        self._on_main_thread(_update)

    def set_status(self, message):
        self._on_main_thread(lambda: self.status_label.config(text=message))

    # --- Compression flow ---

    def start_compression(self):
        input_dir = self.input_dir_entry.get()
        output_dir = self.output_dir_entry.get()
        quality = int(self.quality_scale.get())
        keep_originals = self.keep_originals_var.get()

        if not input_dir or not output_dir:
            messagebox.showerror("Error", "Please select both input and output directories.")
            return

        if not os.path.isdir(input_dir):
            messagebox.showerror("Error", "Input directory does not exist.")
            return

        if not os.path.isdir(output_dir) and os.path.exists(output_dir):
            messagebox.showerror("Error", "Output path exists but is not a directory.")
            return

        self._capture_settings()
        self._save_settings()

        self.compress_button.config(state="disabled")
        self.progress_bar["value"] = 0
        self.set_status("Starting...")
        self.log_message("--- Starting compression ---", "info")

        thread = threading.Thread(
            target=self.run_compression,
            args=(input_dir, output_dir, quality, keep_originals)
        )
        thread.start()

    def run_compression(self, input_dir, output_dir, quality, keep_originals):
        totals = [0]
        self._start_time = time.time()

        def on_progress(done, total):
            totals[0] = total

            def _update():
                if done == 0:
                    self.progress_bar["maximum"] = total
                self.progress_bar["value"] = done
                self.status_label.config(text=f"Processing {done}/{total} files · {self._format_elapsed()}")

            self._on_main_thread(_update)

        try:
            compressor.process_directory(
                input_dir,
                output_dir,
                quality,
                keep_originals,
                log_callback=lambda msg: self.log_message(msg, "info"),
                warning_callback=lambda msg: self.log_message(msg, "warning"),
                error_callback=lambda msg: self.log_message(msg, "error"),
                progress_callback=on_progress,
            )

            if totals[0] == 0:
                self.log_message("No images found in the input directory.", "warning")
                self.set_status("No images found.")
                self._on_main_thread(lambda: messagebox.showwarning("No images", "No images were found in the input directory."))
            else:
                self.log_message("--- Compression finished ---", "info")
                self.set_status(f"Completed in {self._format_elapsed()} ({totals[0]} files)")
                self._on_main_thread(lambda: messagebox.showinfo("Success", "Image compression completed successfully!"))
        except Exception as e:
            self.log_message(f"--- Compression failed: {e} ---", "error")
            self.set_status("Failed.")
            self._on_main_thread(lambda: messagebox.showerror("Error", f"An unexpected error occurred: {e}"))
        finally:
            def _reset():
                self.compress_button.config(state="normal")
                self.progress_bar["value"] = 0
            self._on_main_thread(_reset)
            self._start_time = None


if __name__ == "__main__":
    app = ImageCompressorApp()
    app.mainloop()
