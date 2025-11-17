import pytest
from app.utils.wsi.ifds import IFD, IFDCollection


class TestIFD:
    """Test IFD (Image File Directory) class"""
    
    def test_ifd_initialization(self):
        """Test IFD initialization with basic parameters"""
        ifd = IFD(
            level=0,
            width=1024,
            height=768,
            tile_width=256,
            tile_height=256
        )
        assert ifd.level == 0
        assert ifd.width == 1024
        assert ifd.height == 768
        assert ifd.tile_width == 256
        assert ifd.tile_height == 256
        
    def test_ifd_tile_count_calculation(self):
        """Test IFD calculates tile counts correctly"""
        ifd = IFD(
            level=0,
            width=1024,
            height=768,
            tile_width=256,
            tile_height=256
        )
        assert ifd.tiles_x == 4  # 1024 / 256
        assert ifd.tiles_y == 3  # 768 / 256
        
    def test_ifd_total_tiles(self):
        """Test IFD calculates total tiles"""
        ifd = IFD(
            level=0,
            width=1024,
            height=768,
            tile_width=256,
            tile_height=256
        )
        assert ifd.total_tiles == 12  # 4 * 3
        
    def test_ifd_with_partial_tiles(self):
        """Test IFD with non-even dimensions"""
        ifd = IFD(
            level=0,
            width=1000,
            height=700,
            tile_width=256,
            tile_height=256
        )
        # Should round up
        assert ifd.tiles_x >= 3
        assert ifd.tiles_y >= 2
        
    def test_ifd_downsampling_factor(self):
        """Test IFD with downsampling factor"""
        ifd = IFD(
            level=1,
            width=512,
            height=384,
            tile_width=256,
            tile_height=256,
            downsample=2.0
        )
        assert ifd.downsample == 2.0
        

class TestIFDCollection:
    """Test IFD collection management"""
    
    def test_ifd_collection_initialization(self):
        """Test IFDCollection initialization"""
        collection = IFDCollection()
        assert len(collection.ifds) == 0
        
    def test_add_ifd_to_collection(self):
        """Test adding IFD to collection"""
        collection = IFDCollection()
        ifd = IFD(0, 1024, 768, 256, 256)
        collection.add(ifd)
        assert len(collection.ifds) == 1
        
    def test_get_ifd_by_level(self):
        """Test retrieving IFD by level"""
        collection = IFDCollection()
        ifd0 = IFD(0, 1024, 768, 256, 256)
        ifd1 = IFD(1, 512, 384, 256, 256)
        collection.add(ifd0)
        collection.add(ifd1)
        
        retrieved = collection.get_level(0)
        assert retrieved == ifd0
        
    def test_ifd_collection_sorting(self):
        """Test IFD collection maintains order by level"""
        collection = IFDCollection()
        ifd2 = IFD(2, 256, 192, 256, 256)
        ifd0 = IFD(0, 1024, 768, 256, 256)
        ifd1 = IFD(1, 512, 384, 256, 256)
        
        collection.add(ifd2)
        collection.add(ifd0)
        collection.add(ifd1)
        
        levels = [ifd.level for ifd in collection.ifds]
        assert levels == sorted(levels)