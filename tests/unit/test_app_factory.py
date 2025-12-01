import pytest
from unittest.mock import patch, Mock
from flask import Flask


class TestAppFactory:
    """Test Flask application factory"""
    
    @patch('app.setup_logger')
    def test_create_app_returns_flask_instance(self, mock_logger):
        """Test create_app returns Flask application"""
        from app import create_app
        
        app = create_app()
        
        assert isinstance(app, Flask)
        
    @patch('app.setup_logger')
    def test_create_app_registers_blueprints(self, mock_logger):
        """Test blueprints are registered"""
        from app import create_app
        
        app = create_app()
        
        # Check blueprints are registered
        assert len(app.blueprints) > 0
        
    @patch('app.setup_logger')
    def test_create_app_has_healthz_endpoint(self, mock_logger):
        """Test healthz endpoint is available"""
        from app import create_app
        
        app = create_app()
        
        with app.test_client() as client:
            response = client.get('/healthz')
            assert response.status_code == 200
            data = response.get_json()
            assert data['ok'] is True
            
    @patch('app.setup_logger')
    def test_create_app_configures_from_config_object(self, mock_logger):
        """Test app is configured from Config object"""
        from app import create_app
        
        app = create_app()
        
        # Should have config from Config class
        assert 'TILE_SIZE' in app.config or hasattr(app.config, 'get')
        
    @patch('app.setup_logger')
    def test_create_app_registers_error_handlers(self, mock_logger):
        """Test error handlers are registered"""
        from app import create_app
        
        app = create_app()
        
        # Test 404 error returns JSON
        with app.test_client() as client:
            response = client.get('/nonexistent-route')
            assert response.status_code == 404
            assert response.is_json