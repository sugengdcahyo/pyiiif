import pytest
from unittest.mock import Mock, patch, MagicMock
from app.utils.s3range_reader import S3RangeReader


class TestS3RangeReader:
    """Test S3 range reading operations"""
    
    @patch('boto3.client')
    def test_s3range_reader_initialization(self, mock_boto_client):
        """Test S3RangeReader initialization"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        reader = S3RangeReader(
            bucket='test-bucket',
            key='test/file.tiff',
            region='us-east-1'
        )
        
        assert reader.bucket == 'test-bucket'
        assert reader.key == 'test/file.tiff'
        
    @patch('boto3.client')
    def test_read_bytes_at_offset(self, mock_boto_client):
        """Test reading bytes at specific offset"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=b'\x00\x01\x02\x03'))
        }
        
        reader = S3RangeReader('test-bucket', 'test/file.bin', 'us-east-1')
        data = reader.read(offset=100, length=4)
        
        assert data == b'\x00\x01\x02\x03'
        assert len(data) == 4
        
    @patch('boto3.client')
    def test_read_multiple_ranges(self, mock_boto_client):
        """Test reading multiple non-contiguous ranges"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Setup different responses for different ranges
        mock_client.get_object.side_effect = [
            {'Body': Mock(read=Mock(return_value=b'AAAA'))},
            {'Body': Mock(read=Mock(return_value=b'BBBB'))}
        ]
        
        reader = S3RangeReader('test-bucket', 'test/file.bin', 'us-east-1')
        data1 = reader.read(0, 4)
        data2 = reader.read(100, 4)
        
        assert data1 == b'AAAA'
        assert data2 == b'BBBB'
        assert mock_client.get_object.call_count == 2
        
    @patch('boto3.client')
    def test_read_with_invalid_range(self, mock_boto_client):
        """Test reading with invalid range raises error"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        from botocore.exceptions import ClientError
        mock_client.get_object.side_effect = ClientError(
            {'Error': {'Code': 'InvalidRange'}},
            'GetObject'
        )
        
        reader = S3RangeReader('test-bucket', 'test/file.bin', 'us-east-1')
        
        with pytest.raises(ClientError):
            reader.read(10000000, 100)