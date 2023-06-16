# PixelPushupAPI Documentation

![Image Alt Text](images/pushup.webp)

The PixelPushupAPI is a Flask-based API that allows users to upload images, resize them, and store the resized versions in an S3 bucket. This documentation provides an overview of the API endpoints, request/response formats, and important considerations.

## Endpoints

### Test Endpoint

- **Endpoint**: `/`
- **HTTP Method**: GET
- **Description**: A test endpoint to check if the API is up and running.
- **Response**: A plain text message indicating the API status.

### Image Pushup

- **Endpoint**: `/pushup`
- **HTTP Method**: POST
- **Description**: Uploads an image and generates resized versions of the image.
- **Request**:

  - Form Data:
    - `image`: The image file to be uploaded (multipart/form-data).

- **Response**:
  - HTTP Status: 200 OK
  - Body: JSON object containing the following information:
    - `message`: A success message indicating that the image was processed and uploaded successfully.
    - `original`: Details of the original image:
      - `filename`: The filename of the original image.
      - `size`: The dimensions of the original image.
      - `file_size`: The file size of the original image.
      - `file_type`: The MIME type of the original image.
    - `images`: An array of resized image details, each containing:
      - `filename`: The filename of the resized image.
      - `size_name`: The size name of the resized image (t, s, m, l).
      - `size`: The dimensions of the resized image.
      - `file_size`: The file size of the resized image.
      - `url`: The URL of the resized image stored in the S3 bucket.

## Response Codes

- **200 OK**: The request was successful, and the response contains the expected data.
- **400 Bad Request**: The request was malformed or missing required parameters.
- **500 Internal Server Error**: An error occurred on the server-side.

## Usage

To use the PixelPushupAPI, you can send an HTTP POST request to the `/pushup` endpoint, including the image file as form data. The API will process the image, generate resized versions, and store them in an S3 bucket. The response will contain information about the original image and the URLs of the resized images.

## Requirements

- Python 3.10
- Flask
- Pillow (PIL)
- boto3
- flask-cors

## Deployment

The PixelPushupAPI can be deployed as a Lambda function using Zappa. Zappa allows you to package and deploy Flask applications as serverless functions on AWS Lambda. The `zappa_settings.json` file contains the configuration settings for the Zappa deployment.

1. Ensure you have the necessary AWS credentials set up.
2. Install the required Python dependencies: `pip install flask flask-cors pillow boto3 zappa`.
3. Set `S3_BUCKET_NAME` in your environment variables.
4. Run the application locally for testing: `python main.py`.
5. Configure your AWS credentials using the AWS CLI: `aws configure`.
6. Deploy the application to AWS Lambda using Zappa: `zappa deploy dev`.

## Conclusion

The PixelPushupAPI provides a simple and efficient way to upload images, generate resized versions, and store them in an S3 bucket. By leveraging Flask, AWS Lambda, and S3, you can easily integrate image uploading and resizing functionality into your applications.

## Example output.

```json
{
  "images": [
    {
      "file_size": "5.63 KB",
      "filename": "angels-envy-rye",
      "size": [37, 100],
      "size_name": "t",
      "url": "https://pixelpushup-test.s3.amazonaws.com/assets/img/bottle/product/angels-envy-rye/t.webp"
    },
    {
      "file_size": "41.34 KB",
      "filename": "angels-envy-rye",
      "size": [112, 300],
      "size_name": "s",
      "url": "https://pixelpushup-test.s3.amazonaws.com/assets/img/bottle/product/angels-envy-rye/s.webp"
    },
    {
      "file_size": "106.30 KB",
      "filename": "angels-envy-rye",
      "size": [186, 500],
      "size_name": "m",
      "url": "https://pixelpushup-test.s3.amazonaws.com/assets/img/bottle/product/angels-envy-rye/m.webp"
    },
    {
      "file_size": "152.83 KB",
      "filename": "angels-envy-rye",
      "size": [222, 597],
      "size_name": "l",
      "url": "https://pixelpushup-test.s3.amazonaws.com/assets/img/bottle/product/angels-envy-rye/l.webp"
    },
    {
      "file_size": "152.83 KB",
      "filename": "angels-envy-rye",
      "size": [222, 597],
      "size_name": "xl",
      "url": "https://pixelpushup-test.s3.amazonaws.com/assets/img/bottle/product/angels-envy-rye/xl.webp"
    },
    {
      "file_size": "152.83 KB",
      "filename": "angels-envy-rye",
      "size": [222, 597],
      "size_name": "xxl",
      "url": "https://pixelpushup-test.s3.amazonaws.com/assets/img/bottle/product/angels-envy-rye/xxl.webp"
    }
  ],
  "message": "Image processed and uploaded successfully.",
  "original": {
    "file_size": "191.52 KB",
    "file_type": "image/png",
    "filename": "angels-envy-rye",
    "size": [222, 597]
  }
}
```

```sh

curl -X POST -H "BucketLocation: bottle/product" -F "image=@/Users/joshua/Desktop/angels-envy-rye.png" http://127.0.0.1:5000/pushup | jq

curl -X POST -H "BucketLocation: bottle/product" -F "image=@/Users/joshua/Desktop/angels-envy-rye.png" https://knadac9lf1.execute-api.us-east-1.amazonaws.com/dev/pushup | jq

```

just pass in the `BucketLocation` in the headers

## S3 Folder Structure

```
- /assets
	- /img
		- /icon
			- /occasions
			- /cocktails
			- /alcohol
			- /alcohol-graphics
		- /refinement
			- /mentions
			- /culture
			- /gender
		- /opportunity
		- /bottle
			- /category
			- /product
		- /app
			- {landing page images}.png
			- {logo}.png
```
