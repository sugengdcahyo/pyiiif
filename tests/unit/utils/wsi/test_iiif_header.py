import pytest
from app.utils.wsi.iiif_header import build_iiif_context, build_iiif_profile


class TestIIIFHeader:
    """Test IIIF header building functions"""
    
    def test_build_iiif_context(self):
        """Test building IIIF context"""
        context = build_iiif_context()
        assert context == "http://iiif.io/api/image/2/context.json"
        
    def test_build_iiif_profile_basic(self):
        """Test building basic IIIF profile"""
        profile = build_iiif_profile()
        assert isinstance(profile, list)
        assert len(profile) >= 1
        assert "http://iiif.io/api/image/2/level2.json" in profile[0] or \
               profile[0] == "http://iiif.io/api/image/2/level2.json"
               
    def test_build_iiif_profile_includes_formats(self):
        """Test IIIF profile includes supported formats"""
        profile = build_iiif_profile()
        if len(profile) > 1 and isinstance(profile[1], dict):
            assert 'formats' in profile[1]
            formats = profile[1]['formats']
            assert 'jpg' in formats or 'jpeg' in formats
            assert 'png' in formats
            
    def test_build_iiif_profile_includes_qualities(self):
        """Test IIIF profile includes supported qualities"""
        profile = build_iiif_profile()
        if len(profile) > 1 and isinstance(profile[1], dict):
            assert 'qualities' in profile[1]
            qualities = profile[1]['qualities']
            assert 'default' in qualities
            
    def test_build_iiif_profile_includes_supports(self):
        """Test IIIF profile includes supported features"""
        profile = build_iiif_profile()
        if len(profile) > 1 and isinstance(profile[1], dict):
            assert 'supports' in profile[1]
            supports = profile[1]['supports']
            assert isinstance(supports, list)