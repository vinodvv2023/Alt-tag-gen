import os
import io
import requests
import base64
import ollama
from flask import Flask, render_template, send_file, Response
from dotenv import load_dotenv
import openpyxl

# Load environment variables from a .env file
load_dotenv()

app = Flask(__name__)

# --- Configuration ---
IMAGE_DIR = "static/images"

# Hugging Face Configuration
HF_API_URL = os.getenv("HF_API_URL", "https://api-inference.huggingface.co/models/nlpconnect/vit-gpt2-image-captioning")

# Ollama Configuration
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llava")
# --- End Configuration ---


def generate_alt_text_huggingface(image_path: str) -> str:
    """Generates alt text for an image using the Hugging Face API."""
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        return "Error: HUGGINGFACE_API_KEY environment variable not set."

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        response = requests.post(HF_API_URL, headers=headers, data=data)
        response.raise_for_status()
        result = response.json()

        if isinstance(result, list) and result and 'generated_text' in result[0]:
            return result[0]['generated_text']
        else:
            app.logger.error(f"HF Error: Unexpected API response format: {result}")
            return "Error: Could not parse Hugging Face API response."
    except requests.exceptions.RequestException as e:
        app.logger.error(f"HF Error: API request failed: {e}")
        return f"Error: Hugging Face API request failed: {e}"
    except (KeyError, IndexError):
        app.logger.error(f"HF Error: Malformed JSON response from API: {result}")
        return "Error: Unexpected Hugging Face API response format."


def generate_alt_text_ollama(image_path: str) -> str:
    """Generates alt text for an image using a local Ollama model."""
    try:
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')

        client = ollama.Client(host=OLLAMA_API_URL)
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    'role': 'user',
                    'content': 'Describe this image in one sentence for use as alt text.',
                    'images': [image_base64]
                }
            ]
        )
        return response['message']['content']
    except ollama.ResponseError as e:
        app.logger.error(f"Ollama Error: API request failed: {e.error}")
        return f"Error: Ollama API request failed: {e.error}"
    except Exception as e:
        app.logger.error(f"Ollama Error: An unexpected error occurred: {e}")
        return f"Error: An unexpected error occurred with Ollama: {e}"


def generate_alt_text(image_path: str) -> str:
    """
    Dispatcher function to generate alt text using the configured AI backend.
    """
    backend = os.getenv("AI_BACKEND", "huggingface").lower()
    if backend == 'ollama':
        return generate_alt_text_ollama(image_path)
    elif backend == 'huggingface':
        return generate_alt_text_huggingface(image_path)
    else:
        error_msg = f"Invalid AI_BACKEND configured: '{backend}'. Please use 'huggingface' or 'ollama'."
        app.logger.error(error_msg)
        return error_msg


def get_image_data() -> list[dict[str, str]]:
    """Scans the image directory, generates alt text for each image."""
    image_folder_path = os.path.join(app.root_path, IMAGE_DIR)
    if not os.path.isdir(image_folder_path):
        app.logger.error(f"Image directory not found: {image_folder_path}")
        return []

    supported_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
    image_files = [f for f in os.listdir(image_folder_path) if f.lower().endswith(supported_extensions)]

    image_data = []
    for filename in image_files:
        full_path = os.path.join(image_folder_path, filename)
        try:
            alt_text = generate_alt_text(full_path)
            image_data.append({'filename': filename, 'alt_text': alt_text})
        except FileNotFoundError:
            app.logger.error(f"Image file not found at path: {full_path}")
            image_data.append({'filename': filename, 'alt_text': 'Error: File not found.'})

    return image_data


@app.route('/')
def index() -> str:
    """Renders the main gallery page."""
    image_data = get_image_data()
    backend = os.getenv("AI_BACKEND", "huggingface").lower()
    return render_template('index.html', image_data=image_data, backend=backend)


@app.route('/download_excel')
def download_excel() -> Response:
    """Generates and serves an Excel file with image alt tags."""
    image_data = get_image_data()
    backend = os.getenv("AI_BACKEND", "huggingface").lower()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Alt Tags"
    sheet.append(["Image Filename", "Alt Tag", "AI Backend"])
    for item in image_data:
        sheet.append([item['filename'], item['alt_text'], backend])
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
