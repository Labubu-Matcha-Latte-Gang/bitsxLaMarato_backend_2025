from unittest.mock import patch

from tests.base_test import BaseTest


class TestFavicon(BaseTest):
    """
    Test suite for the favicon endpoint.
    Validates success cases, error handling, and MIME type correctness.
    """

    def test_favicon_returns_200_with_correct_mimetype(self):
        """Test that the favicon endpoint returns 200 with correct MIME type when file exists."""
        response = self.client.get('/favicon.ico')
        assert response.status_code == 200
        assert response.mimetype == 'image/vnd.microsoft.icon'

    def test_favicon_returns_valid_icon_data(self):
        """Test that the favicon endpoint returns actual icon data."""
        response = self.client.get('/favicon.ico')
        assert response.status_code == 200
        # Verify we got some binary data back
        assert len(response.data) > 0
        # ICO files typically start with specific bytes (0x00 0x00 0x01 0x00 or 0x00 0x00 0x02 0x00)
        # This is a basic validation that we received an icon file
        assert response.data[:2] == b'\x00\x00'

    def test_favicon_handles_malformed_path_gracefully(self):
        """Test that the favicon endpoint handles malformed paths without crashing."""
        # Mock FAVICON_PATH to a malformed path (no directory separator)
        with patch('resources.favicon.FAVICON_PATH', 'malformed'):
            response = self.client.get('/favicon.ico')
            # Should return an error (either 404 or 500) but not crash
            assert response.status_code in [404, 500]

    def test_favicon_caching_headers(self):
        """Test that appropriate caching headers could be set (optional check)."""
        response = self.client.get('/favicon.ico')
        assert response.status_code == 200
        # This is just validating the response is successful
        # Additional caching header validations could be added if implemented

    def test_favicon_content_disposition(self):
        """Test that the favicon is served inline (not as download)."""
        response = self.client.get('/favicon.ico')
        assert response.status_code == 200
        # By default, send_from_directory should serve inline
        # If Content-Disposition header is present, it should not be 'attachment'
        content_disposition = response.headers.get('Content-Disposition', '')
        assert 'attachment' not in content_disposition.lower()
