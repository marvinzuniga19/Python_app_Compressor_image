import os
import argparse
import logging
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
        default=65,
        help="Compression quality (1-100). Default is 65."
    )
    parser.add_argument(
        "--keep-originals",
        action="store_true",
        help="If set, original files will not be deleted after compression."
    )
    return parser.parse_args()

def create_output_directory(path, log_callback=logging.info):
    """Creates the output directory if it doesn't exist."""
    if not os.path.exists(path):
        log_callback(f"Creating output directory: {path}")
        os.makedirs(path)

def compress_image(source_path, dest_path, quality, log_callback=logging.info, error_callback=logging.error):
    """Compresses a single image."""
    try:
        image = Image.open(source_path).convert("RGB")
        image.save(dest_path, "JPEG", optimize=True, quality=quality)
        log_callback(f"Compressed {source_path} -> {dest_path}")
        return True
    except (IOError, OSError) as e:
        error_callback(f"Error processing {source_path}: {e}")
        return False

def process_directory(input_dir, output_dir, quality, keep_originals, log_callback=logging.info, warning_callback=logging.warning, error_callback=logging.error):
    """Processes all images in a directory and returns the list of processed files."""
    create_output_directory(output_dir, log_callback)
    processed_files = []

    image_files = [os.path.join(root, f) for root, _, files in os.walk(input_dir) for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    for source_path in image_files:
        relative_path = os.path.relpath(os.path.dirname(source_path), input_dir)
        output_subdir = os.path.join(output_dir, relative_path)
        create_output_directory(output_subdir, log_callback)

        name, _ = os.path.splitext(os.path.basename(source_path))
        dest_filename = f"compressed_{name}.jpg"
        dest_path = os.path.join(output_subdir, dest_filename)

        if os.path.exists(dest_path):
            warning_callback(f"Skipping {os.path.basename(source_path)}, destination file already exists: {dest_path}")
            continue

        if compress_image(source_path, dest_path, quality, log_callback, error_callback):
            processed_files.append(source_path)
            if not keep_originals:
                os.remove(source_path)
                log_callback(f"Removed original file: {source_path}")
    
    return processed_files

def main():
    """Main function to run the image compression script from the command line."""
    setup_logging()
    args = get_arguments()
    process_directory(args.input_dir, args.output_dir, args.quality, args.keep_originals)

if __name__ == "__main__":
    main()
