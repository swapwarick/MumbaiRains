"""
tests/test_gis.py
------------------
Automated pytest suite for the Sprint 1 GIS Foundation module.
Verifies LayerMetadata, LayerManager, RasterLayer window/tile reads,
VectorLayer validations, CRS transformations, dataset immutability,
provenance contexts, validation reports, explicit geometry repairs,
and missing spatial dependency exceptions.
"""

from datetime import datetime
import sys
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

# Inject Mock modules into sys.modules before imports to fake dependencies
mock_rasterio = MagicMock()
mock_gpd = MagicMock()
mock_shapely_ops = MagicMock()

sys.modules["rasterio"] = mock_rasterio
sys.modules["rasterio.features"] = mock_rasterio.features
sys.modules["rasterio.windows"] = mock_rasterio.windows
sys.modules["geopandas"] = mock_gpd
sys.modules["shapely.ops"] = mock_shapely_ops

# Configure default mock methods
mock_rasterize = MagicMock()
mock_from_bounds = MagicMock()
mock_rasterio.features.rasterize = mock_rasterize
mock_rasterio.windows.from_bounds = mock_from_bounds

# Now import the simulation.gis modules
import simulation.gis.layers
import simulation.gis.manager
import simulation.gis.mask_factory
import simulation.gis.geometry_repair

# Force dependency flags to True
simulation.gis.layers._RASTERIO = True
simulation.gis.layers._SHAPELY = True
simulation.gis.manager._RASTERIO = True
simulation.gis.manager._GEOPANDAS = True
simulation.gis.mask_factory._RASTERIO = True
simulation.gis.mask_factory._SHAPELY = True

# Attach mock references
simulation.gis.layers.rasterio = mock_rasterio
simulation.gis.manager.rasterio = mock_rasterio
simulation.gis.manager.gpd = mock_gpd
simulation.gis.mask_factory.rasterio = mock_rasterio
simulation.gis.mask_factory.rasterize = mock_rasterize

from simulation.gis.layers import RasterLayer, VectorLayer, LayerMetadata
from simulation.gis.manager import LayerManager, GISManager
from simulation.gis.catalog import DatasetCatalog, DatasetMetadata
from simulation.gis.crs import CRSManager
from simulation.gis.geometry_repair import repair_geometry, GeometryRepairReport
from simulation.gis.mask_factory import MaskFactory
from simulation.gis.provenance import ProvenanceContext, AuditRecord
from simulation.gis.immutable import ImmutableDataset
from simulation.gis.validation import ValidationReport
from backend.exceptions import GISException, MissingSpatialDependencyError


class TestGISLayers:
    def test_raster_layer_stats(self):
        # 3x3 array values
        data = np.array([[10.0, 20.0, 30.0], [40.0, 50.0, 60.0], [70.0, 80.0, 90.0]], dtype=np.float32)
        layer = RasterLayer(
            name="test_raster",
            crs="EPSG:4326",
            bounds=(72.8, 19.0, 72.9, 19.1),
            shape=(3, 3),
            transform=[0.01, 0.0, 72.8, 0.0, -0.01, 19.1],
            resolution=(0.01, -0.01),
            nodata=-9999.0
        )
        stats = layer.statistics(grid_data=data)
        assert stats["min"] == 10.0
        assert stats["max"] == 90.0
        assert stats["mean"] == 50.0

    def test_raster_layer_invalid_resolution(self):
        layer = RasterLayer(
            name="bad_res",
            crs="EPSG:4326",
            bounds=(72.8, 19.0, 72.9, 19.1),
            shape=(3, 3),
            transform=[0.01, 0.0, 72.8, 0.0, -0.01, 19.1],
            resolution=(-1.0, 0.0),
            nodata=-9999.0
        )
        report = layer.validate()
        assert report.result is False
        assert len(report.errors) > 0

    def test_vector_layer_geometry_validation(self):
        features = [
            # Valid point
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [72.85, 19.15]}
            },
            # Empty geometry payload
            {
                "type": "Feature",
                "geometry": None
            },
            # Empty geometry
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": []}
            },
            # Invalid polygon (self-intersecting bowtie)
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 2], [2, 0], [2, 2], [0, 0]]]
                }
            },
            # Duplicate valid point
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [72.85, 19.15]}
            },
            # Parsing error geometry type
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": "invalid"}
            }
        ]
        
        layer = VectorLayer(
            name="test_vector",
            crs="EPSG:4326",
            bounds=(0, 0, 10, 10),
            features=features
        )
        report = layer.validate()
        assert report.result is False
        # Should have empty payload, empty coordinates, invalid bowtie, parsing exception
        assert len(report.errors) == 4
        # Duplicate geometry should produce a warning
        assert len(report.warnings) == 1

    def test_raster_layer_nodata_only_statistics(self):
        layer = RasterLayer(
            name="nodata_only",
            crs="EPSG:4326",
            bounds=(0, 0, 5, 5),
            shape=(3, 3),
            transform=[1, 0, 0, 0, -1, 5],
            resolution=(1, 1),
            nodata=-9999.0
        )
        data = np.full((3, 3), -9999.0, dtype=np.float32)
        stats = layer.statistics(grid_data=data)
        assert stats["min"] == 0.0
        assert stats["mean"] == 0.0

    def test_raster_layer_band_reading(self):
        mock_src = MagicMock()
        mock_src.count = 2
        mock_src.read.return_value = np.ones((5, 5), dtype=np.float32) * 42.0
        mock_src.overviews.return_value = [2, 4]
        mock_src.nodata = -99.0
        mock_rasterio.open.return_value.__enter__.return_value = mock_src
        
        with patch("os.path.exists", return_value=True):
            layer = RasterLayer("mock_r", "EPSG:4326", (0, 0, 5, 5), (5, 5), [1, 0, 0, 0, -1, 5], (1, 1), -99.0, "dummy.tif")
            
            assert layer.band_count == 2
            assert np.all(layer.read_band(1) == 42.0)
            assert np.all(layer.read_bands([1, 2]) == 42.0)
            assert np.all(layer.nodata_mask() == False)
            assert layer.overview_levels(1) == [2, 4]
            
            stats = layer.statistics(1)
            assert stats["min"] == 42.0
            
            hist, bin_edges = layer.histogram(1, bins=10)
            assert hist.sum() == 25
            
            mock_src.read.return_value = np.ones((2, 2), dtype=np.float32) * 5.0
            win_data = layer.read_window((1, 1, 3, 3))
            assert win_data.shape == (2, 2)
            
            tile_data = layer.read_tile(0, 0, 2)
            assert tile_data.shape == (256, 256)

    def test_raster_layer_exceptions(self):
        layer = RasterLayer("mock_r", "EPSG:4326", (0, 0, 5, 5), (5, 5), [1, 0, 0, 0, -1, 5], (1, 1), -99.0, None)
        
        with pytest.raises(ValueError):
            layer.read_window((0, 0, 1, 1))

        layer.file_path = "dummy.tif"
        with patch("simulation.gis.layers._RASTERIO", False), patch("os.path.exists", return_value=True):
            with pytest.raises(ImportError):
                layer.read_window((0, 0, 1, 1))
            with pytest.raises(ImportError):
                layer.read_band(1)
            with pytest.raises(ImportError):
                layer.read_bands([1])
            assert layer.overview_levels(1) == []
            assert layer.band_count == 1

        v_layer = VectorLayer("v", "EPSG:4326", (0,0,5,5), [])
        with patch("simulation.gis.layers._SHAPELY", False):
            v_layer.build_spatial_index()
            assert v_layer.spatial_index is None
            report = v_layer.validate()
            assert report.result is False
            assert "Shapely is required" in report.errors[0]


class TestGISManagers:
    def test_layer_manager_lazy_load_cache(self):
        mock_src = MagicMock()
        mock_src.transform = MagicMock(a=1, b=0, c=0, d=0, e=-1, f=5)
        mock_src.res = (1, 1)
        mock_src.bounds = MagicMock(left=0, bottom=0, right=5, top=5)
        mock_src.height = 5
        mock_src.width = 5
        mock_src.crs = "EPSG:4326"
        mock_src.nodata = -99.0
        mock_rasterio.open.return_value.__enter__.return_value = mock_src

        manager = LayerManager()
        
        with patch("os.path.exists", return_value=True), patch("os.path.getsize", return_value=500):
            manager.register_layer(
                name="dem_layer",
                layer_type="raster",
                file_path="dummy.tif"
            )
            assert "dem_layer" in manager.registry
            assert "dem_layer" not in manager.cache
            
            layer = manager.get_layer("dem_layer")
            assert isinstance(layer, RasterLayer)
            assert "dem_layer" in manager.cache
            
            meta = manager.get_metadata("dem_layer")
            assert isinstance(meta, dict)

    def test_gis_manager_crs_validation(self):
        layer_manager = LayerManager()
        r_layer = RasterLayer("dem", "EPSG:4326", (0, 0, 5, 5), (5, 5), [1, 0, 0, 0, -1, 5], (1, 1), -99.0, "dummy.tif")
        layer_manager.cache["dem"] = r_layer
        
        gis_manager = GISManager(layer_manager)
        assert gis_manager.validate_crs_match("dem", "EPSG:4326") is True

    def test_layer_unload(self):
        manager = LayerManager()
        r_layer = RasterLayer("dem", "EPSG:4326", (0, 0, 5, 5), (5, 5), [1, 0, 0, 0, -1, 5], (1, 1), -99.0, "dummy.tif")
        manager.cache["dem"] = r_layer
        
        manager.get_layer("dem")
        assert "dem" in manager.cache
        
        manager.unload_layer("dem")
        assert "dem" not in manager.cache

    def test_layer_manager_load_vector(self):
        mock_gdf = MagicMock()
        mock_gdf.crs = "EPSG:4326"
        mock_gdf.total_bounds = [0.0, 0.0, 5.0, 5.0]
        mock_gdf.to_crs.return_value = mock_gdf
        mock_gdf.to_json.return_value = '{"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}}]}'
        mock_gpd.read_file.return_value = mock_gdf
        
        manager = LayerManager()
        with patch("os.path.exists", return_value=True), patch("os.path.getsize", return_value=500):
            manager.register_layer("v_layer", "vector", "dummy.gpkg")
            layer = manager.get_layer("v_layer")
            assert isinstance(layer, VectorLayer)

        gis = GISManager(manager)
        gis.reproject_vector_layer("v_layer", "EPSG:32643")
        assert layer.crs == "EPSG:32643"
        
        manager.cache["r_layer"] = RasterLayer("r_layer", "EPSG:4326", (0,0,5,5), (5,5), [1,0,0,0,-1,5], (1,1))
        with pytest.raises(GISException):
            gis.reproject_vector_layer("r_layer", "EPSG:32643")

    def test_layer_manager_load_vector_failure(self):
        mock_gpd.read_file.side_effect = Exception("mock read error")
        manager = LayerManager()
        with patch("os.path.exists", return_value=True), patch("os.path.getsize", return_value=500):
            manager.register_layer("v_layer_fail", "vector", "dummy.gpkg")
            layer = manager.get_layer("v_layer_fail")
            assert isinstance(layer, VectorLayer)
            assert len(layer.features) == 1
            assert layer.features[0]["geometry"] is None
        mock_gpd.read_file.side_effect = None

    def test_gis_manager_rasterize(self):
        mock_rasterize.return_value = np.ones((5, 5), dtype=np.uint8)
        
        r_layer = RasterLayer("r_lay", "EPSG:4326", (0, 0, 5, 5), (5, 5), [1, 0, 0, 0, -1, 5], (1, 1), -99.0, "dummy.tif")
        v_layer = VectorLayer("v_lay", "EPSG:4326", (0, 0, 5, 5), [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 1]}}])
        
        manager = LayerManager()
        manager.cache["r_lay"] = r_layer
        manager.cache["v_lay"] = v_layer
        
        gis = GISManager(manager)
        mask = gis.rasterize_layer("v_lay", "r_lay")
        assert mask.shape == (5, 5)
        assert np.all(mask == True)
        
        with pytest.raises(GISException):
            gis.rasterize_layer("r_lay", "r_lay")
            
        with pytest.raises(GISException):
            gis.rasterize_layer("v_lay", "v_lay")

        manager.registry["roads"] = {"type": "vector", "path": "", "metadata": {}}
        manager.registry["buildings"] = {"type": "vector", "path": "", "metadata": {}}
        manager.registry["waterways"] = {"type": "vector", "path": "", "metadata": {}}
        manager.cache["roads"] = v_layer
        manager.cache["buildings"] = v_layer
        manager.cache["waterways"] = v_layer
        
        masks = gis.generate_masks("r_lay")
        assert "roads" in masks
        assert "buildings" in masks
        assert "waterways" in masks

    def test_layer_manager_unsupported_type(self):
        manager = LayerManager()
        manager.registry["bad"] = {"type": "unsupported", "path": "", "metadata": {}}
        with pytest.raises(GISException):
            manager.get_layer("bad")


class TestDatasetCatalog:
    def test_catalog_lifecycle(self, tmp_path):
        catalog = DatasetCatalog()
        meta = DatasetMetadata(
            id="mumbai_dem",
            name="Mumbai DEM",
            source="SRTM",
            version="1.0",
            license="Public Domain",
            download_date="2026-07-09",
            processing_date="2026-07-09",
            checksum="abcdef",
            crs="EPSG:4326",
            extent=(72.8, 18.8, 72.9, 19.2),
            format="GeoTIFF",
            file_path=str(tmp_path / "dem.tif")
        )
        
        catalog.register_dataset(meta)
        assert len(catalog.list_datasets()) == 1
        assert catalog.get_dataset("mumbai_dem") == meta
        
        errors = catalog.validate_dataset("mumbai_dem")
        assert len(errors) > 0
        
        with patch("os.path.exists", return_value=True):
            clean_errors = catalog.validate_dataset("mumbai_dem")
            assert len(clean_errors) == 0
        
        with pytest.raises(GISException):
            catalog.get_dataset("non_existent")

        with pytest.raises(GISException):
            catalog.remove_dataset("non_existent")

        catalog.remove_dataset("mumbai_dem")
        assert len(catalog.list_datasets()) == 0


class TestCRSManager:
    def test_crs_validation(self):
        assert CRSManager.validate_crs("EPSG:4326") is True
        assert CRSManager.validate_crs("INVALID_CRS_NAME") is False

    def test_crs_compare(self):
        assert CRSManager.compare_crs("EPSG:4326", "WGS 84") is True
        assert CRSManager.compare_crs("EPSG:4326", "EPSG:32643") is False

    def test_crs_suggest_utm(self):
        suggested = CRSManager.suggest_projected_crs(72.85, 19.0)
        assert suggested == "EPSG:32643"

    def test_transform_coordinates(self):
        tx, ty = CRSManager.transform_coordinates(72.85, 19.0, "EPSG:4326", "EPSG:32643")
        assert tx > 200000.0
        assert ty > 2000000.0
        
        with pytest.raises(Exception):
            CRSManager.transform_coordinates(0, 0, "INVALID", "EPSG:4326")

    def test_haversine_geodetic_distance(self):
        dist = CRSManager.calculate_distance((72.8, 19.0), (72.9, 19.0), "EPSG:4326")
        assert dist > 10000.0

        dist_proj = CRSManager.calculate_distance((0, 0), (3, 4), "EPSG:32643")
        assert dist_proj == 5.0

    def test_geodetic_area(self):
        poly = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]
        area = CRSManager.calculate_area(poly, "EPSG:4326")
        assert area > 1e10

        poly_proj = [(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)]
        area_proj = CRSManager.calculate_area(poly_proj, "EPSG:32643")
        assert area_proj == 100.0

        assert CRSManager.calculate_area([(0, 0), (0, 1)], "EPSG:32643") == 0.0


class TestGeometryRepairAndValidation:
    def test_explicit_repair_flow(self):
        # Feature with self-intersecting invalid polygon (bowtie)
        feature = {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0, 2], [2, 0], [2, 2], [0, 0]]]
            }
        }
        
        # 1. Validation is always performed, but repair is NEVER automatic
        repaired_no, report_no = repair_geometry(feature, "bowtie_01", repair_requested=False)
        assert report_no.repair_succeeded is False
        assert report_no.geometry_changed is False
        assert repaired_no == feature  # Immutability check - original returned

        # 2. Repair only happens when explicitly requested by the caller
        repaired_yes, report_yes = repair_geometry(feature, "bowtie_01", repair_requested=True)
        assert report_yes.repair_succeeded is True
        assert report_yes.geometry_changed is True
        assert report_yes.geometry_area_before == 0.0
        assert report_yes.geometry_area_after == 2.0
        assert repaired_yes != feature  # Repaired geometry returned
        assert feature["geometry"]["coordinates"] == [[[0, 0], [0, 2], [2, 0], [2, 2], [0, 0]]]  # Original untouched

        # Test empty geometry validation
        empty_feat = {"geometry": None}
        _, report_empty = repair_geometry(empty_feat, "empty_01")
        assert "Empty" in report_empty.original_validity_error

        # Test missing geometry key
        missing_feat = {"properties": {}}
        _, report_missing = repair_geometry(missing_feat, "missing_01")
        assert "Empty" in report_missing.original_validity_error

        # Test valid geometry (Point)
        valid_feat = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}}
        _, report_valid = repair_geometry(valid_feat, "valid_01")
        assert report_valid.repair_succeeded is True
        assert report_valid.geometry_changed is False
        assert "valid" in report_valid.original_validity_error.lower()

        # Test geometry repair exception handling
        with patch("simulation.gis.geometry_repair.make_valid", side_effect=Exception("mock error")):
            _, report_err = repair_geometry({"geometry": {"type": "Polygon", "coordinates": [[[0, 0], [0, 2], [2, 0], [2, 2], [0, 0]]]}}, "err_01", repair_requested=True)
            assert report_err.repair_succeeded is False

        # Test custom GeometryCollection unpacking
        mock_collection = MagicMock()
        mock_collection.is_empty = False
        mock_collection.is_valid = False
        mock_collection.geom_type = "Polygon"
        
        mock_repaired = MagicMock()
        mock_repaired.is_valid = True
        mock_repaired.geom_type = "GeometryCollection"
        
        sub_poly = MagicMock()
        sub_poly.geom_type = "Polygon"
        mock_repaired.geoms = [sub_poly]
        
        # Configure shapely.ops mock
        mock_shapely_ops.unary_union.return_value = mock_collection

        with patch("simulation.gis.geometry_repair.shapely_shape", return_value=mock_collection), \
             patch("simulation.gis.geometry_repair.make_valid", return_value=mock_repaired), \
             patch("simulation.gis.geometry_repair.mapping") as mock_map:
            
            repair_geometry({"geometry": {"type": "Polygon"}}, "coll_01", repair_requested=True)
            assert mock_map.called

        # Test non-shapely exception path
        with patch("simulation.gis.geometry_repair._SHAPELY", False):
            with pytest.raises(GISException) as exc_info:
                repair_geometry(feature, "no_shapely_01")
            assert "Shapely is required" in str(exc_info.value)


class TestDatasetImmutability:
    def test_immutable_dataset_lineage(self):
        raw_dem_layer = RasterLayer("raw_dem", "EPSG:4326", (0, 0, 5, 5), (5, 5), [1, 0, 0, 0, -1, 5], (1, 1))
        
        # Wrap raw layer
        raw_dataset = ImmutableDataset(raw_dem_layer)
        assert raw_dataset.parent is None
        assert raw_dataset.lineage_operation is None
        
        # Derive a clipped DEM
        clipped_dem_layer = RasterLayer("clipped_dem", "EPSG:4326", (1, 1, 4, 4), (3, 3), [1, 0, 1, 0, -1, 4], (1, 1))
        clipped_dataset = raw_dataset.derive(clipped_dem_layer, "Clipping")
        
        assert clipped_dataset.parent == raw_dataset
        assert clipped_dataset.lineage_operation == "Clipping"
        assert clipped_dataset in raw_dataset.children
        
        # Derive a filled DEM
        filled_dem_layer = RasterLayer("filled_dem", "EPSG:4326", (1, 1, 4, 4), (3, 3), [1, 0, 1, 0, -1, 4], (1, 1))
        filled_dataset = clipped_dataset.derive(filled_dem_layer, "Fill NoData")
        
        assert filled_dataset.parent == clipped_dataset
        assert filled_dataset.lineage_operation == "Fill NoData"
        
        # Verify lineage tracking path
        path = filled_dataset.get_lineage_path()
        assert len(path) == 3
        assert "raw_dem (Source)" in path[0]
        assert "clipped_dem (Clipping)" in path[1]
        assert "filled_dem (Fill NoData)" in path[2]


class TestProvenanceContexts:
    def test_provenance_context_isolation(self):
        # Context 1
        ctx1 = ProvenanceContext(simulation_id="sim_run_01", configuration={"intensity": 50})
        ctx1.record_operation("Reproject", ["dem"], ["dem_proj"], 12.0, "1.0", {}, "Success")
        ctx1.add_warning("Warning in Sim 1")
        
        # Context 2
        ctx2 = ProvenanceContext(simulation_id="sim_run_02", configuration={"intensity": 100})
        ctx2.record_operation("Rasterize", ["roads"], ["roads_mask"], 24.0, "1.0", {}, "Success")
        ctx2.add_error("Error in Sim 2")
        
        # Verify no shared global state (complete isolation)
        assert len(ctx1.processing_history) == 1
        assert ctx1.processing_history[0].operation == "Reproject"
        assert "Warning in Sim 1" in ctx1.warnings
        assert not ctx1.errors
        
        assert len(ctx2.processing_history) == 1
        assert ctx2.processing_history[0].operation == "Rasterize"
        assert "Error in Sim 2" in ctx2.errors
        assert not ctx2.warnings
        
        json_log1 = ctx1.export_json()
        assert "sim_run_01" in json_log1
        assert "sim_run_02" not in json_log1


class TestMaskFactoryAndMissingDependencies:
    def test_mask_factory_with_missing_dependency(self):
        factory = MaskFactory()
        template = RasterLayer("dem", "EPSG:4326", (0, 0, 5, 5), (5, 5), [1, 0, 0, 0, -1, 5], (1, 1))
        roads = VectorLayer("roads", "EPSG:4326", (0, 0, 5, 5), [])
        
        # When RASTERIO is False, it must raise MissingSpatialDependencyError
        with patch("simulation.gis.mask_factory._RASTERIO", False):
            with pytest.raises(MissingSpatialDependencyError) as exc_info:
                factory.generate_road_mask(roads, template)
            assert "Required spatial libraries" in str(exc_info.value)
            assert "pip install" in str(exc_info.value)

    def test_gis_manager_with_missing_dependency(self):
        manager = LayerManager()
        r_layer = RasterLayer("r_lay", "EPSG:4326", (0, 0, 5, 5), (5, 5), [1, 0, 0, 0, -1, 5], (1, 1))
        v_layer = VectorLayer("v_lay", "EPSG:4326", (0, 0, 5, 5), [])
        manager.cache["r_lay"] = r_layer
        manager.cache["v_lay"] = v_layer
        
        gis = GISManager(manager)
        
        # Reprojection fails when GEOPANDAS is False
        with patch("simulation.gis.manager._GEOPANDAS", False):
            with pytest.raises(MissingSpatialDependencyError):
                gis.reproject_vector_layer("v_lay", "EPSG:32643")
                
            # Rasterization fails when GEOPANDAS is False
            with pytest.raises(MissingSpatialDependencyError):
                gis.rasterize_layer("v_lay", "r_lay")

    def test_mask_generation_all_types(self):
        factory = MaskFactory()
        template = RasterLayer("dem", "EPSG:4326", (0, 0, 5, 5), (5, 5), [1, 0, 0, 0, -1, 5], (1, 1))
        roads = VectorLayer("roads", "EPSG:4326", (0, 0, 5, 5), [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 1]}}])
        
        mock_rasterize.return_value = np.ones((5, 5), dtype=np.uint8)
        
        w_mask = factory.generate_waterway_mask(roads, template)
        veg_mask = factory.generate_vegetation_mask(roads, template)
        assert w_mask.shape == (5, 5)
        assert veg_mask.shape == (5, 5)
