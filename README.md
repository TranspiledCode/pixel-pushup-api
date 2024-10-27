# PixelPushup API

![Image Alt Text](images/pushup.webp)

A Flask-based API for uploading, resizing, and storing images in AWS S3. This tool automatically generates multiple sizes of your images and returns URLs for each version.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the API](#running-the-api)
- [Using the API](#using-the-api)
- [API Reference](#api-reference)
- [Development](#development)
- [Deployment](#deployment)
- [S3 Structure](#s3-structure)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.10+
- AWS Account with admin access (for initial setup)
- Git
- Mac or Linux operating system
- bash or fish shell

## Initial Setup

### 1. AWS IAM Setup (One-time setup)

Contact your AWS administrator to:

1. Create an IAM user for the PixelPushup API
2. Attach these policies:
   - AWSLambdaFullAccess
   - AmazonS3FullAccess
   - IAMFullAccess
3. Generate and provide you with:
   - Access Key ID
   - Secret Access Key

### 2. Install Required Tools

```bash
# bash
# Install Python (Mac)
brew install python

# Install AWS CLI
pip3 install awscli

# Configure AWS CLI with pixelPusher profile
aws configure --profile pixelPusher
# Enter Access Key ID when prompted
# Enter Secret Access Key when prompted
# Region: us-east-1 (or your preferred region)
# Output format: json

# Verify AWS Configuration
aws s3 ls --profile pixelPusher
```

```fish
# fish
# Install Python (Mac)
brew install python

# Install AWS CLI
pip3 install awscli

# Configure AWS CLI with pixelPusher profile
aws configure --profile pixelPusher
# Enter Access Key ID when prompted
# Enter Secret Access Key when prompted
# Region: us-east-1 (or your preferred region)
# Output format: json

# Verify AWS Configuration
aws s3 ls --profile pixelPusher
```

## Installation

### 1. Clone the Repository

```bash
# bash/fish
git clone git@github.com:TranspiledCode/pixel-pushup-api.git
cd pixel-pushup-api
```

### 2. Set Up Virtual Environment

```bash
# bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

```fish
# fish
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate.fish

# Install dependencies
pip install -r requirements.txt
```

### 3. Create Executable (Optional)

```bash
# bash/fish
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile main.py --name pixel-pushup

# The executable will be in the 'dist' directory
```

## Configuration

### 1. Environment Setup

Create a `.env` file in the project root:

```bash
# bash
echo "AWS_PROFILE=pixelPusher" >> .env
```

```fish
# fish
echo "AWS_PROFILE=pixelPusher" >> .env
```

### 2. S3 Bucket Structure

```
your-bucket-name/
├── assets/
│   ├── img/
│   └── icon/
```

## Running the API

### Development Mode

```bash
# bash
# Activate virtual environment (if not already activated)
source venv/bin/activate

# Run the API
python main.py
```

```fish
# fish
# Activate virtual environment (if not already activated)
source venv/bin/activate.fish

# Run the API
python main.py
```

### Using the Executable

```bash
# bash/fish
./dist/pixel-pushup
```

## Using the API

### 1. Test the Connection

```bash
# bash/fish
curl http://127.0.0.1:5000/
# Should return "PixelPushup API is running!"
```

### 2. Upload and Process an Image

```bash
# bash
curl -X POST \
  -H "BucketLocation: assets/img" \
  -F "image=@/path/to/your/image.png" \
  http://127.0.0.1:5000/pushup | jq
```

```fish
# fish
curl -X POST \
  -H "BucketLocation: assets/img" \
  -F "image=@/path/to/your/image.png" \
  http://127.0.0.1:5000/pushup | jq
```

Example Response:

```json
{
  "images": [
    {
      "file_size": "8.76 KB",
      "filename": "Trailer",
      "size": [100, 57],
      "size_name": "t",
      "url": "https://your-bucket.s3.amazonaws.com/assets/img/Trailer/t.webp"
    },
    {
      "file_size": "66.68 KB",
      "filename": "Trailer",
      "size": [300, 171],
      "size_name": "s",
      "url": "https://your-bucket.s3.amazonaws.com/assets/img/Trailer/s.webp"
    }
    // ... more sizes ...
  ],
  "message": "Image processed and uploaded successfully.",
  "original": {
    "file_size": "3.12 MB",
    "file_type": "image/png",
    "filename": "Trailer",
    "size": [1792, 1024]
  }
}
```

## API Reference

### Test Endpoint

- **URL**: `/`
- **Method**: `GET`
- **Response**: Text confirming API is running

### Image Processing Endpoint

- **URL**: `/pushup`
- **Method**: `POST`
- **Headers**:
  - `BucketLocation`: Path in S3 bucket (e.g., "assets/img")
- **Body**:
  - `image`: Image file (multipart/form-data)
- **Response**: JSON object with original and resized image details

Generated Image Sizes:

- Thumbnail (t): 100px width
- Small (s): 300px width
- Medium (m): 500px width
- Large (l): 800px width
- Extra Large (xl): 1000px width
- Double Extra Large (xxl): 1200px width

## Development

### Running Tests

```bash
# bash/fish
python -m pytest tests/
```

### Code Style

```bash
# bash/fish
# Install black
pip install black

# Format code
black .
```

## Deployment

### Deploy to AWS Lambda

```bash
# bash
export AWS_PROFILE=pixelPusher
zappa deploy dev
```

```fish
# fish
set -x AWS_PROFILE pixelPusher
zappa deploy dev
```

## S3 Structure

```
bucket-name/
├── assets/
│   ├── img/
│   │   └── ImageName/
│   │       ├── t.webp
│   │       ├── s.webp
│   │       ├── m.webp
│   │       ├── l.webp
│   │       ├── xl.webp
│   │       └── xxl.webp
│   └── icon/
```

## Troubleshooting

### Common Issues

1. **AWS Credentials Not Working**

```bash
# bash/fish
aws configure list --profile pixelPusher
# Verify credentials are correct
```

2. **Virtual Environment Issues**

```bash
# bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

```fish
# fish
rm -rf venv
python3 -m venv venv
source venv/bin/activate.fish
pip install -r requirements.txt
```

3. **Permission Denied on S3**
   - Verify IAM user has correct permissions
   - Check S3 bucket policy
   - Ensure bucket name in .env is correct

### Getting Help

- Open an issue on GitHub
- Check AWS CloudWatch logs for Lambda deployments
- Review Flask debug logs when running locally

## Requirements

- Python 3.10+
- Flask
- Pillow (PIL)
- boto3
- flask-cors
- python-dotenv
- zappa (for deployment)

## License

MIT License - See LICENSE file for details
