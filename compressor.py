import os
import argparse
import logging
import concurrent.futures
from PIL import Image

def setup_logging():
    """Configures the logging."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_arguments():
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
        type=int,
        default=60,
        help="Compression quality (1-100). Default is 60."
    )
    parser.add_argument(
        "--keep-originals",
        action="store_true",
        help="If set, original files will not be deleted after compression."
    )
    return parser.parse_args()

def create_output_directory(path, log_callback=logging.info):
    """Creates the output directory if it doesn't exist in a thread-safe way."""
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
            log_callback(f"Creating output directory: {path}")
        except FileExistsError:
            # Another thread created it in the meantime.
            pass

def compress_image(source_path, dest_path, quality, log_callback=logging.info, error_callback=logging.error):
    """Compresses a single image."""
    try:
        image = Image.open(source_path).convert("RGB")
        image.save(dest_path, "JPEG", optimize=True, quality=quality, progressive=True)
        log_callback(f"Compressed {source_path} -> {dest_path}")
        return True
    except (IOError, OSError) as e:
        error_callback(f"Error processing {source_path}: {e}")
        return False

def process_directory(input_dir, output_dir, quality, keep_originals, log_callback=logging.info, warning_callback=logging.warning, error_callback=logging.error):
    """Processes all images in a directory concurrently and returns the list of processed files."""
    create_output_directory(output_dir, log_callback)
    
    image_files = [os.path.join(root, f) for root, _, files in os.walk(input_dir) for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    processed_files = []

    def process_one(source_path):
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

    return processed_files

def main():
    """Main function to run the image compression script from the command line."""
    setup_logging()
    args = get_arguments()
    process_directory(args.input_dir, args.output_dir, args.quality, args.keep_originals)

if __name__ == "__main__":
    main()