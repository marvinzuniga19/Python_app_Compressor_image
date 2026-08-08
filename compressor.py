import os
import argparse
import logging
import concurrent.futures
from typing import Callable, List, Optional
from PIL import Image

DEFAULT_QUALITY = 60

def format_size(num_bytes: int) -> str:
    """Formats a byte count as a human-readable string."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    for unit in ("KB", "MB", "GB"):
        num_bytes /= 1024.0
        if num_bytes < 1024 or unit == "GB":
            return f"{num_bytes:.1f} {unit}"
    return f"{num_bytes:.1f} GB"

def setup_logging() -> None:
    """Configures the logging."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def quality_type(value: str) -> int:
    """Validates that a --quality argument is an integer between 1 and 100."""
    try:
        quality = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"quality must be an integer, got '{value}'")
    if not 1 <= quality <= 100:
        raise argparse.ArgumentTypeError(f"quality must be between 1 and 100, got {quality}")
    return quality

def get_arguments() -> argparse.Namespace:
    """Parses and returns command-line arguments."""
    parser = argparse.ArgumentParser(description="Compress images in a directory.")
    parser.add_argument(
        "-i", "--input-dir",
        required=True,
        help="The directory containing images to compress."
    )
    parser.add_argument(
        "-o", "--output-dir",
        required=True,
        help="The directory where compressed images will be saved."
    )
    parser.add_argument(
        "-q", "--quality",
        type=quality_type,
        default=DEFAULT_QUALITY,
        help=f"Compression quality (1-100). Default is {DEFAULT_QUALITY}."
    )
    parser.add_argument(
        "--keep-originals",
        action="store_true",
        help="If set, original files will not be deleted after compression."
    )
    return parser.parse_args()

def create_output_directory(path: str, log_callback: Callable[[str], None] = logging.info, error_callback: Callable[[str], None] = logging.error) -> None:
    """Creates the output directory if it doesn't exist in a thread-safe way."""
    if not os.path.isdir(path):
        try:
            os.makedirs(path, exist_ok=True)
            log_callback(f"Creating output directory: {path}")
        except OSError as e:
            error_callback(f"Failed to create directory {path}: {e}")

def compress_image(source_path: str, dest_path: str, quality: int, log_callback: Callable[[str], None] = logging.info, error_callback: Callable[[str], None] = logging.error) -> bool:
    """Compresses a single image."""
    try:
        original_size = os.path.getsize(source_path)
        with Image.open(source_path) as image:
            image.convert("RGB").save(dest_path, "JPEG", optimize=True, quality=quality, progressive=True)
        compressed_size = os.path.getsize(dest_path)
        saved_pct = (1 - compressed_size / original_size) * 100 if original_size else 0
        if saved_pct >= 0:
            size_summary = f"({format_size(original_size)} -> {format_size(compressed_size)}, {saved_pct:.0f}% smaller)"
        else:
            size_summary = f"({format_size(original_size)} -> {format_size(compressed_size)}, {-saved_pct:.0f}% larger)"
        log_callback(f"Compressed {source_path} -> {dest_path} {size_summary}")
        return True
    except (IOError, OSError) as e:
        error_callback(f"Error processing {source_path}: {e}")
        return False

def process_directory(
    input_dir: str,
    output_dir: str,
    quality: int,
    keep_originals: bool,
    log_callback: Callable[[str], None] = logging.info,
    warning_callback: Callable[[str], None] = logging.warning,
    error_callback: Callable[[str], None] = logging.error,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[str]:
    """Processes all images in a directory concurrently and returns the list of processed files.

    `progress_callback(done, total)` is invoked first with the total number of
    images and then after every file has been processed (succeeded, skipped, or failed).
    """
    create_output_directory(output_dir, log_callback)

    image_files = [os.path.join(root, f) for root, _, files in os.walk(input_dir) for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    total_files = len(image_files)
    if progress_callback is not None:
        progress_callback(0, total_files)

    processed_files = []
    done_count = [0]

    def process_one(source_path: str) -> Optional[str]:
        """Helper function to process a single image file."""
        relative_path = os.path.relpath(os.path.dirname(source_path), input_dir)
        output_subdir = os.path.join(output_dir, relative_path)
        create_output_directory(output_subdir, log_callback)

        name, _ = os.path.splitext(os.path.basename(source_path))
        dest_filename = f"compressed_{name}.jpg"
        dest_path = os.path.join(output_subdir, dest_filename)

        if os.path.exists(dest_path):
            warning_callback(f"Skipping {os.path.basename(source_path)}, destination file already exists: {dest_path}")
            return None

        if compress_image(source_path, dest_path, quality, log_callback, error_callback):
            if not keep_originals:
                try:
                    os.remove(source_path)
                    log_callback(f"Removed original file: {source_path}")
                except OSError as e:
                    error_callback(f"Error removing original file {source_path}: {e}")
            return source_path
        return None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_path = {executor.submit(process_one, path): path for path in image_files}
        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            try:
                result = future.result()
                if result:
                    processed_files.append(result)
            except Exception as exc:
                error_callback(f'{path} generated an exception: {exc}')
            finally:
                done_count[0] += 1
                if progress_callback is not None:
                    progress_callback(done_count[0], total_files)

    return processed_files

def main() -> None:
    """Main function to run the image compression script from the command line."""
    setup_logging()
    args = get_arguments()
    process_directory(args.input_dir, args.output_dir, args.quality, args.keep_originals)

if __name__ == "__main__":
    main()
