# Image Compressor GUI

A user-friendly tool to compress multiple images efficiently, featuring a modern interface built with Python, Tkinter, and ttkbootstrap.



<img width="596" height="576" alt="compresroImagenes" src="https://github.com/user-attachments/assets/960e6bb2-92af-4e1b-8abf-0b5ef1ec52f0" /> <!-- Replace with a real screenshot URL -->
 

## Features

-   **Modern & Clean UI**: A visually appealing and easy-to-use interface.
-   **Batch Processing**: Compresses all images within a directory and its subdirectories.
-   **Adjustable Quality**: Control the JPEG compression level (1-100) to balance file size and quality.
-   **Format Conversion**: Converts PNG, JPG, and JPEG files to the highly compatible JPEG format.
-   **Keep or Delete Originals**: Option to automatically delete original files after compression.
-   **Real-time Feedback**: A progress bar and detailed log provide clear feedback during the compression process.
-   **Safe by Default**: Never overwrites existing files in the output directory.
-   **Dual Mode**: Can also be run as a command-line tool for scripting and automation.

## Requirements

-   Python 3.x
-   Pillow
-   ttkbootstrap

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Create and activate a virtual environment** (recommended):
    ```bash
    python -m venv env
    source env/bin/activate  # On Windows, use `env\Scripts\activate`
    ```

3.  **Install the dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: A `requirements.txt` file will be created in the next step)*

## How to Use

### Graphical User Interface (GUI)

This is the recommended way for most users.

1.  **Run the application**:
    ```bash
    bash run_gui.sh
    ```
    Or, with the virtual environment activated:
    ```bash
    python gui.py
    ```

2.  **Using the Interface**:
    -   **Input Directory**: Click "Browse..." and select the folder containing your images.
    -   **Output Directory**: Click "Browse..." and choose where to save the compressed files.
    -   **Quality Slider**: Adjust the slider to set the desired compression quality.
    -   **Keep original files**: Toggle this on if you want to keep your source images after compression.
    -   **Compress Images**: Click the main button to begin. The progress bar will show the status, and the log window will display detailed results.

### Command-Line Interface (CLI)

For automation or integration into scripts.

#### Basic Syntax

```bash
python compressor.py --input-dir <path_to_images> --output-dir <path_to_compressed>
```

#### Arguments

-   `-i, --input-dir` (Required): Path to the source directory.
-   `-o, --output-dir` (Required): Path to the destination directory.
-   `-q, --quality` (Optional): Compression quality (1-100). Defaults to `65`.
-   `--keep-originals` (Optional): Add this flag to prevent original files from being deleted.

#### Example

```bash
python compressor.py --input-dir ./photos --output-dir ./compressed --quality 80 --keep-originals
```

## How It Works

-   **`gui.py`**: Creates the main application window and all widgets using `ttkbootstrap`. It handles user input and runs the compression logic in a separate thread to keep the UI responsive.
-   **`compressor.py`**: Contains the core logic for finding, compressing, and saving images. It uses the `Pillow` library to perform the image manipulation.

## Future Improvements

-   [ ] Add support for more image formats (e.g., WEBP, TIFF).
-   [ ] Allow specifying a file size target.
-   [ ] Implement drag-and-drop for the input directory.
