import pytest
from PIL import Image
import io
from app.utils.image import (
    save_to_bytes, JpegOpts, JPEG_DEFAULT, PNG_OPTS,
    pick_level_for_target, level_dims
)


class TestImageUtils:
    """Test image utility functions"""
    
    def test_jpeg_opts_defaults(self):
        """Test default JPEG options"""
        opts = JPEG_DEFAULT
        assert opts.quality == 80
        assert opts.optimize is True
        assert opts.progressive is True
        
    def test_save_to_bytes_jpeg(self):
        """Test saving image as JPEG"""
        img = Image.new('RGB', (100, 100), color='red')
        data = save_to_bytes(img, 'JPEG')
        
        assert len(data) > 0
        assert data[:2] == b'\xff\xd8'  # JPEG SOI marker
        
    def test_save_to_bytes_png(self):
        """Test saving image as PNG"""
        img = Image.new('RGB', (100, 100), color='blue')
        data = save_to_bytes(img, 'PNG')
        
        assert len(data) > 0
        assert data[:8] == b'\x89PNG\r\n\x1a\n'  # PNG signature
        
    def test_save_to_bytes_with_custom_quality(self):
        """Test saving with custom JPEG quality"""
        img = Image.new('RGB', (100, 100), color='green')
        opts = JpegOpts(quality=50)
        data = save_to_bytes(img, 'JPEG', opts)
        
        assert len(data) > 0
        
    def test_save_to_bytes_converts_rgba_to_rgb(self):
        """Test RGBA is converted to RGB for JPEG"""
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        data = save_to_bytes(img, 'JPEG')
        
        # Should not raise error
        assert len(data) > 0
        
    def test_pick_level_for_target(self):
        """Test picking optimal pyramid level"""
        from unittest.mock import Mock
        
        slide = Mock()
        slide.level_downsamples = [1.0, 2.0, 4.0, 8.0]
        
        # Request close to level 2 (4x downsample)
        level = pick_level_for_target(slide, 4000, 3000, 1000, 750)
        
        assert 0 <= level < len(slide.level_downsamples)
        
    def test_level_dims_calculates_correctly(self):
        """Test level dimensions calculation"""
        from unittest.mock import Mock
        
        slide = Mock()
        slide.level_downsamples = [1.0, 2.0, 4.0]
        
        rw, rh, scale = level_dims(slide, level=1, w=1000, h=800)
        
        assert scale == 2.0
        assert rw == 500
        assert rh == 400


class TestJpegOpts:
    """Test JPEG options dataclass"""
    
    def test_jpeg_opts_initialization(self):
        """Test JpegOpts with custom values"""
        opts = JpegOpts(quality=90, optimize=False, progressive=False)
        
        assert opts.quality == 90
        assert opts.optimize is False
        assert opts.progressive is False
        
    def test_jpeg_opts_subsampling(self):
        """Test JpegOpts with subsampling"""
        opts = JpegOpts(subsampling=0)
        assert opts.subsampling == 0
        
        opts2 = JpegOpts(subsampling="4:2:0")
        assert opts2.subsampling == "4:2:0"