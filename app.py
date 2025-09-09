import os
import io
import requests
from flask import Flask, render_template, send_file, Response
from dotenv import load_dotenv
import openpyxl

# Load environment variables from a .env file
load_dotenv()

app = Flask(__name__)

# Configuration
API_URL = "https://api-inference.huggingface.co/models/nlpconnect/vit-gpt2-image-captioning"
IMAGE_DIR = "static/images"


def generate_alt_text(image_path: str) -> str:
    """Generates alt text for a single image using the Hugging Face API.

    This function reads an image file, sends it to the specified Hugging Face
    Inference API endpoint, and parses the response to extract the generated
    text.

    Args:
        image_path: The absolute file path to the image.

    Returns:
        The generated alt text as a string. If the API key is missing, the request
        fails, or the response is malformed, an error message string is returned.
    """
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        return "Error: HUGGINGFACE_API_KEY environment variable not set."

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        response = requests.post(API_URL, headers=headers, data=data)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        result = response.json()

        if isinstance(result, list) and result and 'generated_text' in result[0]:
            return result[0]['generated_text']
        else:
            app.logger.error(f"Unexpected API response format: {result}")
            return "Error: Could not parse API response."

    except FileNotFoundError:
        app.logger.error(f"Image file not found at path: {image_path}")
        return "Error: Image file not found."
    except requests.exceptions.RequestException as e:
        app.logger.error(f"API request failed: {e}")
        return f"Error: API request failed: {e}"
    except (KeyError, IndexError):
        app.logger.error(f"Malformed JSON response from API: {result}")
        return "Error: Unexpected API response format."


def get_image_data() -> list[dict[str, str]]:
    """Scans the image directory, generates alt text for each image.

    It locates the image directory, iterates through supported image file types,
    and calls `generate_alt_text` for each one.

    Returns:
        A list of dictionaries, where each dictionary contains the 'filename'
        and its corresponding 'alt_text'. Returns an empty list if the
        directory doesn't exist or contains no images.
    """
    image_folder_path = os.path.join(app.root_path, IMAGE_DIR)
    if not os.path.isdir(image_folder_path):
        app.logger.error(f"Image directory not found: {image_folder_path}")
        return []

    supported_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
    image_files = [f for f in os.listdir(image_folder_path) if f.lower().endswith(supported_extensions)]

    image_data = []
    for filename in image_files:
        full_path = os.path.join(image_folder_path, filename)
        alt_text = generate_alt_text(full_path)
        image_data.append({'filename': filename, 'alt_text': alt_text})

    return image_data


@app.route('/')
def index() -> str:
    """Renders the main gallery page.

    Fetches the image data and renders the `index.html` template,
    displaying the gallery of images and their alt text.

    Returns:
        The rendered HTML page as a string.
    """
    image_data = get_image_data()
    return render_template('index.html', image_data=image_data)


@app.route('/download_excel')
def download_excel() -> Response:
    """Generates and serves an Excel file with image alt tags.

    Fetches the latest image and alt text data, creates an Excel workbook
    in memory, and serves it as a downloadable file.

    Returns:
        A Flask Response object containing the Excel file.
    """
    image_data = get_image_data()

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Alt Tags"

    # Add headers
    sheet.append(["Image Filename", "Alt Tag"])

    # Add data rows
    for item in image_data:
        sheet.append([item['filename'], item['alt_text']])

    # Save the workbook to a memory buffer
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='alt_tags.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
