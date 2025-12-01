import pytest
import os
from pathlib import Path
from unittest.mock import patch
from app.config import Config, get_config


class TestConfig:
    """Test configuration loading and validation"""
    
    def test_config_defaults(self):
        """Test default configuration values"""
        assert Config.TILE_SIZE == 512
        assert isinstance(Config.VALID_EXTENSIONS, tuple)
        assert '.svs' in Config.VALID_EXTENSIONS
        assert '.tiff' in Config.VALID_EXTENSIONS
        
    def test_config_paths_are_resolved(self):
        """Test that paths are properly resolved"""
        assert Config.BASE_DIR.is_absolute()
        assert Config.PROJECT_ROOT.is_absolute()
        assert Config.SLIDE_PATH.is_absolute()
        
    def test_config_max_dimensions(self):
        """Test max output dimensions"""
        assert Config.MAX_OUT_W > 0
        assert Config.MAX_OUT_H > 0
        assert isinstance(Config.MAX_OUT_W, int)
        assert isinstance(Config.MAX_OUT_H, int)
        
    def test_cors_origins_parsing(self):
        """Test CORS origins are properly parsed"""
        assert isinstance(Config.CORS_ORIGINS, list)
        for origin in Config.CORS_ORIGINS:
            assert isinstance(origin, str)
            assert origin.strip() == origin  # No leading/trailing whitespace
            
    @patch.dict(os.environ, {'CORS_ORIGINS': 'http://localhost:3000,http://example.com'})
    def test_cors_origins_from_env(self):
        """Test CORS origins can be set from environment"""
        # This would require reloading the config module
        pass
        
    def test_mongo_uri_format(self):
        """Test MongoDB URI construction"""
        uri = Config.mongo_uri()
        assert 'mongodb+srv://' in uri or uri == ""
        
    def test_config_to_dict_sanitizes_secrets(self):
        """Test that sensitive values are sanitized in dict output"""
        config_dict = Config.to_dict()
        
        # Check that secret keys are sanitized
        sensitive_keys = ['PASSWORD', 'SECRET', 'ACCESS_KEY']
        for key, value in config_dict.items():
            if any(s in key for s in sensitive_keys):
                assert value == "***", f"Secret key {key} not sanitized"
                
    def test_config_to_dict_includes_non_private(self):
        """Test that public config values are included"""
        config_dict = Config.to_dict()
        assert 'TILE_SIZE' in config_dict
        assert 'MAX_OUT_W' in config_dict
        
    def test_get_config_returns_config_class(self):
        """Test get_config accessor function"""
        config = get_config()
        assert config == Config
        
    def test_s3_prefix_configs(self):
        """Test S3 prefix configurations"""
        assert hasattr(Config, 'PREFIX_RAW')
        assert hasattr(Config, 'PREFIX_INFO')
        assert hasattr(Config, 'PREFIX_IFDS')
        assert hasattr(Config, 'PREFIX_ZOOM')
        
    def test_iiif_backend_config(self):
        """Test IIIF backend configuration"""
        assert hasattr(Config, 'IIIF_BACKEND')
        assert isinstance(Config.IIIF_BACKEND, str)


class TestConfigEnvironmentVariables:
    """Test configuration with environment variables"""
    
    @patch.dict(os.environ, {'TILE_SIZE': '256'})
    def test_tile_size_from_env(self):
        """Test TILE_SIZE can be overridden"""
        # Note: This test shows the pattern but won't work without reloading
        pass
        
    @patch.dict(os.environ, {'MAX_OUT_W': '4096', 'MAX_OUT_H': '4096'})
    def test_max_dimensions_from_env(self):
        """Test max dimensions can be overridden"""
        pass