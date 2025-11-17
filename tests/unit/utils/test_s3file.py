import pytest
from unittest.mock import Mock, patch, MagicMock
from app.utils.s3file import S3File


class TestS3File:
    """Test S3 file operations"""
    
    @patch('boto3.client')
    def test_s3file_initialization(self, mock_boto_client):
        """Test S3File initialization"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        s3file = S3File(
            bucket='test-bucket',
            key='test/file.txt',
            region='us-east-1'
        )
        
        assert s3file.bucket == 'test-bucket'
        assert s3file.key == 'test/file.txt'
        
    @patch('boto3.client')
    def test_s3file_read_object(self, mock_boto_client):
        """Test reading object from S3"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=b'test content'))
        }
        
        s3file = S3File('test-bucket', 'test/file.txt', 'us-east-1')
        content = s3file.read()
        
        assert content == b'test content'
        mock_client.get_object.assert_called_once()
        
    @patch('boto3.client')
    def test_s3file_range_read(self, mock_boto_client):
        """Test range read from S3"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=b'partial'))
        }
        
        s3file = S3File('test-bucket', 'test/file.txt', 'us-east-1')
        content = s3file.read_range(0, 100)
        
        assert content == b'partial'
        call_args = mock_client.get_object.call_args
        assert 'Range' in call_args[1]
        
    @patch('boto3.client')
    def test_s3file_get_metadata(self, mock_boto_client):
        """Test getting object metadata"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.head_object.return_value = {
            'ContentLength': 12345,
            'ContentType': 'image/tiff'
        }
        
        s3file = S3File('test-bucket', 'test/file.tiff', 'us-east-1')
        metadata = s3file.get_metadata()
        
        assert metadata['ContentLength'] == 12345
        assert metadata['ContentType'] == 'image/tiff'