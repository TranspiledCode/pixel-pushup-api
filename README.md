# PixelPushupAPI

![PixelPushup Logo](images/pushup.webp)

A high-performance Flask-based API for batch image processing, resizing, and optimization. PixelPushupAPI automatically generates multiple sizes of your images while maintaining quality and optimizing for web use.

## Features

- Batch image processing with parallel execution
- Multiple output sizes (thumbnail to XXL)
- Support for multiple export formats (WebP, JPEG, PNG)
- Color profile conversion to sRGB
- Automatic image optimization
- CORS support for web applications
- Memory-efficient processing using temporary files
- Maintains aspect ratios during resizing

## Prerequisites

- Python 3.x
- PIL (Pillow)
- Flask
- Flask-CORS

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd pixel-pushup-api
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# Fish Shell: 
source venv/bin/activate.fish
# Bash: 
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install flask pillow flask-cors
```

## Configuration

The API can be configured through environment variables:

- `VERBOSE`: Set to 'True' for detailed logging (default: False)
- `LOG_LEVEL`: Automatically set based on VERBOSE setting
- `MAX_WORKERS`: Defaults to number of CPU cores
- `JPEG_QUALITY`: Set JPEG quality (default: 95)
- `PNG_COMPRESSION`: Set PNG compression level (default: 6)
- `WEBP_QUALITY`: Set WebP quality (default: 90)

## Usage

1. Start the server:
```bash
python app.py
```

The server will start on `http://localhost:5000`

2. Send a POST request to `/pushup` endpoint with:
   - Form field `images`: One or multiple image files
   - Form field `Export-Type`: One of 'webp', 'png', 'jpg' (default: 'webp')

### Output Sizes

The API generates the following sizes for each image:

- Thumbnail (t): 100x100
- Small (s): 300x300
- Medium (m): 500x500
- Large (l): 800x800
- Extra Large (xl): 1000x1000
- Extra Extra Large (xxl): 1200x1200

All sizes maintain the original aspect ratio.

### Example Request using curl

```bash
curl -X POST \
  http://localhost:5000/pushup \
  -F "images=@image1.jpg" \
  -F "images=@image2.png" \
  -F "Export-Type=webp"
```

### Response

The API returns a ZIP file containing all processed images organized in folders by original filename, with each size variant named according to its size designation.

## CORS Configuration

By default, the API accepts requests from `http://localhost:5001`. To modify CORS settings, update the CORS configuration in the code:

```python
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5001"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Access-Control-Allow-Origin"],
        "expose_headers": ["Content-Disposition"]
    }
})
```

## Error Handling

The API includes comprehensive error handling for:
- Invalid image files
- Unsupported export types
- Image processing errors
- Server errors

All errors are returned as JSON responses with appropriate HTTP status codes.

## Performance Considerations

- Uses ThreadPoolExecutor for parallel processing
- Implements LRU cache for optimization calculations
- Handles memory efficiently with temporary files
- Optimizes image saving based on format

## 🤝 Contributing

See `CONTRIBUTING.md` for development guidelines and contribution process.

## 📄 License

MIT License - See LICENSE file for details

## 🚨 Support

For issues or questions, [open a GitHub issue](https://github.com/TranspiledCode/pixel-pushup-api/issues)