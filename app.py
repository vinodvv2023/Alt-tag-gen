import os
import io
import requests
import base64
import ollama
import pandas as pd
from bs4 import BeautifulSoup
from flask import Flask, render_template, send_file, Response, redirect, url_for, request, flash
from dotenv import load_dotenv
import openpyxl

# Load environment variables from a .env file
load_dotenv()

app = Flask(__name__)
# A secret key is required for flashing messages
app.secret_key = os.urandom(24)

# --- In-Memory Cache ---
image_cache = []
# --- End Cache ---

# --- Configuration ---
IMAGE_DIR = "static/images"

# Hugging Face Configuration
HF_API_URL = os.getenv("HF_API_URL", "https://api-inference.huggingface.co/models/nlpconnect/vit-gpt2-image-captioning")

# Ollama Configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llava")
# --- End Configuration ---


def get_image_bytes(path_or_url: str) -> bytes:
    """Gets the byte content of an image from either a local file path or a URL."""
    if path_or_url.startswith('http://') or path_or_url.startswith('https://'):
        response = requests.get(path_or_url)
        response.raise_for_status()
        return response.content
    else:
        with open(path_or_url, "rb") as f:
            return f.read()


def generate_alt_text_huggingface(image_path: str) -> str:
    """Generates alt text for an image using the Hugging Face API."""
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        return "Error: HUGGINGFACE_API_KEY environment variable not set."
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        image_bytes = get_image_bytes(image_path)
        response = requests.post(HF_API_URL, headers=headers, data=image_bytes)
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list) and result and 'generated_text' in result[0]:
            return result[0]['generated_text']
        else:
            app.logger.error(f"HF Error: Unexpected API response format: {result}")
            return "Error: Could not parse Hugging Face API response."
    except (requests.exceptions.RequestException, FileNotFoundError) as e:
        app.logger.error(f"HF Error: Failed to get image data for '{image_path}'. Reason: {e}")
        return f"Error: Failed to get image data. Reason: {e}"
    except (KeyError, IndexError):
        app.logger.error(f"HF Error: Malformed JSON response from API: {result}")
        return "Error: Unexpected Hugging Face API response format."


def generate_alt_text_ollama(image_path: str) -> str:
    """Generates alt text for an image using a local Ollama model."""
    try:
        image_bytes = get_image_bytes(image_path)
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        response = ollama.chat(
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
    except (requests.exceptions.RequestException, FileNotFoundError) as e:
        app.logger.error(f"Ollama Error: Failed to get image data for '{image_path}'. Reason: {e}")
        return f"Error: Failed to get image data. Reason: {e}"
    except ollama.ResponseError as e:
        app.logger.error(f"Ollama Error: API request failed: {e.error}")
        return f"Error: Ollama API request failed: {e.error}"
    except Exception as e:
        app.logger.error(f"Ollama Error: An unexpected error occurred: {e}")
        return f"Error: An unexpected error occurred with Ollama: {e}"


def generate_alt_text(image_path: str) -> str:
    """Dispatcher function to generate alt text using the configured AI backend."""
    backend = os.getenv("AI_BACKEND", "huggingface").lower()
    if backend == 'ollama':
        return generate_alt_text_ollama(image_path)
    elif backend == 'huggingface':
        return generate_alt_text_huggingface(image_path)
    else:
        error_msg = f"Invalid AI_BACKEND configured: '{backend}'. Please use 'huggingface' or 'ollama'."
        app.logger.error(error_msg)
        return error_msg


def update_cache_from_folder():
    """Scans the image directory, generates alt text, and populates the cache."""
    global image_cache
    image_cache.clear()
    image_folder_path = os.path.join(app.root_path, IMAGE_DIR)
    if not os.path.isdir(image_folder_path):
        app.logger.error(f"Image directory not found: {image_folder_path}")
        return
    supported_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
    image_files = [f for f in os.listdir(image_folder_path) if f.lower().endswith(supported_extensions)]
    for filename in image_files:
        full_path = os.path.join(image_folder_path, filename)
        alt_text = generate_alt_text(full_path)
        image_cache.append({'filename': filename, 'alt_text': alt_text})


@app.route('/')
def index() -> str:
    """Renders the main gallery page using cached data."""
    backend = os.getenv("AI_BACKEND", "huggingface").lower()
    return render_template('index.html', image_data=image_cache, backend=backend)


@app.route('/refresh')
def refresh():
    """Forces a refresh of the image cache from the local folder."""
    update_cache_from_folder()
    flash('Gallery has been refreshed from the local "images" folder.', 'success')
    return redirect(url_for('index'))


@app.route('/clear')
def clear_cache():
    """Clears the in-memory image cache."""
    global image_cache
    image_cache.clear()
    flash('Cache has been cleared.', 'info')
    return redirect(url_for('index'))


@app.route('/upload', methods=['POST'])
def upload_excel_file():
    """Processes an uploaded Excel file to generate alt tags."""
    global image_cache
    if 'excel_file' not in request.files:
        flash('No file part in the request.', 'danger')
        return redirect(url_for('index'))
    file = request.files['excel_file']
    if file.filename == '':
        flash('No file selected for uploading.', 'danger')
        return redirect(url_for('index'))
    if file and file.filename.endswith('.xlsx'):
        try:
            df = pd.read_excel(file)
            if 'Image Path' not in df.columns or 'Image Name' not in df.columns:
                flash("Excel file must have 'Image Name' and 'Image Path' columns.", 'danger')
                return redirect(url_for('index'))
            image_cache.clear()
            for index, row in df.iterrows():
                image_path = row['Image Path']
                image_name = row['Image Name']
                alt_text = generate_alt_text(image_path)
                image_cache.append({'filename': image_name, 'alt_text': alt_text})
            flash(f"Successfully processed {len(df)} rows from the Excel file.", "success")
        except Exception as e:
            app.logger.error(f"Error processing Excel file: {e}")
            flash(f"An error occurred while processing the Excel file: {e}", "danger")
        return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload a .xlsx file.', 'danger')
        return redirect(url_for('index'))


@app.route('/apply_html', methods=['POST'])
def apply_html():
    """Applies cached alt tags to an uploaded HTML file."""
    if not image_cache:
        flash("Cache is empty. Please process some images first.", "danger")
        return redirect(url_for('index'))
    if 'html_file' not in request.files:
        flash('No file part in the request.', 'danger')
        return redirect(url_for('index'))
    file = request.files['html_file']
    if file.filename == '':
        flash('No file selected for uploading.', 'danger')
        return redirect(url_for('index'))
    if file and (file.filename.endswith('.html') or file.filename.endswith('.htm')):
        try:
            html_content = file.read().decode('utf-8')
            soup = BeautifulSoup(html_content, 'html.parser')

            unmatched_files = [item['filename'] for item in image_cache]

            for img in soup.find_all('img'):
                src = img.get('src')
                if not src:
                    continue

                for i, item in enumerate(image_cache):
                    if item['filename'] in src:
                        img['alt'] = item['alt_text']
                        if item['filename'] in unmatched_files:
                            unmatched_files.pop(unmatched_files.index(item['filename']))
                        break # Move to the next img tag once a match is found

            if unmatched_files:
                flash(f"The following images from the cache were not found in the HTML: {', '.join(unmatched_files)}", 'info')
            else:
                flash("Successfully applied all cached alt tags to the HTML file.", "success")

            output_html = soup.prettify()
            buffer = io.BytesIO(output_html.encode('utf-8'))

            return send_file(
                buffer,
                as_attachment=True,
                download_name='updated_tags.html',
                mimetype='text/html'
            )
        except Exception as e:
            app.logger.error(f"Error processing HTML file: {e}")
            flash(f"An error occurred while processing the HTML file: {e}", "danger")
        return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload a .html or .htm file.', 'danger')
        return redirect(url_for('index'))


@app.route('/download_excel')
def download_excel() -> Response:
    """Generates and serves an Excel file with image alt tags from the cache."""
    backend = os.getenv("AI_BACKEND", "huggingface").lower()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Alt Tags"
    sheet.append(["Image Filename", "Alt Tag", "AI Backend"])
    for item in image_cache:
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
