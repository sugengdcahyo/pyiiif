import pytest
from flask import Flask
from app.errors import register_error_handlers


class TestErrorHandlers:
    """Test error handler registration and behavior"""
    
    def test_register_error_handlers(self):
        """Test error handlers can be registered"""
        app = Flask(__name__)
        register_error_handlers(app)
        
        # Check handlers are registered
        assert 400 in app.error_handler_spec[None]
        assert 404 in app.error_handler_spec[None]
        assert 500 in app.error_handler_spec[None]
        
    def test_400_error_returns_json(self):
        """Test 400 error returns JSON response"""
        app = Flask(__name__)
        register_error_handlers(app)
        
        @app.route('/test400')
        def trigger_400():
            from flask import abort
            abort(400, description="Bad request test")
            
        with app.test_client() as client:
            response = client.get('/test400')
            assert response.status_code == 400
            assert response.is_json
            data = response.get_json()
            assert 'error' in data
            assert 'status' in data
            assert data['status'] == 400
            
    def test_404_error_returns_json(self):
        """Test 404 error returns JSON response"""
        app = Flask(__name__)
        register_error_handlers(app)
        
        with app.test_client() as client:
            response = client.get('/nonexistent')
            assert response.status_code == 404
            assert response.is_json
            data = response.get_json()
            assert 'error' in data
            assert 'status' in data
            assert data['status'] == 404
            
    def test_500_error_returns_json(self):
        """Test 500 error returns JSON response"""
        app = Flask(__name__)
        register_error_handlers(app)
        
        @app.route('/test500')
        def trigger_500():
            raise Exception("Internal server error test")
            
        with app.test_client() as client:
            response = client.get('/test500')
            assert response.status_code == 500
            assert response.is_json
            data = response.get_json()
            assert 'error' in data
            assert 'status' in data
            
    def test_error_response_structure(self):
        """Test error response has correct structure"""
        app = Flask(__name__)
        register_error_handlers(app)
        
        @app.route('/test')
        def trigger_error():
            from flask import abort
            abort(400, description="Test error message")
            
        with app.test_client() as client:
            response = client.get('/test')
            data = response.get_json()
            assert isinstance(data, dict)
            assert 'error' in data
            assert 'status' in data
            assert isinstance(data['error'], str)
            assert isinstance(data['status'], int)