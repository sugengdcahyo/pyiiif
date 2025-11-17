import pytest
from pathlib import Path
from flask import Flask
from app.utils.path import safe_join_slide


class TestPathUtils:
    """Test path utility functions"""
    
    def test_safe_join_slide_basic(self):
        """Test basic path joining"""
        app = Flask(__name__)
        with app.test_request_context():
            base = Path("/base")
            result = safe_join_slide(base, "file.svs")
            assert "file.svs" in str(result)
        
    def test_safe_join_slide_prevents_traversal(self):
        """Test safe_join_slide prevents directory traversal"""
        app = Flask(__name__)
        with app.test_request_context():
            base = Path("/base")
            with pytest.raises(Exception):  # Will abort with 400
                safe_join_slide(base, "../etc/passwd")
            
    def test_safe_join_slide_with_subdirectories(self):
        """Test safe_join_slide with valid subdirectories"""
        app = Flask(__name__)
        with app.test_request_context():
            base = Path("/base")
            result = safe_join_slide(base, "sub/dir/file.svs")
            assert "sub" in str(result)
            assert "file.svs" in str(result)
        
    def test_safe_join_slide_removes_leading_slashes(self):
        """Test safe_join_slide handles leading slashes"""
        app = Flask(__name__)
        with app.test_request_context():
            base = Path("/base")
            result = safe_join_slide(base, "/file.svs")
            assert "file.svs" in str(result)
            assert ".." not in str(result)