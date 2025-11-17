import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from app.logger import setup_logger, redact_sensitive_data


class TestLogger:
    """Test logging setup and configuration"""
    
    def test_setup_logger_creates_log_directory(self, tmp_path):
        """Test setup_logger creates log directory"""
        from flask import Flask
        app = Flask(__name__)
        app.config['LOG_DIR'] = str(tmp_path / "logs")
        
        setup_logger(app)
        
        log_dir = Path(app.config['LOG_DIR'])
        assert log_dir.exists()
        assert log_dir.is_dir()
        
    def test_setup_logger_adds_handlers(self):
        """Test setup_logger adds appropriate handlers"""
        from flask import Flask
        app = Flask(__name__)
        
        setup_logger(app)
        
        # Should have at least console + file handlers
        assert len(app.logger.handlers) >= 2
        
    def test_setup_logger_sets_log_level(self):
        """Test setup_logger sets correct log level"""
        from flask import Flask
        app = Flask(__name__)
        app.config['LOG_LEVEL'] = 'DEBUG'
        
        setup_logger(app)
        
        assert app.logger.level == logging.DEBUG
        
    def test_setup_logger_with_info_level(self):
        """Test setup_logger with INFO level"""
        from flask import Flask
        app = Flask(__name__)
        app.config['LOG_LEVEL'] = 'INFO'
        
        setup_logger(app)
        
        assert app.logger.level == logging.INFO
        
    def test_logger_no_propagation(self):
        """Test logger doesn't propagate to avoid duplicates"""
        from flask import Flask
        app = Flask(__name__)
        
        setup_logger(app)
        
        assert app.logger.propagate is False
        
    def test_redact_sensitive_data_removes_secrets(self):
        """Test sensitive data is redacted"""
        record = {
            'AWS_ACCESS_KEY_ID': 'AKIAIOSFODNN7EXAMPLE',
            'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'PASSWORD': 'secret123',
            'USERNAME': 'john_doe',
            'LOG_LEVEL': 'INFO'
        }
        
        redacted = redact_sensitive_data(record)
        
        assert redacted['AWS_ACCESS_KEY_ID'] == '***'
        assert redacted['AWS_SECRET_ACCESS_KEY'] == '***'
        assert redacted['PASSWORD'] == '***'
        assert redacted['USERNAME'] == 'john_doe'  # Not sensitive
        assert redacted['LOG_LEVEL'] == 'INFO'  # Not sensitive
        
    def test_redact_sensitive_data_case_insensitive(self):
        """Test redaction is case-insensitive"""
        record = {
            'password': 'secret',
            'Password': 'secret',
            'PASSWORD': 'secret',
            'api_token': 'token123',
            'API_TOKEN': 'token123'
        }
        
        redacted = redact_sensitive_data(record)
        
        for key in record.keys():
            if 'password' in key.lower() or 'token' in key.lower():
                assert redacted[key] == '***'
                
    def test_redact_sensitive_data_preserves_structure(self):
        """Test redaction preserves record structure"""
        record = {
            'key1': 'value1',
            'SECRET_KEY': 'secret',
            'key2': 'value2'
        }
        
        redacted = redact_sensitive_data(record)
        
        assert set(redacted.keys()) == set(record.keys())
        assert len(redacted) == len(record)