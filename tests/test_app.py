import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import requests
import ollama

# Add the parent directory to the sys.path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import from app
from app import app, generate_alt_text_huggingface, generate_alt_text_ollama, generate_alt_text, image_cache

class BackendTestCase(unittest.TestCase):
    """Tests for the individual backend functions, isolated from the app."""

    def setUp(self):
        os.environ['HUGGINGFACE_API_KEY'] = 'test_api_key'

    def tearDown(self):
        os.environ.pop('HUGGINGFACE_API_KEY', None)

    # --- Hugging Face Backend Tests ---
    @patch('app.requests.post')
    def test_generate_alt_text_huggingface_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'generated_text': 'a test description'}]
        mock_post.return_value = mock_response
        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            self.assertEqual(generate_alt_text_huggingface('dummy.jpg'), 'a test description')

    @patch('app.requests.post')
    def test_generate_alt_text_huggingface_api_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException("API is down")
        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            self.assertIn('Error: Hugging Face API request failed', generate_alt_text_huggingface('dummy.jpg'))

    # --- Ollama Backend Tests ---
    @patch('app.ollama.chat')
    def test_generate_alt_text_ollama_success(self, mock_ollama_chat):
        mock_ollama_chat.return_value = {'message': {'content': 'a local description'}}
        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            self.assertEqual(generate_alt_text_ollama('dummy.jpg'), 'a local description')

    @patch('app.ollama.chat')
    def test_generate_alt_text_ollama_api_error(self, mock_ollama_chat):
        mock_ollama_chat.side_effect = ollama.ResponseError("Ollama is down")
        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            self.assertIn('Error: Ollama API request failed', generate_alt_text_ollama('dummy.jpg'))

class DispatcherAndRouteTestCase(unittest.TestCase):
    """Tests for the dispatcher, routes, and caching logic."""

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()
        app.testing = True
        # Clear the cache before each test
        image_cache.clear()

    def tearDown(self):
        image_cache.clear()
        os.environ.pop('AI_BACKEND', None)
        self.app_context.pop()

    # --- Dispatcher Tests ---
    @patch('app.generate_alt_text_huggingface')
    @patch.dict(os.environ, {"AI_BACKEND": "huggingface"})
    def test_dispatcher_calls_huggingface(self, mock_hf_func):
        generate_alt_text('dummy.jpg')
        mock_hf_func.assert_called_once_with('dummy.jpg')

    @patch('app.generate_alt_text_ollama')
    @patch.dict(os.environ, {"AI_BACKEND": "ollama"})
    def test_dispatcher_calls_ollama(self, mock_ollama_func):
        generate_alt_text('dummy.jpg')
        mock_ollama_func.assert_called_once_with('dummy.jpg')

    # --- Route and Cache Tests ---
    @patch('app.update_cache')
    def test_index_route_shows_empty_message(self, mock_update_cache):
        """Test that the index route does not call update_cache and shows the empty message."""
        response = self.client.get('/')
        mock_update_cache.assert_not_called()
        self.assertIn(b"No images found", response.data)

    @patch('app.update_cache')
    def test_index_route_uses_existing_cache(self, mock_update_cache):
        """Test that the index route does not call update_cache if cache is not empty."""
        image_cache.append({'filename': 'test.jpg', 'alt_text': 'cached text'})
        response = self.client.get('/')
        mock_update_cache.assert_not_called()
        self.assertIn(b'cached text', response.data)

    @patch('app.update_cache')
    def test_refresh_route(self, mock_update_cache):
        """Test that the /refresh route calls update_cache."""
        response = self.client.get('/refresh', follow_redirects=True)
        mock_update_cache.assert_called_once()
        self.assertEqual(response.status_code, 200)

    def test_clear_route(self):
        """Test that the /clear route empties the cache."""
        # Populate the cache first
        image_cache.append({'filename': 'test.jpg', 'alt_text': 'cached text'})
        self.assertEqual(len(image_cache), 1)
        # Hit the clear route
        self.client.get('/clear')
        # Check that the cache is now empty
        self.assertEqual(len(image_cache), 0)

    @patch('app.update_cache')
    def test_download_excel_route(self, mock_update_cache):
        """Test the Excel download route uses the cache."""
        image_cache.append({'filename': 'test1.jpg', 'alt_text': 'cached excel text'})
        response = self.client.get('/download_excel')
        # update_cache should not be called, it should use the existing cache
        mock_update_cache.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    unittest.main()
