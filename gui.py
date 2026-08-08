import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.widgets import ToolTip
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
        self.geometry("680x640")
        self.minsize(560, 520)

        # Thread-safe UI updates are marshalled to the main thread via a queue.
        self._ui_queue = queue.Queue()
        self.after(100, self._process_ui_queue)

        self._settings_path = Path.home() / ".config" / "image-compressor" / "settings.json"
        self._settings = self._load_settings()
        self._start_time = None

        # --- Variables ---
        self.input_dir_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.input_dir_var.trace_add("write", self._validate_inputs)
        self.output_dir_var.trace_add("write", self._validate_inputs)

        # --- Widgets ---
        self.main_frame = ttk.Frame(self, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header / Theme Selector
        self.header_frame = ttk.Frame(self.main_frame)
        self.header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(self.header_frame, text="Theme:").pack(side=tk.LEFT)
        self.theme_combo = ttk.Combobox(self.header_frame, values=self.style.theme_names(), state="readonly", width=15)
        self.theme_combo.set(self._settings.get("theme", "darkly"))
        self.theme_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.theme_combo.bind("<<ComboboxSelected>>", self.change_theme)

        # Directories Labelframe
        self.dir_frame = ttk.Labelframe(self.main_frame, text="Directories", padding="15")
        self.dir_frame.pack(fill=tk.X, pady=(0, 15))

        self.input_dir_label = ttk.Label(self.dir_frame, text="Input Directory:")
        self.input_dir_entry = ttk.Entry(self.dir_frame, textvariable=self.input_dir_var)
        self.input_dir_button = ttk.Button(self.dir_frame, text="📁 Browse...", command=self.browse_input_dir, style="outline")
        
        self.output_dir_label = ttk.Label(self.dir_frame, text="Output Directory:")
        self.output_dir_entry = ttk.Entry(self.dir_frame, textvariable=self.output_dir_var)
        self.output_dir_button = ttk.Button(self.dir_frame, text="📁 Browse...", command=self.browse_output_dir, style="outline")

        # Directories Layout
        self.dir_frame.columnconfigure(1, weight=1)
        self.input_dir_label.grid(row=0, column=0, sticky="w", pady=(0, 5), padx=(0, 10))
        self.input_dir_entry.grid(row=0, column=1, sticky="ew", pady=(0, 5), padx=(0, 10))
        self.input_dir_button.grid(row=0, column=2, pady=(0, 5))

        self.output_dir_label.grid(row=1, column=0, sticky="w", pady=(5, 0), padx=(0, 10))
        self.output_dir_entry.grid(row=1, column=1, sticky="ew", pady=(5, 0), padx=(0, 10))
        self.output_dir_button.grid(row=1, column=2, pady=(5, 0))

        # Settings Labelframe
        self.settings_frame = ttk.Labelframe(self.main_frame, text="Compression Settings", padding="15")
        self.settings_frame.pack(fill=tk.X, pady=(0, 15))

        self.quality_frame = ttk.Frame(self.settings_frame)
        self.quality_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.quality_label = ttk.Label(self.quality_frame, text="Quality (1-100):")
        self.quality_label.pack(side=tk.LEFT)
        self.quality_value_label = ttk.Label(self.quality_frame, text=str(compressor.DEFAULT_QUALITY), font=("Helvetica", 10, "bold"))
        self.quality_value_label.pack(side=tk.LEFT, padx=(10, 0))
        
        self.quality_scale = ttk.Scale(self.settings_frame, from_=1, to=100, orient=tk.HORIZONTAL, command=self.update_quality_label)
        self.quality_scale.pack(fill=tk.X, pady=(0, 15))
        ToolTip(self.quality_scale, text="Lower quality reduces size but loses detail. 60-80 is ideal.")

        self.keep_originals_var = tk.BooleanVar()
        self.keep_originals_check = ttk.Checkbutton(self.settings_frame, text="Keep original files", variable=self.keep_originals_var, style="round-toggle")
        self.keep_originals_check.pack(anchor="w")
        ToolTip(self.keep_originals_check, text="If unchecked, source files will be permanently deleted after compression.")

        # Action Button
        self.compress_button = ttk.Button(self.main_frame, text="🗜️ Compress Images", command=self.start_compression, style="success", state="disabled")
        self.compress_button.pack(fill=tk.X, pady=(0, 10), ipady=8)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(self.main_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        # Status Label
        self.status_label = ttk.Label(self.main_frame, text="Ready.", anchor="w")
        self.status_label.pack(fill=tk.X, pady=(0, 10))

        # Log Area
        self.log_frame = ttk.Labelframe(self.main_frame, text="Log")
        self.log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_header = ttk.Frame(self.log_frame)
        self.log_header.pack(fill=tk.X, padx=5, pady=5)
        self.clear_log_btn = ttk.Button(self.log_header, text="🗑️ Clear Log", command=self.clear_log, style="secondary-link")
        self.clear_log_btn.pack(side=tk.RIGHT)

        self.log_text = tk.Text(self.log_frame, height=8, state="disabled", relief="flat", borderwidth=0)
        self.log_text.tag_configure("info", foreground="#c1d0d6")
        self.log_text.tag_configure("warning", foreground="#f0ad4e")
        self.log_text.tag_configure("error", foreground="#e56b6f")
        self.log_scroll = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview, style="round")
        self.log_text.config(yscrollcommand=self.log_scroll.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=(0, 10))
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=(0, 10))

        # Restore saved preferences
        self._restore_settings()

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
        theme = self._settings.get("theme", "darkly")

        self.input_dir_var.set(input_dir)
        self.output_dir_var.set(output_dir)
        if isinstance(quality, int) and 1 <= quality <= 100:
            self.quality_scale.set(quality)
        self.keep_originals_var.set(bool(keep_originals))
        
        if theme in self.style.theme_names():
            self.style.theme_use(theme)

    def _capture_settings(self):
        self._settings["input_dir"] = self.input_dir_var.get()
        self._settings["output_dir"] = self.output_dir_var.get()
        self._settings["quality"] = int(self.quality_scale.get())
        self._settings["keep_originals"] = bool(self.keep_originals_var.get())
        self._settings["theme"] = self.theme_combo.get()

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
    
    def change_theme(self, event=None):
        theme_name = self.theme_combo.get()
        self.style.theme_use(theme_name)

    def update_quality_label(self, value):
        self.quality_value_label.config(text=f"{int(float(value))}")

    def browse_input_dir(self):
        directory = filedialog.askdirectory(title="Select Input Directory")
        if directory:
            self.input_dir_var.set(directory)

    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_var.set(directory)
            
    def _validate_inputs(self, *args):
        if self.input_dir_var.get().strip() and self.output_dir_var.get().strip():
            self.compress_button.config(state="normal")
        else:
            self.compress_button.config(state="disabled")

    def log_message(self, message, level="info"):
        def _update():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, f"[{level.upper()}] {message}\n", (level,))
            self.log_text.config(state="disabled")
            self.log_text.see(tk.END)
            self.update_idletasks()
        self._on_main_thread(_update)
        
    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")

    def set_status(self, message):
        self._on_main_thread(lambda: self.status_label.config(text=message))

    # --- Compression flow ---

    def start_compression(self):
        input_dir = self.input_dir_var.get()
        output_dir = self.output_dir_var.get()
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
                self._validate_inputs() # Reset button state based on inputs
                self.progress_bar["value"] = 0
            self._on_main_thread(_reset)
            self._start_time = None


if __name__ == "__main__":
    app = ImageCompressorApp()
    app.mainloop()
