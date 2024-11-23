# backend/helpers.py
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
import re
from PIL import Image
from io import BytesIO
import posixpath
import logging

logger = logging.getLogger(__name__)

def validate_s3_prefix(s3_prefix):
    """Validate the S3 path prefix format."""
    pattern = r'^[\w\-\/]+$'
    if re.match(pattern, s3_prefix):
        return True
    return False

def validate_bucket_location(bucket_location):
    """Validate the BucketLocation format."""
    pattern = r'^[a-z]{2}-[a-z]+-\d+$'
    if re.match(pattern, bucket_location):
        return True
    return False

def bucket_exists(bucket_name):
    """Check if an S3 bucket exists."""
    s3 = boto3.client('s3')
    try:
        s3.head_bucket(Bucket=bucket_name)
        logger.debug(f"S3 bucket exists: {bucket_name}")
        return True
    except ClientError:
        logger.error(f"S3 bucket does not exist or is inaccessible: {bucket_name}")
        return False
    except NoCredentialsError:
        logger.error("AWS credentials not found.")
        return False

def upload_image_to_s3(image, key, bucket_name, export_type):
    """Upload an image to AWS S3."""
    try:
        s3 = boto3.client('s3')
        buffer = BytesIO()
        save_kwargs = {}
        
        # Determine save parameters based on export_type
        if export_type == 'webp':
            save_kwargs['lossless'] = True
        image.save(buffer, format=export_type.upper(), **save_kwargs)
        buffer.seek(0)
        content_type = f'image/{export_type.lower()}'
        
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=buffer,
            ContentType=content_type
        )
        logger.info(f"Uploaded image to S3: Bucket='{bucket_name}', Key='{key}'")
    except (ClientError, NoCredentialsError, BotoCoreError) as e:
        logger.exception(f"Failed to upload image to S3: {key}")
        raise

def resize_image(image, size, resample_filter):
    """Resize an image to the given size."""
    try:
        image.thumbnail(size, resample=resample_filter)
        logger.debug(f"Image resized to {size}")
        return image
    except Exception as e:
        logger.exception("Failed to resize image.")
        raise

def validate_s3_bucket_name(bucket_name):
    """Validate the S3 bucket name format."""
    pattern = r'^[a-z0-9.-]{3,63}$'
    return re.match(pattern, bucket_name) is not None