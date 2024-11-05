import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from flask import Flask, request, jsonify
from PIL import Image
from io import BytesIO
from helpers import resize_image, upload_image_to_s3, is_file_exists, get_file_size, format_file_size
from flask_cors import CORS
import re
import argparse

UPLOADS_DIR = 'uploads'

app = Flask(__name__, static_url_path='/uploads', static_folder='uploads')
CORS(app)

def bucket_exists(bucket_name):
    """
    Check if an S3 bucket exists.
    """
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
    # Check if 'image' exists in the request
    if 'image' not in request.files:
        return jsonify({'error': 'Image not found in the request.'}), 400

    # Get the uploaded image from the request
    image_file = request.files['image']

    # Get the original file size
    image_file.seek(0, os.SEEK_END)
    image_file_size = image_file.tell()
    image_file.seek(0)

    # Open the image using PIL
    image = Image.open(image_file)

    # Remove file extension from filename
    filename = os.path.splitext(image_file.filename)[0]

    # Get the BucketLocation from the request header
    bucket_location = request.headers.get('BucketLocation', '').strip()
    if not bucket_location:
        return jsonify({'error': 'BucketLocation header is missing.'}), 400

    # Validate bucket_location and filename
    if not re.match(r'^[\w\-]+$', bucket_location):
        return jsonify({'error': 'Invalid BucketLocation.'}), 400
    if not re.match(r'^[\w\-]+$', filename):
        return jsonify({'error': 'Invalid filename.'}), 400

    # Determine the processing mode
    processing_mode = request.headers.get('Processing-Mode', 'both').lower()
    if processing_mode not in ['local', 'aws', 'both']:
        return jsonify({'error': 'Invalid Processing-Mode. Must be "local", "aws", or "both".'}), 400

    # Override processing mode if script is running in local-only mode
    if app.config.get('SCRIPT_MODE') == 'local':
        processing_mode = 'local'

    # Create the folder path for local saving if needed
    if processing_mode in ['local', 'both']:
        folder_path = os.path.join(UPLOADS_DIR, bucket_location, filename)
        os.makedirs(folder_path, exist_ok=True)

    # Get the original image size
    original_image_size = image.size

    # Define the sizes
    sizes = {
        't': (100, 100),
        's': (300, 300),
        'm': (500, 500),
        'l': (800, 800),
        'xl': (1000, 1000),
        'xxl': (1200, 1200)
    }

    # List to store image details
    image_details = []

    # Initialize original image details
    original_image_details = {}

    # Process local saving
    if processing_mode in ['local', 'both']:
        # Save the original image locally
        original_extension = os.path.splitext(image_file.filename)[1]
        original_filename = f'original{original_extension}'
        local_original_key = os.path.join(folder_path, original_filename)

        if os.path.exists(local_original_key):
            return jsonify({'error': f'File {local_original_key} already exists.'}), 400

        image.save(local_original_key)

        # Get the file size
        local_original_file_size = os.path.getsize(local_original_key)
        formatted_local_original_file_size = format_file_size(local_original_file_size)

        # Construct the local image URL
        local_original_image_url = f"/uploads/{bucket_location}/{filename}/{original_filename}"

        # Prepare original image details for local saving
        original_image_details['local'] = {
            'filename': original_filename,
            'size': original_image_size,
            'file_size': formatted_local_original_file_size,
            'file_type': image_file.content_type,
            'url': local_original_image_url
        }

    # Process AWS S3 uploading
    if processing_mode in ['aws', 'both']:
        # AWS S3 configurations
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        if not bucket_name:
            return jsonify({'error': 'S3 bucket name not found in environment variables.'}), 500

        # Upload the original image to S3
        original_extension = os.path.splitext(image_file.filename)[1]
        s3_original_key = os.path.join(
            bucket_location, filename, f'original{original_extension}')
        upload_image_to_s3(image.copy(), s3_original_key, bucket_name)

        # Get the file size from S3
        formatted_s3_original_file_size = get_file_size(bucket_name, s3_original_key)

        # Construct the S3 image URL
        s3_original_image_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_original_key}"

        # Prepare original image details for S3
        original_image_details['s3'] = {
            'filename': f'original{original_extension}',
            'size': original_image_size,
            'file_size': formatted_s3_original_file_size,
            'file_type': image_file.content_type,
            'url': s3_original_image_url
        }

    # Process and save/upload resized images
    for size_name, size in sizes.items():
        resized_image = resize_image(image.copy(), size)

        image_info = {
            'filename': f'{size_name}.webp',
            'size_name': size_name,
            'size': resized_image.size,
        }

        # Local saving
        if processing_mode in ['local', 'both']:
            local_key = os.path.join(folder_path, f'{size_name}.webp')
            if os.path.exists(local_key):
                return jsonify({'error': f'File {local_key} already exists locally.'}), 400

            # Save the resized image locally in WebP format with lossless compression
            image_data = BytesIO()
            resized_image.save(image_data, format='webp', lossless=True)
            image_data.seek(0)

            with open(local_key, 'wb') as f:
                f.write(image_data.read())

            image_data.close()

            local_file_size = os.path.getsize(local_key)
            formatted_local_file_size = format_file_size(local_file_size)
            local_image_url = f"/uploads/{bucket_location}/{filename}/{size_name}.webp"

            image_info['local'] = {
                'file_size': formatted_local_file_size,
                'url': local_image_url
            }

        # AWS S3 uploading
        if processing_mode in ['aws', 'both']:
            bucket_name = os.environ.get('S3_BUCKET_NAME')
            if not bucket_name:
                return jsonify({'error': 'S3 bucket name not found in environment variables.'}), 500

            s3_key = os.path.join(bucket_location, filename, f'{size_name}.webp')
            if is_file_exists(bucket_name, s3_key):
                return jsonify({'error': f'File {s3_key} already exists in S3 bucket.'}), 400

            upload_image_to_s3(resized_image, s3_key, bucket_name)

            formatted_s3_file_size = get_file_size(bucket_name, s3_key)
            s3_image_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

            image_info['s3'] = {
                'file_size': formatted_s3_file_size,
                'url': s3_image_url
            }

        image_details.append(image_info)

    # Prepare the response
    response = {
        'message': 'Image processed successfully.',
        'processing_mode': processing_mode,
        'original': original_image_details,
        'images': image_details
    }

    return jsonify(response), 200

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the PixelPushupAPI.')
    parser.add_argument('--mode', choices=['local', 'aws', 'both'], default='both',
                        help='Set the script mode to local, aws, or both. Default is both.')
    args = parser.parse_args()

    # Store the script mode in the app configuration
    app.config['SCRIPT_MODE'] = args.mode

    # Check for AWS S3 requirements if mode includes 'aws'
    if app.config['SCRIPT_MODE'] in ['aws', 'both']:
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        if bucket_name:
            if bucket_exists(bucket_name):
                print(f" * Bucket '{bucket_name}' exists.")
            else:
                print(f"Bucket '{bucket_name}' does not exist or is not accessible.")
                exit(1)
        else:
            print("S3 bucket name not found in environment variables.")
            exit(1)
    else:
        print("Running in local-only mode. AWS S3 credentials are not required.")

    # Ensure the uploads directory exists if running in local mode
    if app.config['SCRIPT_MODE'] in ['local', 'both']:
        if not os.path.exists(UPLOADS_DIR):
            os.makedirs(UPLOADS_DIR)

    app.run()
