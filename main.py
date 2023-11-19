import os
from flask import Flask, request, jsonify
from PIL import Image
from io import BytesIO
from helpers import resize_image, upload_image_to_s3, is_file_exists, get_file_size, format_file_size
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


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

    # Get the file size of the original image
    image_file.seek(0, os.SEEK_END)
    original_file_size = format_file_size(image_file.tell())

    image_file.seek(0)

    image = Image.open(image_file)

    # Remove file extension from filename
    filename = os.path.splitext(image_file.filename)[0]

    # Get the BucketDir from the request header
    bucket_location = request.headers.get('BucketLocation')

    # Create a folder for the filename in BucketDir
    folder_path = os.path.join(bucket_location, filename)

    # Get the image size of the original image
    original_image_size = image.size

    # Define the sizes for t, s, m, l
    sizes = {
        't': (100, 100),
        's': (300, 300),
        'm': (500, 500),
        'l': (800, 800),
        'xl': (1000, 1000),
        'xxl': (1200, 1200)
    }

    # Get the S3 bucket name from environment variables
    print("S3_BUCKET_NAME:", os.environ.get('S3_BUCKET_NAME'))

    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if not bucket_name:
        return jsonify({'error': 'S3 bucket name not found in environment variables.'}), 500

    # List to store the image details
    image_details = []

    # Prepare the original image details
    original_image_details = {
        'filename': filename,
        'size': original_image_size,
        'file_size': original_file_size,
        'file_type': image_file.content_type
    }

    # Upload the original image to the 'originals' folder
    original_key = os.path.join(
        folder_path, f'original{os.path.splitext(image_file.filename)[1]}')
    upload_image_to_s3(image.copy(), original_key, bucket_name)

    # Process and upload the resized images
    for size_name, size in sizes.items():
        resized_image = resize_image(image.copy(), size)
        key = os.path.join(folder_path, f'{size_name}.webp')

        # Check if the file already exists in the bucket
        if is_file_exists(bucket_name, key):
            return jsonify({'error': f'File {key} already exists in the bucket.'}), 400

        upload_image_to_s3(resized_image, key, bucket_name)

        # Get the resized image size
        resized_image_size = resized_image.size

        # Get the file size from S3
        file_size = get_file_size(bucket_name, key)

        # Construct the image URL
        image_url = f"https://{bucket_name}.s3.amazonaws.com/{key}"

        # Add image details to the list
        image_details.append({
            'filename': filename,
            'size_name': size_name,
            'size': resized_image_size,
            'file_size': file_size,
            'url': image_url
        })

    # Prepare the response
    response = {
        'message': 'Image processed and uploaded successfully.',
        'original': original_image_details,
        'images': image_details
    }

    return jsonify(response), 200


if __name__ == '__main__':
    app.run()
