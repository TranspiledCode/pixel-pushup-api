# PixelPushup API

A Flask-based API for uploading, resizing, and storing images locally and/or in AWS S3. This tool automatically generates multiple sizes of your images, supports PDF conversion to images, and returns URLs for each version.

## Prerequisites

- macOS
- Python 3.10+
- Fish shell
- AWS Account (if using AWS mode)
- Git

## Installation

### 1. Install Required Tools

```fish
# Install Python
brew install python

# Install AWS CLI (if using AWS S3)
pip3 install awscli

# Install Poppler (required for PDF conversion)
brew install poppler
```

### 2. Configure AWS (If using AWS S3)

```fish
# Configure AWS credentials
aws configure --profile pixelPusher
# Enter your:
# - Access Key ID
# - Secret Access Key
# - Region
# - Output format (json recommended)

# Verify configuration
aws s3 ls --profile pixelPusher
```

### 3. Set Up Project

```fish
# Clone repository
git clone git@github.com:TranspiledCode/pixel-pushup-api.git
cd pixel-pushup-api

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate.fish

# Install dependencies
pip install -r requirements.txt
pip install pdf2image
```

### 4. Configuration

Create a `.env` file in the project root (if using AWS S3):

```fish
echo "AWS_PROFILE=pixelPusher" >> .env
echo "S3_BUCKET_NAME=your-s3-bucket-name" >> .env
```

## Running the API

The API supports three processing modes:

- `local`: Save images to local file system only
- `aws`: Upload images to AWS S3 only
- `both`: Save images both locally and to AWS S3

```fish
# Start the API in your preferred mode
python main.py --mode local  # or 'aws' or 'both'
```

## Using the API

### 1. Test Connection

```fish
curl http://127.0.0.1:5000/
# Should return "PixelPushupAPI is up and running!"
```

### 2. Upload Images

```fish
# Upload an image
curl -X POST \
  -H "BucketLocation: assets/img" \
  -H "Processing-Mode: local" \
  -F "image=@/path/to/your/image.png" \
  http://127.0.0.1:5000/pushup | jq

# Upload a PDF
curl -X POST \
  -H "BucketLocation: assets/img" \
  -H "Processing-Mode: local" \
  -F "image=@/path/to/your/document.pdf" \
  http://127.0.0.1:5000/pushup | jq
```

## Generated Image Sizes

- Thumbnail (t): 100x100px
- Small (s): 300x300px
- Medium (m): 500x500px
- Large (l): 800x800px
- Extra Large (xl): 1000x1000px
- Double Extra Large (xxl): 1200x1200px

## Development

```fish
# Run tests
python -m pytest tests/

# Format code
pip install black
black .
```

## Troubleshooting

### Common Issues

1. **Virtual Environment Problems**

   ```fish
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate.fish
   pip install -r requirements.txt
   ```

2. **AWS Credential Issues**

   ```fish
   aws configure list --profile pixelPusher
   ```

3. **PDF Processing Errors**
   - Ensure `pdf2image` and `poppler` are installed correctly
   - Verify PDF file is valid and accessible

### Getting Help

- Open an issue on GitHub
- Check AWS CloudWatch logs (if using AWS)
- Review Flask debug logs when running locally

## Requirements

- Python 3.10+
- Flask
- Pillow (PIL)
- boto3 (for AWS S3)
- flask-cors
- python-dotenv
- pdf2image
- Poppler

## License

MIT License - See LICENSE file for details
