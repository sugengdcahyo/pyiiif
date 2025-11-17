import pytest
from app.utils.http import cache_headers, timed


class TestHttpUtils:
    """Test HTTP utility functions"""
    
    def test_cache_headers_with_default_params(self):
        """Test adding cache headers with default parameters"""
        from flask import Flask, Response
        app = Flask(__name__)
        
        with app.test_request_context():
            response = Response("test")
            cached_response = cache_headers(response)
            
            assert 'Cache-Control' in cached_response.headers
            cache_control = cached_response.headers['Cache-Control']
            assert 'public' in cache_control
            assert 'max-age' in cache_control
            
    def test_cache_headers_with_custom_max_age(self):
        """Test adding cache headers with custom max-age"""
        from flask import Flask, Response
        app = Flask(__name__)
        
        with app.test_request_context():
            response = Response("test")
            cached_response = cache_headers(response, seconds=3600)
            
            cache_control = cached_response.headers['Cache-Control']
            assert 'max-age=3600' in cache_control
            
    def test_cache_headers_with_immutable(self):
        """Test adding immutable directive"""
        from flask import Flask, Response
        app = Flask(__name__)
        
        with app.test_request_context():
            response = Response("test")
            cached_response = cache_headers(response, immutable=True)
            
            cache_control = cached_response.headers['Cache-Control']
            assert 'immutable' in cache_control
            
    def test_cache_headers_without_immutable(self):
        """Test cache headers without immutable"""
        from flask import Flask, Response
        app = Flask(__name__)
        
        with app.test_request_context():
            response = Response("test")
            cached_response = cache_headers(response, immutable=False)
            
            cache_control = cached_response.headers['Cache-Control']
            assert 'immutable' not in cache_control
            
    def test_cache_headers_returns_response(self):
        """Test function returns the response object"""
        from flask import Flask, Response
        app = Flask(__name__)
        
        with app.test_request_context():
            response = Response("test")
            cached_response = cache_headers(response)
            
            assert cached_response is response
            assert isinstance(cached_response, Response)
            
    def test_timed_decorator(self):
        """Test timed decorator for performance logging"""
        from unittest.mock import Mock
        
        mock_logger = Mock()
        
        @timed(mock_logger)
        def sample_function():
            return "result"
        
        result = sample_function()
        
        assert result == "result"
        # Logger debug should have been called
        assert mock_logger.debug.called