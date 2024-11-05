import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from flask import Flask, request, jsonify, send_file
from PIL import Image
from io import BytesIO
from flask_cors import CORS
import re
import zipfile

app = Flask(__name__)
CORS(app)

# Import Resampling based on Pillow version
try:
    from PIL import Resampling  # Pillow >= 10.0.0
    resample_filter = Resampling.LANCZOS
except ImportError:
    resample_filter = Image.LANCZOS  # Pillow < 10.0.0

def resize_image(image, size):
    """Resize an image to the given size."""
    image.thumbnail(size, resample=resample_filter)
    return image

def upload_image_to_s3(image, key, bucket_name):
    """Upload an image to AWS S3."""
    s3 = boto3.client('s3')
    buffer = BytesIO()
    image.save(buffer, format='webp', lossless=True)
    buffer.seek(0)
    s3.put_object(Bucket=bucket_name, Key=key, Body=buffer, ContentType='image/webp')

def bucket_exists(bucket_name):
    """Check if an S3 bucket exists."""
    s3 = boto3.client('s3')
    try:
        s3.head_bucket(Bucket=bucket_name)
        return True
    except (ClientError, NoCredentialsError):
        return False

@app.route("/")
def test_endpoint():
    return "PixelPushupAPI is up and running!"

@app.route("/pushup", methods=['POST'])
def pushup():
    # Check if 'images' exist in the request
    if 'images' not in request.files:
        return jsonify({'error': 'Images not found in the request.'}), 400

    # Get the list of uploaded images from the request
    image_files = request.files.getlist('images')

    # Get the Processing-Mode from the request form data
    processing_mode = request.form.get('Processing-Mode', 'local').lower()
    if processing_mode not in ['local', 'aws']:
        return jsonify({'error': 'Invalid Processing-Mode. Must be "local" or "aws".'}), 400

    # For 'aws' processing mode, get the BucketLocation
    bucket_location = None
    if processing_mode == 'aws':
        bucket_location = request.form.get('BucketLocation', '').strip()
        if not bucket_location:
            return jsonify({'error': 'BucketLocation is missing.'}), 400
        if not re.match(r'^[\w\-]+$', bucket_location):
            return jsonify({'error': 'Invalid BucketLocation.'}), 400

    # Initialize a list to store details for each file
    processed_files = []

    # Initialize in-memory ZIP file for local processing
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

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
            # Open the image using PIL
            image = Image.open(image_file)

            # Remove file extension from filename
            filename = os.path.splitext(image_file.filename)[0]

            # Validate filename
            if not re.match(r'^[\w\-\s]+$', filename):
                return jsonify({'error': f'Invalid filename: {filename}.'}), 400

            # Get the original image size
            original_image_size = image.size

            # Processed image details
            image_details = []

            if processing_mode == 'local':
                # Save the original image
                original_extension = os.path.splitext(image_file.filename)[1]
                original_filename = f'{filename}/original{original_extension}'

                # Save the image to a BytesIO object
                image_data = BytesIO()
                image.save(image_data, format=image.format)
                image_data.seek(0)
                zip_file.writestr(original_filename, image_data.read())
                image_data.close()

            if processing_mode == 'aws':
                # AWS S3 configurations
                bucket_name = os.environ.get('S3_BUCKET_NAME')
                if not bucket_name:
                    return jsonify({'error': 'S3 bucket name not found in environment variables.'}), 500

                # Upload the original image to S3
                original_extension = os.path.splitext(image_file.filename)[1]
                s3_original_key = os.path.join(bucket_location, filename, f'original{original_extension}')
                upload_image_to_s3(image.copy(), s3_original_key, bucket_name)

            # Process and save/upload resized images
            for size_name, size in sizes.items():
                resized_image = resize_image(image.copy(), size)

                # Image metadata
                image_info = {
                    'filename': f'{filename}/{size_name}.webp',
                    'size_name': size_name,
                    'size': resized_image.size,
                }

                if processing_mode == 'local':
                    # Convert the image to WebP format with lossless compression
                    image_data = BytesIO()
                    resized_image.save(image_data, format='webp', lossless=True)
                    image_data.seek(0)
                    zip_filename = f'{filename}/{size_name}.webp'
                    zip_file.writestr(zip_filename, image_data.read())
                    image_data.close()

                if processing_mode == 'aws':
                    s3_key = os.path.join(bucket_location, filename, f'{size_name}.webp')
                    upload_image_to_s3(resized_image, s3_key, bucket_name)

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
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='all_images_processed.zip'
        )

    # Return JSON response if processing on AWS
    return jsonify({
        'message': 'Images processed and uploaded to AWS S3.',
        'files': processed_files
    }), 200

if __name__ == '__main__':
    app.run(port=5000)