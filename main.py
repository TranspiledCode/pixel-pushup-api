# main.py
import os
from flask import Flask, request, jsonify, send_file
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from flask_cors import CORS
import re
import zipfile
import posixpath
import logging

from helpers import (
    validate_s3_prefix,
    validate_bucket_location,
    bucket_exists,
    upload_image_to_s3,
    resize_image,
    validate_s3_bucket_name  
)
from config import Config

app = Flask(__name__)
CORS(app)

# Configure logging based on Config
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import Resampling based on Pillow version
try:
    from PIL import Resampling  # Pillow >= 10.0.0
    resample_filter = Resampling.LANCZOS
    logger.debug("Using Resampling.LANCZOS from Pillow >= 10.0.0")
except ImportError:
    resample_filter = Image.LANCZOS  # Pillow < 10.0.0
    logger.debug("Using Image.LANCZOS from Pillow < 10.0.0")

@app.route("/")
def test_endpoint():
    logger.info("Test endpoint accessed.")
    return "PixelPushupAPI is up and running!"

@app.route("/pushup", methods=['POST'])
def pushup():
    logger.info("Received a /pushup request.")
    try:
        if 'images' not in request.files:
            logger.warning("Images not found in the request.")
            return jsonify({'error': 'Images not found in the request.'}), 400

        image_files = request.files.getlist('images')
        logger.debug(f"Number of images received: {len(image_files)}")

        if not image_files:
            logger.warning("No images provided in the request.")
            return jsonify({'error': 'No images provided.'}), 400

        processing_mode = request.form.get('Processing-Mode', 'local').lower()
        logger.debug(f"Processing-Mode received: '{processing_mode}'")

        if processing_mode not in ['local', 'aws']:
            logger.warning(f"Invalid Processing-Mode: '{processing_mode}'")
            return jsonify({'error': 'Invalid Processing-Mode. Must be "local" or "aws".'}), 400

        export_type = request.form.get('Export-Type', 'webp').lower()
        logger.debug(f"Export-Type received: '{export_type}'")

        if export_type not in ['png', 'webp', 'jpg', 'jpeg']:
            logger.warning(f"Invalid Export-Type: '{export_type}'")
            return jsonify({'error': 'Invalid Export-Type. Must be "png", "webp", or "jpg".'}), 400

        if export_type == 'jpg':
            export_type = 'jpeg'
            logger.debug("Normalized Export-Type 'jpg' to 'jpeg'.")

        s3_prefix = None
        bucket_name = None
        if processing_mode == 'aws':
            s3_prefix = request.form.get('S3_Prefix', '').strip()
            logger.debug(f"S3_Prefix received: '{s3_prefix}'")

            if not s3_prefix:
                logger.warning("S3_Prefix is missing.")
                return jsonify({'error': 'S3_Prefix is missing.'}), 400

            if not validate_s3_prefix(s3_prefix):
                logger.warning(f"Invalid S3_Prefix format: '{s3_prefix}'")
                return jsonify({'error': 'Invalid S3_Prefix format.'}), 400

            # Extract S3_Bucket_Name from the request
            bucket_name = request.form.get('S3_Bucket_Name', '').strip()
            logger.debug(f"S3_Bucket_Name received: '{bucket_name}'")

            if not bucket_name:
                logger.error('S3_Bucket_Name is missing in the request.')
                return jsonify({'error': 'S3_Bucket_Name is missing in the request.'}), 400

            if not validate_s3_bucket_name(bucket_name):
                logger.warning(f"Invalid S3_Bucket_Name format: '{bucket_name}'")
                return jsonify({'error': 'Invalid S3_Bucket_Name format.'}), 400

            if not bucket_exists(bucket_name):
                logger.error(f"S3 bucket '{bucket_name}' does not exist or is inaccessible.")
                return jsonify({'error': f"S3 bucket '{bucket_name}' does not exist or is inaccessible."}), 500

        processed_files = []

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            logger.debug("Initialized in-memory ZIP buffer for processing.")

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
                    image = Image.open(image_file)
                    image.verify()
                    image_file.seek(0)
                    image = Image.open(image_file).convert('RGB')
                    logger.debug(f"Opened and verified image: {image_file.filename}")
                except (UnidentifiedImageError, Exception):
                    logger.exception(f"Failed to open or verify image: {image_file.filename}")
                    return jsonify({'error': f'Invalid image file: {image_file.filename}.'}), 400

                filename = os.path.splitext(image_file.filename)[0]
                logger.debug(f"Processing filename: '{filename}'")

                if not re.match(r'^[\w\-\s]+$', filename):
                    logger.warning(f"Invalid filename: '{filename}'")
                    return jsonify({'error': f'Invalid filename: {filename}.'}), 400

                original_image_size = image.size
                logger.debug(f"Original image size for '{filename}': {original_image_size}")

                image_details = []

                if processing_mode == 'local':
                    try:
                        original_extension = os.path.splitext(image_file.filename)[1].lower()
                        valid_extensions = {'.png', '.webp', '.jpg', '.jpeg'}
                        if original_extension not in valid_extensions:
                            logger.warning(f"Unsupported original image format: '{original_extension}'")
                            return jsonify({'error': f'Unsupported original image format: {original_extension}.'}), 400

                        original_filename = f'{filename}/original{original_extension}'
                        logger.debug(f"Original image will be saved as: '{original_filename}'")

                        image_data = BytesIO()
                        image_format = image.format or original_extension.lstrip('.').upper()
                        logger.debug(f"Saving image with format: '{image_format}'")

                        image.save(image_data, format=image_format)
                        image_data.seek(0)
                        zip_file.writestr(original_filename, image_data.read())
                        image_data.close()
                        logger.info(f"Saved original image to ZIP: '{original_filename}'")
                    except Exception:
                        logger.exception(f"Failed to save original image: '{filename}'")
                        return jsonify({'error': f'Failed to save original image: {filename}.'}), 500

                for size_name, size in sizes.items():
                    try:
                        resized_image = resize_image(image.copy(), size, resample_filter)
                        logger.debug(f"Resized image '{filename}' to size '{size_name}': {resized_image.size}")
                    except Exception:
                        logger.exception(f"Failed to resize image '{filename}' to size '{size_name}'")
                        return jsonify({'error': f'Failed to resize image {filename}.'}), 500

                    image_info = {
                        'filename': f'{filename}/{size_name}.{export_type}',
                        'size_name': size_name,
                        'size': resized_image.size,
                    }

                    if processing_mode == 'local':
                        try:
                            image_data = BytesIO()
                            resized_image.save(image_data, format=export_type.upper())
                            image_data.seek(0)
                            zip_filename = f'{filename}/{size_name}.{export_type}'
                            zip_file.writestr(zip_filename, image_data.read())
                            image_data.close()
                            logger.info(f"Saved resized image to ZIP: '{zip_filename}'")
                        except Exception:
                            logger.exception(f"Failed to save resized image: '{zip_filename}'")
                            return jsonify({'error': f'Failed to save resized image: {zip_filename}.'}), 500
                    elif processing_mode == 'aws':
                        try:
                            s3_key = posixpath.join(s3_prefix, filename, f'{size_name}.{export_type}')
                            upload_image_to_s3(resized_image, s3_key, bucket_name, export_type)
                            logger.info(f"Uploaded resized image to S3: Bucket='{bucket_name}', Key='{s3_key}'")
                            image_info['s3_url'] = f's3://{bucket_name}/{s3_key}'
                        except Exception:
                            logger.exception(f"Failed to upload image to S3: '{s3_key}'")
                            return jsonify({'error': f'Failed to upload image to S3: {s3_key}.'}), 500

                    image_details.append(image_info)

                processed_files.append({
                    'filename': image_file.filename,
                    'original_size': original_image_size,
                    'processed_images': image_details
                })

        if processing_mode == 'local':
            try:
                zip_buffer.seek(0)
                logger.info("Returning ZIP file to the client.")
                return send_file(
                    zip_buffer,
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name='all_images_processed.zip'
                )
            except Exception:
                logger.exception("Failed to send ZIP file to client.")
                return jsonify({'error': 'Failed to create ZIP file.'}), 500

        logger.info("Returning JSON response after successful AWS processing.")
        return jsonify({
            'message': 'Images processed and uploaded to AWS S3.',
            'files': processed_files
        }), 200

    except Exception:
        logger.exception("An unexpected error occurred during processing.")
        return jsonify({'error': 'Internal server error.'}), 500

if __name__ == '__main__':
    # No required environment variables now
    try:
        app.run(port=5000, debug=False)
    except Exception:
        logger.exception("Failed to start the Flask application.")