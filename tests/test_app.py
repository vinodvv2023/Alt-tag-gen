import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import requests
import ollama

# Add the parent directory to the sys.path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import from app
from app import app, generate_alt_text_huggingface, generate_alt_text_ollama, get_image_data, generate_alt_text

class AppTestCase(unittest.TestCase):
    def setUp(self):
        """Set up a test client for the Flask application."""
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()
        app.testing = True
        os.environ['HUGGINGFACE_API_KEY'] = 'test_api_key'

    def tearDown(self):
        """Clean up after each test."""
        os.environ.pop('HUGGINGFACE_API_KEY', None)
        os.environ.pop('AI_BACKEND', None)
        self.app_context.pop()

    # --- Hugging Face Backend Tests ---
    @patch('app.requests.post')
    def test_generate_alt_text_huggingface_success(self, mock_post):
        """Test generate_alt_text_huggingface on successful API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'generated_text': 'a test description'}]
        mock_post.return_value = mock_response

        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            alt_text = generate_alt_text_huggingface('dummy_path.jpg')

        self.assertEqual(alt_text, 'a test description')

    @patch('app.requests.post')
    def test_generate_alt_text_huggingface_api_error(self, mock_post):
        """Test generate_alt_text_huggingface when the API returns an error."""
        mock_post.side_effect = requests.exceptions.RequestException("API is down")

        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            alt_text = generate_alt_text_huggingface('dummy_path.jpg')

        self.assertIn('Error: Hugging Face API request failed', alt_text)

    def test_generate_alt_text_huggingface_no_api_key(self):
        """Test generate_alt_text_huggingface when the API key is not set."""
        os.environ.pop('HUGGINGFACE_API_KEY', None)
        alt_text = generate_alt_text_huggingface('dummy_path.jpg')
        self.assertIn('HUGGINGFACE_API_KEY environment variable not set', alt_text)

    # --- Ollama Backend Tests ---
    @patch('app.ollama.Client')
    def test_generate_alt_text_ollama_success(self, mock_ollama_client):
        """Test generate_alt_text_ollama on successful API call."""
        mock_instance = mock_ollama_client.return_value
        mock_instance.chat.return_value = {'message': {'content': 'a local description'}}

        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            alt_text = generate_alt_text_ollama('dummy_path.jpg')

        self.assertEqual(alt_text, 'a local description')

    @patch('app.ollama.Client')
    def test_generate_alt_text_ollama_api_error(self, mock_ollama_client):
        """Test generate_alt_text_ollama when the API returns an error."""
        mock_instance = mock_ollama_client.return_value
        mock_instance.chat.side_effect = ollama.ResponseError("Ollama is down")

        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            alt_text = generate_alt_text_ollama('dummy_path.jpg')

        self.assertIn('Error: Ollama API request failed', alt_text)

    # --- Dispatcher Tests ---
    @patch('app.generate_alt_text_huggingface')
    @patch.dict(os.environ, {"AI_BACKEND": "huggingface"})
    def test_dispatcher_calls_huggingface(self, mock_hf_func):
        """Test that the dispatcher calls the Hugging Face function."""
        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            generate_alt_text('dummy_path.jpg')
        mock_hf_func.assert_called_once_with('dummy_path.jpg')

    @patch('app.generate_alt_text_ollama')
    @patch.dict(os.environ, {"AI_BACKEND": "ollama"})
    def test_dispatcher_calls_ollama(self, mock_ollama_func):
        """Test that the dispatcher calls the Ollama function."""
        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            generate_alt_text('dummy_path.jpg')
        mock_ollama_func.assert_called_once_with('dummy_path.jpg')

    @patch.dict(os.environ, {"AI_BACKEND": "invalid_backend"})
    def test_dispatcher_handles_invalid_backend(self):
        """Test that the dispatcher returns an error for an invalid backend."""
        # This test doesn't need to open a file, as it should fail before that.
        result = generate_alt_text('dummy_path.jpg')
        self.assertIn("Invalid AI_BACKEND configured", result)

    # --- Route and High-Level Tests (remain mostly unchanged) ---
    @patch('app.get_image_data')
    def test_index_route(self, mock_get_image_data):
        """Test the main index route ('/')."""
        mock_get_image_data.return_value = [{'filename': 'test.jpg', 'alt_text': 'a test image'}]

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Image Alt Tag Gallery', response.data)
        self.assertIn(b'test.jpg', response.data)

    @patch('app.get_image_data')
    def test_download_excel_route(self, mock_get_image_data):
        """Test the Excel download route ('/download_excel')."""
        mock_get_image_data.return_value = [
            {'filename': 'test1.jpg', 'alt_text': 'first image'},
            {'filename': 'test2.png', 'alt_text': 'second image'}
        ]

        response = self.client.get('/download_excel')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment; filename=alt_tags.xlsx', response.headers['Content-Disposition'])

if __name__ == '__main__':
    unittest.main()
