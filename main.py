import os
from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageCms, UnidentifiedImageError
from io import BytesIO
import zipfile
import logging
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import threading
from typing import Tuple, Dict, List
import multiprocessing
from dataclasses import dataclass
from pathlib import Path
import tempfile

# Configuration


@dataclass
class Config:
    """Enhanced configuration with image processing settings."""
    VERBOSE: bool = os.environ.get('VERBOSE', 'False').lower() in [
        'true', '1', 'yes']
    LOG_LEVEL: str = 'DEBUG' if VERBOSE else 'INFO'
    MAX_WORKERS: int = multiprocessing.cpu_count()
    JPEG_QUALITY: int = 95  # High quality JPEG
    PNG_COMPRESSION: int = 6  # Balanced PNG compression
    WEBP_QUALITY: int = 90  # High quality WebP
    CHUNK_SIZE: int = 1024 * 1024  # 1MB chunks for file operations
    MAX_IMAGE_DIMENSION: int = 8000  # Maximum dimension allowed
    COLOR_PROFILE: str = 'sRGB'  # Target color profile


# Initialize Flask with enhanced logging
app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5001"],  # Your React app's origin
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Access-Control-Allow-Origin"],
        # Important for file downloads
        "expose_headers": ["Content-Disposition"]
    }
})
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Thread-local storage for resource management
thread_local = threading.local()

# Import Resampling based on Pillow version
try:
    from PIL import Resampling
    RESAMPLE_FILTER = Resampling.LANCZOS
except ImportError:
    RESAMPLE_FILTER = Image.LANCZOS


class ImageProcessor:
    """Handles all image processing operations with optimizations."""

    def __init__(self):
        self.srgb_profile = ImageCms.createProfile('sRGB')
        self.executor = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)

    @lru_cache(maxsize=32)
    def get_optimal_resize_dimensions(self, original_size: Tuple[int, int], target_size: Tuple[int, int]) -> Tuple[int, int]:
        """Calculate optimal resize dimensions while maintaining aspect ratio."""
        width, height = original_size
        target_width, target_height = target_size
        ratio = min(target_width / width, target_height / height)
        return (int(width * ratio), int(height * ratio))

    def convert_color_profile(self, image: Image.Image) -> Image.Image:
        """Convert image to sRGB color profile if needed."""
        if image.info.get('icc_profile'):
            try:
                input_profile = ImageCms.ImageCmsProfile(
                    BytesIO(image.info['icc_profile']))
                return ImageCms.profileToProfile(image, input_profile, self.srgb_profile)
            except:
                logger.warning(
                    "Failed to convert color profile, using original image")
        return image

    def optimize_image(self, image: Image.Image, format: str) -> Image.Image:
        """Apply format-specific optimizations."""
        if format.upper() == 'JPEG':
            # Convert to RGB and optimize for JPEG
            if image.mode in ('RGBA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()
                                 [-1] if image.mode == 'RGBA' else None)
                image = background
        elif format.upper() == 'PNG':
            # Optimize PNG color mode
            if image.mode == 'P':
                image = image.convert('RGBA')
        return image

    def resize_image(self, image: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """Resize image with quality preservation."""
        if image.size[0] > Config.MAX_IMAGE_DIMENSION or image.size[1] > Config.MAX_IMAGE_DIMENSION:
            raise ValueError(
                f"Image dimensions exceed maximum allowed size of {Config.MAX_IMAGE_DIMENSION}px")

        new_size = self.get_optimal_resize_dimensions(image.size, size)
        return image.resize(new_size, RESAMPLE_FILTER, reducing_gap=2.0)

    def save_image(self, image: Image.Image, format: str) -> BytesIO:
        """Save image with format-specific optimizations."""
        buffer = BytesIO()
        save_kwargs = {}

        if format.upper() == 'JPEG':
            save_kwargs = {
                'quality': Config.JPEG_QUALITY,
                'optimize': True,
                'progressive': True
            }
        elif format.upper() == 'PNG':
            save_kwargs = {
                'optimize': True,
                'compression_level': Config.PNG_COMPRESSION
            }
        elif format.upper() == 'WEBP':
            save_kwargs = {
                'quality': Config.WEBP_QUALITY,
                'method': 6  # Highest compression method
            }

        image.save(buffer, format=format.upper(), **save_kwargs)
        buffer.seek(0)
        return buffer


# Initialize processor
image_processor = ImageProcessor()


@app.route("/")
def test_endpoint():
    return "PixelPushupAPI is up and running!"


@app.route("/pushup", methods=['POST'])
def pushup():
    logger.info("Received a /pushup request")
    try:
        if 'images' not in request.files:
            return jsonify({'error': 'Images not found in the request.'}), 400

        image_files = request.files.getlist('images')
        if not image_files:
            return jsonify({'error': 'No images provided.'}), 400

        export_type = request.form.get('Export-Type', 'webp').lower()
        if export_type not in ['png', 'webp', 'jpg', 'jpeg']:
            return jsonify({'error': 'Invalid Export-Type. Must be "png", "webp", or "jpg".'}), 400

        if export_type == 'jpg':
            export_type = 'jpeg'

        # Use temporary directory for large files
        with tempfile.TemporaryDirectory() as temp_dir:
            processed_files = []
            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                sizes = {
                    't': (100, 100),
                    's': (300, 300),
                    'm': (500, 500),
                    'l': (800, 800),
                    'xl': (1000, 1000),
                    'xxl': (1200, 1200)
                }

                for image_file in image_files:
                    try:
                        # Verify image
                        with Image.open(image_file) as img:
                            img.verify()

                        image_file.seek(0)
                        with Image.open(image_file) as image:
                            # Convert to RGB and optimize color profile
                            image = image.convert('RGB')
                            image = image_processor.convert_color_profile(
                                image)

                            filename = Path(image_file.filename).stem
                            original_size = image.size
                            image_details = []

                            # Process sizes in parallel
                            def process_size(size_info):
                                size_name, size = size_info
                                try:
                                    resized = image_processor.resize_image(
                                        image.copy(), size)
                                    optimized = image_processor.optimize_image(
                                        resized, export_type)
                                    buffer = image_processor.save_image(
                                        optimized, export_type)

                                    return {
                                        'size_name': size_name,
                                        'buffer': buffer,
                                        'size': resized.size,
                                        'filename': f'{filename}/{size_name}.{export_type}'
                                    }
                                except Exception as e:
                                    logger.error(
                                        f"Error processing size {size_name}: {str(e)}")
                                    raise

                            # Process sizes in parallel
                            results = list(image_processor.executor.map(
                                process_size, sizes.items()))

                            # Save results to zip
                            for result in results:
                                zip_file.writestr(
                                    result['filename'], result['buffer'].getvalue())
                                image_details.append({
                                    'filename': result['filename'],
                                    'size_name': result['size_name'],
                                    'size': result['size']
                                })

                            processed_files.append({
                                'filename': image_file.filename,
                                'original_size': original_size,
                                'processed_images': image_details
                            })

                    except UnidentifiedImageError:
                        return jsonify({'error': f'Image file {image_file.filename} is not recognized as an image.'}), 400
                    except Exception as e:
                        logger.exception(
                            f"Error processing {image_file.filename}")
                        return jsonify({'error': str(e)}), 500

            zip_buffer.seek(0)
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name='all_images_processed.zip'
            )

    except Exception as e:
        logger.exception("An unexpected error occurred")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True)
