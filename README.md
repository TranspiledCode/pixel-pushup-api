# PixelPushup API

A flexible Flask-based API for uploading, resizing, and storing images locally and in AWS S3.

![PixelPushup Logo](images/pushup.webp)


## 🌟 Features

- Multiple image processing modes (local, AWS S3)
- Automatic image resizing to multiple sizes
- Supports various export formats (PNG, WebP, JPEG)
- PDF to image conversion support
- Configurable logging and processing

## 📋 Prerequisites

### System Requirements
- Python 3.10+
- macOS (recommended)
- Git
- AWS Account (optional, for S3 mode)

### Required Tools
- Python
- AWS CLI (optional)
- Poppler (for PDF conversion)

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
# Using Homebrew (macOS)
brew install python awscli poppler

# Using pip
pip install --upgrade pip setuptools wheel
```

### 2. Clone and Set Up Project

```bash
# Clone the repository
git clone https://github.com/TranspiledCode/pixel-pushup-api.git
cd pixel-pushup-api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # For Fish shell: source venv/bin/activate.fish

# Install project dependencies
pip install -r requirements.txt
pip install pdf2image
```

### 3. Configure AWS (Optional)

```bash
# Configure AWS credentials
aws configure --profile pixelPusher

# Verify configuration
aws s3 ls --profile pixelPusher
```

### 4. Environment Configuration

Create a `.env` file:

```bash
AWS_PROFILE=pixelPusher
S3_BUCKET_NAME=your-s3-bucket-name
```

## 🔧 Running the API

```bash
# Start API in different modes
python main.py  # Default mode
python main.py --mode local   # Local processing only
python main.py --mode aws     # AWS S3 processing only
```

## 📤 API Usage Examples

### Test Connection
```bash
curl http://127.0.0.1:5000/
```

### Upload Images
```bash
# Upload an image
curl -X POST \
  -H "Processing-Mode: local" \
  -F "image=@/path/to/image.png" \
  http://127.0.0.1:5000/pushup
```

## 🖼️ Generated Image Sizes

| Size | Dimensions |
|------|------------|
| Thumbnail (t) | 100x100px |
| Small (s) | 300x300px |
| Medium (m) | 500x500px |
| Large (l) | 800x800px |
| Extra Large (xl) | 1000x1000px |
| Double Extra Large (xxl) | 1200x1200px |

## 🛠️ Development

### Running Tests
```bash
# Run test suite
pytest tests/

# Code formatting
pip install black
black .
```

## 🔍 Troubleshooting

### Common Issues
1. **Virtual Environment**
   - Recreate venv if issues persist
   ```bash
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **AWS Credential Verification**
   ```bash
   aws configure list --profile pixelPusher
   ```

### Getting Help
- Open GitHub issues
- Check AWS CloudWatch logs
- Review Flask debug logs

## 📦 Dependencies

- Flask
- Pillow
- boto3
- flask-cors
- python-dotenv
- pdf2image

## 🤝 Contributing

See `CONTRIBUTING.md` for development guidelines and contribution process.

## 📄 License

MIT License - See LICENSE file for details

## 🚨 Support

For issues or questions, [open a GitHub issue](https://github.com/TranspiledCode/pixel-pushup-api/issues)