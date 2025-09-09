# Alt Tag Generator

This web application automatically generates descriptive alt tags for images using a powerful vision-language model from Hugging Face. It provides a simple gallery view of all processed images along with their generated descriptions and an option to export the results to an Excel file.

This tool is designed to help improve web accessibility by making it easy to create meaningful alt text for visual content.

## Features

-   **Automatic Alt Tag Generation**: Scans a local directory for images and generates descriptive captions.
-   **AI-Powered**: Uses the `nlpconnect/vit-gpt2-image-captioning` model via the Hugging Face Inference API.
-   **Web Gallery**: Displays images and their alt tags in a clean, user-friendly web interface.
-   **Excel Export**: Allows you to download a list of all image filenames and their corresponding alt tags in a single `.xlsx` file.
-   **Easy to Set Up**: Requires minimal configuration to get started.

## How It Works

The application is built with Python and Flask. When you run the app, it:
1.  Scans the `static/images` directory for any image files (`.png`, `.jpg`, etc.).
2.  For each image, it sends a request to the Hugging Face API to generate a description.
3.  It then displays these images and their new alt tags in a web gallery.
4.  You have the option to download all this data as an Excel spreadsheet.

---

## ⚙️ Setup and Usage

Follow these steps to run the application on your local machine.

### 1. Prerequisites

-   Python 3.8+
-   A Hugging Face account with an API Access Token.

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

The application requires a Hugging Face API key to function.

1.  **Create a `.env` file.** You can do this by copying the example file:
    ```bash
    cp .env.example .env
    ```
2.  **Edit the `.env` file.** Open the newly created `.env` file in a text editor and replace `"your_huggingface_api_key_here"` with your actual Hugging Face API key.
    ```
    # .env
    HUGGINGFACE_API_KEY="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    ```

### 4. Add Images

Place any images you want to process into the `static/images` directory. The application will automatically detect and process them.

### 5. Running the Application

Once the setup is complete, you can start the Flask web server:
```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000`. Open this URL in your web browser to see the gallery.

---

## 🧪 Running Tests

This project includes a suite of unit tests to ensure the core logic is working correctly. To run the tests, execute the following command from the root directory of the project:

```bash
python -m unittest discover tests
```
