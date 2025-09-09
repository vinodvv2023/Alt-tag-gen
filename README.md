# Alt Tag Generator

This web application automatically generates descriptive alt tags for images using a powerful vision-language model. It supports both the Hugging Face API for cloud-based inference and local models via Ollama.

The app provides a simple gallery view of all processed images along with their generated descriptions and an option to export the results to an Excel file. This tool is designed to help improve web accessibility by making it easy to create meaningful alt text for visual content.

## Features

-   **Automatic Alt Tag Generation**: Scans a local directory for images and generates descriptive captions.
-   **Flexible AI Backends**:
    -   **Hugging Face**: Use the `nlpconnect/vit-gpt2-image-captioning` model via the Inference API.
    -   **Ollama**: Connect to a locally running Ollama instance to use models like `llava` for full privacy and offline capability.
-   **Web Gallery**: Displays images and their alt tags in a clean, user-friendly web interface.
-   **Excel Export**: Allows you to download a list of all image filenames, their corresponding alt tags, and the backend used, in a single `.xlsx` file.
-   **Easy to Configure**: Switch between backends by changing a single environment variable.

---

## ⚙️ Setup and Usage

Follow these steps to run the application on your local machine.

### 1. Prerequisites

-   Python 3.8+
-   **For Hugging Face backend:** A Hugging Face account with an API Access Token.
-   **For Ollama backend:** A local installation of [Ollama](https://ollama.com/) with a vision model pulled (e.g., `ollama pull llava`).

### 2. Installation

First, clone the repository to your local machine:
```bash
git clone <repository_url>
cd <repository_directory>
```

Next, install the required Python packages:
```bash
pip install -r requirements.txt
```

### 3. Configuration

The application is configured using a `.env` file.

1.  **Create a `.env` file** by copying the example:
    ```bash
    cp .env.example .env
    ```
2.  **Edit the `.env` file** to choose and configure your backend.

    **To use Hugging Face (default):**
    -   Set `AI_BACKEND="huggingface"`.
    -   Add your Hugging Face API key to `HUGGINGFACE_API_KEY`.

    **To use Ollama:**
    -   Make sure Ollama is running on your machine.
    -   Set `AI_BACKEND="ollama"`.
    -   Verify the `OLLAMA_API_URL` and `OLLAMA_MODEL` are correct for your setup.

    *Example `.env` for Ollama:*
    ```
    AI_BACKEND="ollama"
    HUGGINGFACE_API_KEY="" # Not needed for Ollama
    OLLAMA_API_URL="http://localhost:11434"
    OLLAMA_MODEL="llava"
    ```

### 4. Add Images

Place any images you want to process into the `static/images` directory. The application will automatically detect and process them on page load.

### 5. Running the Application

Once the setup is complete, you can start the Flask web server:
```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000`. Open this URL in your web browser to see the gallery.

---

## 🧪 Running Tests

This project includes a suite of unit tests to ensure the core logic is working correctly for both backends. To run the tests, execute the following command from the root directory of the project:

```bash
python -m unittest discover tests
```
