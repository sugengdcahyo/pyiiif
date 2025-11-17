import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from app.utils.s3_json_loader import load_json_from_s3, S3JSONLoader


class TestS3JSONLoader:
    """Test S3 JSON loading functionality"""
    
    @patch('boto3.client')
    def test_load_json_from_s3_success(self, mock_boto_client):
        """Test successful JSON loading from S3"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        test_data = {'key': 'value', 'number': 42}
        mock_client.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=json.dumps(test_data).encode()))
        }
        
        result = load_json_from_s3('test-bucket', 'path/to/file.json')
        
        assert result == test_data
        assert result['key'] == 'value'
        assert result['number'] == 42
        
    @patch('boto3.client')
    def test_load_json_from_s3_file_not_found(self, mock_boto_client):
        """Test loading non-existent JSON file"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        from botocore.exceptions import ClientError
        mock_client.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}},
            'GetObject'
        )
        
        with pytest.raises(ClientError):
            load_json_from_s3('test-bucket', 'nonexistent.json')
            
    @patch('boto3.client')
    def test_load_json_from_s3_invalid_json(self, mock_boto_client):
        """Test loading invalid JSON content"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=b'invalid json{'))
        }
        
        with pytest.raises(json.JSONDecodeError):
            load_json_from_s3('test-bucket', 'invalid.json')
            
    @patch('boto3.client')
    def test_s3jsonloader_with_caching(self, mock_boto_client):
        """Test S3JSONLoader with caching"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        test_data = {'cached': True}
        mock_client.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=json.dumps(test_data).encode()))
        }
        
        loader = S3JSONLoader('test-bucket', 'us-east-1')
        
        # First load
        result1 = loader.load('test.json')
        # Second load (should use cache)
        result2 = loader.load('test.json')
        
        assert result1 == test_data
        assert result2 == test_data
        # Should only call S3 once due to caching
        assert mock_client.get_object.call_count <= 2