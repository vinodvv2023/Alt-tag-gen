import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import requests

# Add the parent directory to the sys.path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, generate_alt_text, get_image_data

class AppTestCase(unittest.TestCase):
    def setUp(self):
        """Set up a test client for the Flask application."""
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()
        app.testing = True
        # Set a dummy API key for testing purposes
        os.environ['HUGGINGFACE_API_KEY'] = 'test_api_key'

    def tearDown(self):
        """Clean up after each test."""
        # Use pop to avoid KeyError if the key is already removed
        os.environ.pop('HUGGINGFACE_API_KEY', None)
        self.app_context.pop()

    @patch('app.requests.post')
    def test_generate_alt_text_success(self, mock_post):
        """Test generate_alt_text on successful API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'generated_text': 'a test description'}]
        mock_post.return_value = mock_response

        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            alt_text = generate_alt_text('dummy_path.jpg')

        self.assertEqual(alt_text, 'a test description')

    @patch('app.requests.post')
    def test_generate_alt_text_api_error(self, mock_post):
        """Test generate_alt_text when the API returns an error."""
        mock_post.side_effect = requests.exceptions.RequestException("API is down")

        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
            alt_text = generate_alt_text('dummy_path.jpg')

        self.assertIn('Error: API request failed', alt_text)

    def test_generate_alt_text_no_api_key(self):
        """Test generate_alt_text when the API key is not set."""
        os.environ.pop('HUGGINGFACE_API_KEY', None)
        alt_text = generate_alt_text('dummy_path.jpg')
        self.assertIn('HUGGINGFACE_API_KEY environment variable not set', alt_text)
        # Restore for other tests
        os.environ['HUGGINGFACE_API_KEY'] = 'test_api_key'

    @patch('app.os.path.isdir')
    @patch('app.os.listdir')
    @patch('app.generate_alt_text')
    def test_get_image_data(self, mock_generate_alt_text, mock_listdir, mock_isdir):
        """Test get_image_data with a mocked file system."""
        mock_isdir.return_value = True
        mock_listdir.return_value = ['test1.jpg', 'test2.png', 'document.txt']
        mock_generate_alt_text.return_value = 'mocked alt text'

        image_data = get_image_data()

        # Should ignore 'document.txt'
        self.assertEqual(len(image_data), 2)
        self.assertEqual(image_data[0]['filename'], 'test1.jpg')
        self.assertEqual(image_data[1]['alt_text'], 'mocked alt text')
        # Check that generate_alt_text was called for the image files
        self.assertEqual(mock_generate_alt_text.call_count, 2)

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
