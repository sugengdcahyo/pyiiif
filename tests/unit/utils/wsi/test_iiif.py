import pytest
from unittest.mock import Mock, MagicMock
from app.utils.wsi.iiif import IIIFInfoBuilder, ZoomLevelBuilder


class TestIIIFInfoBuilder:
    """Test IIIF info document building"""
    
    def test_iiif_info_builder_initialization(self):
        """Test IIIFInfoBuilder initialization"""
        mock_explorer = Mock()
        builder = IIIFInfoBuilder(mock_explorer)
        
        assert builder.explorer == mock_explorer
        
    def test_build_iiif_info_structure(self):
        """Test building IIIF info document structure"""
        mock_explorer = Mock()
        mock_explorer.width = 10000
        mock_explorer.height = 8000
        mock_explorer.levels = [
            {'width': 10000, 'height': 8000},
            {'width': 5000, 'height': 4000},
            {'width': 2500, 'height': 2000}
        ]
        
        builder = IIIFInfoBuilder(mock_explorer)
        info = builder.build()
        
        assert '@context' in info
        assert 'width' in info
        assert 'height' in info
        assert info['width'] == 10000
        assert info['height'] == 8000
        
    def test_build_iiif_info_includes_tiles(self):
        """Test IIIF info includes tiles configuration"""
        mock_explorer = Mock()
        mock_explorer.width = 10000
        mock_explorer.height = 8000
        mock_explorer.tile_width = 512
        mock_explorer.tile_height = 512
        mock_explorer.levels = [{'width': 10000, 'height': 8000}]
        
        builder = IIIFInfoBuilder(mock_explorer)
        info = builder.build()
        
        assert 'tiles' in info
        assert isinstance(info['tiles'], list)
        assert len(info['tiles']) > 0
        
    def test_build_iiif_info_includes_profile(self):
        """Test IIIF info includes profile"""
        mock_explorer = Mock()
        mock_explorer.width = 10000
        mock_explorer.height = 8000
        mock_explorer.levels = [{'width': 10000, 'height': 8000}]
        
        builder = IIIFInfoBuilder(mock_explorer)
        info = builder.build()
        
        assert 'profile' in info


class TestZoomLevelBuilder:
    """Test zoom level building"""
    
    def test_zoom_level_builder_initialization(self):
        """Test ZoomLevelBuilder initialization"""
        builder = ZoomLevelBuilder()
        assert builder is not None
        
    def test_build_zoom_levels_from_info(self):
        """Test building zoom levels from IIIF info"""
        info = {
            'width': 10000,
            'height': 8000,
            'tiles': [{
                'width': 512,
                'height': 512,
                'scaleFactors': [1, 2, 4, 8]
            }]
        }
        
        builder = ZoomLevelBuilder()
        zoom = builder.build(info=info)
        
        assert 'levels' in zoom
        assert isinstance(zoom['levels'], list)
        
    def test_zoom_levels_include_scale_factors(self):
        """Test zoom levels include scale factors"""
        info = {
            'width': 10000,
            'height': 8000,
            'tiles': [{
                'width': 512,
                'height': 512,
                'scaleFactors': [1, 2, 4, 8, 16]
            }]
        }
        
        builder = ZoomLevelBuilder()
        zoom = builder.build(info=info)
        
        assert len(zoom['levels']) > 0
        for level in zoom['levels']:
            assert 'downsample' in level or 'scale' in level