# backend/app.py
import os
import boto3
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
    resize_image
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
        # Check if 'images' exist in the request
        if 'images' not in request.files:
            logger.warning("Images not found in the request.")
            return jsonify({'error': 'Images not found in the request.'}), 400

        # Get the list of uploaded images from the request
        image_files = request.files.getlist('images')
        logger.debug(f"Number of images received: {len(image_files)}")

        if not image_files:
            logger.warning("No images provided in the request.")
            return jsonify({'error': 'No images provided.'}), 400

        # Get the Processing-Mode from the request form data
        processing_mode = request.form.get('Processing-Mode', 'local').lower()
        logger.debug(f"Processing-Mode received: '{processing_mode}'")

        if processing_mode not in ['local', 'aws']:
            logger.warning(f"Invalid Processing-Mode: '{processing_mode}'")
            return jsonify({'error': 'Invalid Processing-Mode. Must be "local" or "aws".'}), 400

        # Get the Export-Type from the request form data
        export_type = request.form.get('Export-Type', 'webp').lower()
        logger.debug(f"Export-Type received: '{export_type}'")

        if export_type not in ['png', 'webp', 'jpg', 'jpeg']:
            logger.warning(f"Invalid Export-Type: '{export_type}'")
            return jsonify({'error': 'Invalid Export-Type. Must be "png", "webp", or "jpg".'}), 400

        # Normalize 'jpg' to 'jpeg' for Pillow compatibility
        if export_type == 'jpg':
            export_type = 'jpeg'
            logger.debug("Normalized Export-Type 'jpg' to 'jpeg'.")

        # For 'aws' processing mode, get and validate the S3 Prefix
        s3_prefix = None
        if processing_mode == 'aws':
            s3_prefix = request.form.get('S3_Prefix', '').strip()
            logger.debug(f"S3_Prefix received: '{s3_prefix}'")

            if not s3_prefix:
                logger.warning("S3_Prefix is missing.")
                return jsonify({'error': 'S3_Prefix is missing.'}), 400

            if not validate_s3_prefix(s3_prefix):
                logger.warning(f"Invalid S3_Prefix format: '{s3_prefix}'")
                return jsonify({'error': 'Invalid S3_Prefix format.'}), 400

            # Verify if the bucket exists
            bucket_name = Config.S3_BUCKET_NAME
            if not bucket_name:
                logger.error('S3_BUCKET_NAME not set in environment variables.')
                return jsonify({'error': 'S3 bucket name not found in environment variables.'}), 500

            if not bucket_exists(bucket_name):
                logger.error(f"S3 bucket '{bucket_name}' does not exist or is inaccessible.")
                return jsonify({'error': f"S3 bucket '{bucket_name}' does not exist or is inaccessible."}), 500

        # Initialize a list to store details for each file
        processed_files = []

        # Initialize in-memory ZIP file for local processing
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            logger.debug("Initialized in-memory ZIP buffer for local processing.")

            # Define the sizes
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
                    # Open the image using PIL
                    image = Image.open(image_file)
                    image.verify()  # Verify that it is, in fact, an image
                    image_file.seek(0)  # Reset file pointer after verify
                    image = Image.open(image_file).convert('RGB')  # Re-open in case verify closed it
                    logger.debug(f"Opened and verified image: {image_file.filename}")
                except (UnidentifiedImageError, Exception) as e:
                    logger.exception(f"Failed to open or verify image: {image_file.filename}")
                    return jsonify({'error': f'Invalid image file: {image_file.filename}.'}), 400

                # Remove file extension from filename
                filename = os.path.splitext(image_file.filename)[0]
                logger.debug(f"Processing filename: '{filename}'")

                # Validate filename
                if not re.match(r'^[\w\-\s]+$', filename):
                    logger.warning(f"Invalid filename: '{filename}'")
                    return jsonify({'error': f'Invalid filename: {filename}.'}), 400

                # Get the original image size
                original_image_size = image.size
                logger.debug(f"Original image size for '{filename}': {original_image_size}")

                # Processed image details
                image_details = []

                if processing_mode == 'local':
                    try:
                        # Save the original image
                        original_extension = os.path.splitext(image_file.filename)[1].lower()
                        if original_extension not in ['.png', '.webp', '.jpg', '.jpeg']:
                            logger.warning(f"Unsupported original image format: '{original_extension}'")
                            return jsonify({'error': f'Unsupported original image format: {original_extension}.'}), 400

                        original_filename = f'{filename}/original{original_extension}'
                        logger.debug(f"Original image will be saved as: '{original_filename}'")

                        # Save the image to a BytesIO object
                        image_data = BytesIO()
                        image.save(image_data, format=image.format)
                        image_data.seek(0)
                        zip_file.writestr(original_filename, image_data.read())
                        image_data.close()
                        logger.info(f"Saved original image to ZIP: '{original_filename}'")
                    except Exception as e:
                        logger.exception(f"Failed to save original image: '{filename}'")
                        return jsonify({'error': f'Failed to save original image: {filename}.'}), 500

                if processing_mode == 'aws':
                    try:
                        # AWS S3 configurations
                        bucket_name = Config.S3_BUCKET_NAME
                        # Already checked above

                        # Construct S3 key using posixpath to ensure forward slashes
                        original_extension = os.path.splitext(image_file.filename)[1].lower()
                        s3_original_key = posixpath.join(s3_prefix, filename, f'original{original_extension}')
                        logger.debug(f"S3 key for original image: '{s3_original_key}'")

                        upload_image_to_s3(image.copy(), s3_original_key, bucket_name, export_type)
                    except Exception as e:
                        logger.exception(f"Failed to upload original image to S3: '{filename}'")
                        return jsonify({'error': f'Failed to upload original image to S3: {filename}.'}), 500

                # Process and save/upload resized images
                for size_name, size in sizes.items():
                    try:
                        resized_image = resize_image(image.copy(), size, resample_filter)
                        logger.debug(f"Resized image '{filename}' to size '{size_name}': {resized_image.size}")
                    except Exception as e:
                        logger.exception(f"Failed to resize image '{filename}' to size '{size_name}'")
                        return jsonify({'error': f'Failed to resize image {filename}.'}), 500

                    # Image metadata
                    image_info = {
                        'filename': f'{filename}/{size_name}.{export_type}',
                        'size_name': size_name,
                        'size': resized_image.size,
                    }

                    if processing_mode == 'local':
                        try:
                            # Convert the image to the selected export format
                            image_data = BytesIO()
                            save_kwargs = {}
                            if export_type == 'webp':
                                save_kwargs['lossless'] = True
                            resized_image.save(image_data, format=export_type.upper(), **save_kwargs)
                            image_data.seek(0)
                            zip_filename = f'{filename}/{size_name}.{export_type}'
                            zip_file.writestr(zip_filename, image_data.read())
                            image_data.close()
                            logger.info(f"Saved resized image to ZIP: '{zip_filename}'")
                        except Exception as e:
                            logger.exception(f"Failed to save resized image: '{zip_filename}'")
                            return jsonify({'error': f'Failed to save resized image: {zip_filename}.'}), 500

                    if processing_mode == 'aws':
                        try:
                            s3_key = posixpath.join(s3_prefix, filename, f'{size_name}.{export_type}')
                            logger.debug(f"S3 key for resized image: '{s3_key}'")
                            upload_image_to_s3(resized_image, s3_key, bucket_name, export_type)
                        except Exception as e:
                            logger.exception(f"Failed to upload resized image to S3: '{s3_key}'")
                            return jsonify({'error': f'Failed to upload resized image to S3: {s3_key}.'}), 500

                    # Append metadata to image_details
                    image_details.append(image_info)

                # Append details of the processed image
                processed_files.append({
                    'filename': image_file.filename,
                    'original_size': original_image_size,
                    'processed_images': image_details
                })

        # Finalize and return the ZIP file if processing locally
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
            except Exception as e:
                logger.exception("Failed to send ZIP file to client.")
                return jsonify({'error': 'Failed to create ZIP file.'}), 500

        # Return JSON response if processing on AWS
        logger.info("Returning JSON response after successful AWS processing.")
        return jsonify({
            'message': 'Images processed and uploaded to AWS S3.',
            'files': processed_files
        }), 200

    except Exception as e:
        logger.exception("An unexpected error occurred during processing.")
        return jsonify({'error': 'Internal server error.'}), 500


if __name__ == '__main__':
    # Ensure necessary environment variables are set
    required_env_vars = ['S3_BUCKET_NAME']
    missing_vars = [var for var in required_env_vars if not getattr(Config, var, None)]
    if missing_vars:
        logger.critical(f"Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)
    else:
        logger.info("All required environment variables are set.")

    # Run the Flask app
    try:
        app.run(port=5000, debug=False)
    except Exception as e:
        logger.exception("Failed to start the Flask application.")
