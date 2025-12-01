import pytest
from unittest.mock import Mock, patch, MagicMock
from app.utils.wsi.io import S3RangeReader


class TestS3RangeReader:
    """Test S3 range reading for WSI files"""
    
    @patch('boto3.client')
    def test_s3_range_reader_initialization(self, mock_boto_client):
        """Test S3RangeReader initialization"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        reader = S3RangeReader(
            bucket='wsi-bucket',
            key='slides/sample.svs',
            region_name='us-east-1',
            aws_access_key_id='AKIATEST',
            aws_secret_access_key='secret'
        )
        
        assert reader.bucket == 'wsi-bucket'
        assert reader.key == 'slides/sample.svs'
        
    @patch('boto3.client')
    def test_read_header_bytes(self, mock_boto_client):
        """Test reading header bytes from WSI file"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # TIFF header
        mock_client.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=b'II\x2a\x00\x08\x00\x00\x00'))
        }
        
        reader = S3RangeReader('bucket', 'key', 'us-east-1', 'key', 'secret')
        header = reader.read(0, 8)
        
        assert header[:2] in (b'II', b'MM')  # TIFF magic bytes
        assert len(header) == 8
        
    @patch('boto3.client')
    def test_read_tile_data(self, mock_boto_client):
        """Test reading tile data from specific offset"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=b'\xff\xd8\xff\xe0' + b'\x00' * 1000))
        }
        
        reader = S3RangeReader('bucket', 'key', 'us-east-1', 'key', 'secret')
        tile_data = reader.read(10000, 1004)
        
        assert tile_data[:2] == b'\xff\xd8'  # JPEG SOI marker
        assert len(tile_data) == 1004
        
    @patch('boto3.client')
    def test_read_with_retries_on_failure(self, mock_boto_client):
        """Test read retries on transient failures"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # First call fails, second succeeds
        from botocore.exceptions import ClientError
        mock_client.get_object.side_effect = [
            ClientError({'Error': {'Code': '500'}}, 'GetObject'),
            {'Body': Mock(read=Mock(return_value=b'data'))}
        ]
        
        reader = S3RangeReader('bucket', 'key', 'us-east-1', 'key', 'secret')
        
        # Should succeed after retry
        data = reader.read(0, 4)
        assert data == b'data'