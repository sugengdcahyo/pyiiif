import pytest
from unittest.mock import Mock, patch
from app.services.slide import get_slide_dimensions, open_slide


class TestSlideService:
    """Test slide service operations"""
    
    @patch('openslide.OpenSlide')
    def test_get_slide_dimensions(self, mock_openslide):
        """Test getting slide dimensions"""
        mock_slide = Mock()
        mock_slide.dimensions = (10000, 8000)
        mock_openslide.return_value = mock_slide
        
        width, height = get_slide_dimensions('/path/to/slide.svs')
        
        assert width == 10000
        assert height == 8000
        
    @patch('openslide.OpenSlide')
    def test_open_slide_success(self, mock_openslide):
        """Test successfully opening a slide"""
        mock_slide = Mock()
        mock_openslide.return_value = mock_slide
        
        slide = open_slide('/path/to/slide.svs')
        
        assert slide is not None
        mock_openslide.assert_called_once_with('/path/to/slide.svs')
        
    @patch('openslide.OpenSlide')
    def test_open_slide_failure(self, mock_openslide):
        """Test handling slide open failure"""
        mock_openslide.side_effect = Exception("Cannot open slide")
        
        with pytest.raises(Exception):
            open_slide('/path/to/invalid.svs')
            
    @patch('openslide.OpenSlide')
    def test_get_slide_level_count(self, mock_openslide):
        """Test getting slide level count"""
        mock_slide = Mock()
        mock_slide.level_count = 5
        mock_openslide.return_value = mock_slide
        
        slide = open_slide('/path/to/slide.svs')
        
        assert slide.level_count == 5
        
    @patch('openslide.OpenSlide')
    def test_get_slide_level_dimensions(self, mock_openslide):
        """Test getting dimensions for each level"""
        mock_slide = Mock()
        mock_slide.level_dimensions = [
            (10000, 8000),
            (5000, 4000),
            (2500, 2000)
        ]
        mock_openslide.return_value = mock_slide
        
        slide = open_slide('/path/to/slide.svs')
        
        assert len(slide.level_dimensions) == 3
        assert slide.level_dimensions[0] == (10000, 8000)
        assert slide.level_dimensions[2] == (2500, 2000)