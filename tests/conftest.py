import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import io

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client"""
    with patch('boto3.client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def mock_flask_app():
    """Mock Flask app for testing"""
    from flask import Flask
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def sample_tiff_bytes():
    """Sample TIFF file bytes for testing"""
    # Minimal valid TIFF header
    return (
        b'II\x2a\x00'  # Little-endian TIFF magic
        b'\x08\x00\x00\x00'  # IFD offset
    )

@pytest.fixture
def sample_image_data():
    """Sample image data for PIL testing"""
    from PIL import Image
    img = Image.new('RGB', (100, 100), color='red')
    buf = io.BytesIO()
    img.save(buf, 'JPEG')
    buf.seek(0)
    return buf.getvalue()