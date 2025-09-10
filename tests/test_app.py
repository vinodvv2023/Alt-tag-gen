import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import io
import pandas as pd
import requests
import ollama
from bs4 import BeautifulSoup

# Add the parent directory to the sys.path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import from app
from app import app, generate_alt_text_huggingface, generate_alt_text_ollama, generate_alt_text, get_image_bytes, image_cache

class HelperFunctionTestCase(unittest.TestCase):
    """Tests for the get_image_bytes helper function."""

    @patch('app.requests.get')
    def test_get_image_bytes_from_url_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake_url_image_data'
        mock_get.return_value = mock_response
        image_bytes = get_image_bytes('http://example.com/image.jpg')
        self.assertEqual(image_bytes, b'fake_url_image_data')

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b'fake_local_image_data')
    def test_get_image_bytes_from_local_path_success(self, mock_open):
        image_bytes = get_image_bytes('/path/to/local/image.jpg')
        self.assertEqual(image_bytes, b'fake_local_image_data')

class BackendTestCase(unittest.TestCase):
    """Tests for the individual backend functions, isolated from the app."""

    def setUp(self):
        os.environ['HUGGINGFACE_API_KEY'] = 'test_api_key'

    def tearDown(self):
        os.environ.pop('HUGGINGFACE_API_KEY', None)

    @patch('app.get_image_bytes', return_value=b'fake_image_data')
    @patch('app.requests.post')
    def test_generate_alt_text_huggingface_success(self, mock_post, mock_get_bytes):
        mock_response = MagicMock()
        mock_response.json.return_value = [{'generated_text': 'a test description'}]
        mock_post.return_value = mock_response
        self.assertEqual(generate_alt_text_huggingface('dummy.jpg'), 'a test description')

    @patch('app.get_image_bytes', side_effect=FileNotFoundError("File not found"))
    def test_generate_alt_text_huggingface_file_not_found(self, mock_get_bytes):
        self.assertIn('Error: Failed to get image data.', generate_alt_text_huggingface('dummy.jpg'))

    @patch('app.get_image_bytes', return_value=b'fake_image_data')
    @patch('app.ollama.chat')
    def test_generate_alt_text_ollama_success(self, mock_ollama_chat, mock_get_bytes):
        mock_ollama_chat.return_value = {'message': {'content': 'a local description'}}
        self.assertEqual(generate_alt_text_ollama('dummy.jpg'), 'a local description')

class DispatcherAndRouteTestCase(unittest.TestCase):
    """Tests for the dispatcher, routes, and caching logic."""

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()
        app.testing = True
        image_cache.clear()

    def tearDown(self):
        image_cache.clear()
        os.environ.pop('AI_BACKEND', None)
        self.app_context.pop()

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

    @patch('app.update_cache_from_folder')
    def test_index_route_shows_empty_message(self, mock_update_cache):
        response = self.client.get('/')
        self.assertIn(b"No images found", response.data)

    @patch('app.update_cache_from_folder')
    def test_index_route_uses_existing_cache(self, mock_update_cache):
        image_cache.append({'filename': 'test.jpg', 'alt_text': 'cached text'})
        response = self.client.get('/')
        mock_update_cache.assert_not_called()
        self.assertIn(b'cached text', response.data)

    @patch('app.update_cache_from_folder')
    def test_refresh_route(self, mock_update_cache):
        response = self.client.get('/refresh', follow_redirects=True)
        mock_update_cache.assert_called_once()

    def test_clear_route(self):
        image_cache.append({'filename': 'test.jpg', 'alt_text': 'cached text'})
        self.client.get('/clear')
        self.assertEqual(len(image_cache), 0)

    @patch('app.generate_alt_text')
    def test_upload_excel_route_success(self, mock_generate_alt_text):
        mock_generate_alt_text.return_value = "mocked alt text"
        df = pd.DataFrame({'Image Name': ['img1.jpg'], 'Image Path': ['/path/to/img1.jpg']})
        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        response = self.client.post(
            '/upload',
            content_type='multipart/form-data',
            data={'excel_file': (output, 'test.xlsx')},
            follow_redirects=True
        )
        self.assertEqual(len(image_cache), 1)
        self.assertIn(b"Successfully processed 1 rows", response.data)

    def test_apply_html_empty_cache(self):
        dummy_html = io.BytesIO(b'<html></html>')
        response = self.client.post(
            '/apply_html',
            content_type='multipart/form-data',
            data={'html_file': (dummy_html, 'test.html')},
            follow_redirects=True
        )
        self.assertIn(b"Cache is empty", response.data)

    def test_apply_html_success_and_unmatched(self):
        image_cache.append({'filename': 'image1.jpg', 'alt_text': 'This is image one.'})
        image_cache.append({'filename': 'unmatched.png', 'alt_text': 'This image is not in the HTML.'})
        html_content = "<html><body><img src='/images/image1.jpg'><img src='image2.png'></body></html>"
        dummy_html_file = io.BytesIO(html_content.encode('utf-8'))
        response = self.client.post(
            '/apply_html',
            content_type='multipart/form-data',
            data={'html_file': (dummy_html_file, 'test.html')},
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.data, 'html.parser')
        img_tag = soup.find('img', src='/images/image1.jpg')
        self.assertEqual(img_tag['alt'], 'This is image one.')
        with self.client.session_transaction() as session:
            self.assertIn('unmatched.png', session['_flashes'][0][1])

if __name__ == '__main__':
    unittest.main()
