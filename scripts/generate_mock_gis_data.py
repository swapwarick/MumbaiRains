import os
import sqlite3
import numpy as np

# Try to import GIS packages
try:
    # pyrefly: ignore [missing-import]
    import rasterio
    # pyrefly: ignore [missing-import]
    from rasterio.transform import from_origin
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

try:
    import geopandas as gpd
    from shapely.geometry import Point, LineString, Polygon
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

def generate_dem(output_path):
    print("Generating mock DEM for Greater Mumbai...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if not RASTERIO_AVAILABLE:
        print("rasterio not available. Creating an empty stub file for DEM. In-memory fallback will be used.")
        with open(output_path, 'wb') as f:
            f.write(b"MOCK_DEM_TIFF_DATA")
        return

    # Generate using rasterio
    # Greater Mumbai extent:
    #   Longitude: 72.80 to 72.99 (west to east)
    #   Latitude:  18.89 to 19.27 (south to north)
    width, height = 200, 200
    lon_start = 72.80   # west boundary
    lat_start = 19.27   # north boundary (rasterio uses top-left origin)
    lon_end   = 72.99
    lat_end   = 18.89

    lon_res = (lon_end - lon_start) / width   # ~0.00095° per cell (~105m)
    lat_res = (lat_start - lat_end) / height  # ~0.00190° per cell (~210m)

    # Create normalized coordinate grids (0..1 across the domain)
    # x: west→east, y: south→north
    x = np.linspace(0, 1, width)   # 0=west coast, 1=eastern suburbs
    y = np.linspace(0, 1, height)  # 0=south (Bandra), 1=north (Borivali)
    X, Y = np.meshgrid(x, y[::-1])  # flip y so row 0 = north (top of raster)

    # ---- Realistic Mumbai elevation model ----
    # Mumbai is a narrow peninsula: mostly flat 0-10m near coast, rising inland
    # Western coast (Bandra, Juhu, Versova) → sea level
    # Eastern side (Kurla, Ghatkopar, Mulund) → 10-30m
    # North-east hills (SGNP, Borivali) → 40-100m

    # Base: rises west-to-east with a coastal flat strip
    elev_base = X * 30.0 + 2.0           # 2m at west coast → 32m at east

    # Northern hills (SGNP) — concentrated in top-right
    hill_x, hill_y = 0.75, 0.85          # centre of hill mass
    hills = 65.0 * np.exp(-((X - hill_x)**2 / 0.04 + (Y - hill_y)**2 / 0.06))

    # Aarey/Goregaon hills (mid-east)
    aarey = 30.0 * np.exp(-((X - 0.65)**2 / 0.025 + (Y - 0.55)**2 / 0.03))

    # Powai lake depression (fills with water in low spots)
    powai = -8.0 * np.exp(-((X - 0.70)**2 / 0.008 + (Y - 0.42)**2 / 0.008))

    # Mithi River valley — diagonal trough from NE to SW
    river_dist = (X - 0.3) - (Y - 0.5) * 0.8
    river_valley = -6.0 * np.exp(-(river_dist**2) / 0.006)

    # Dharavi / low-lying reclaimed land (south central — flat, near sea level)
    dharavi = -4.0 * np.exp(-((X - 0.30)**2 / 0.015 + (Y - 0.15)**2 / 0.015))

    # Combine all components
    elevation = elev_base + hills + aarey + powai + river_valley + dharavi

    # Add small-scale realistic noise
    np.random.seed(42)
    noise = np.random.normal(0, 0.5, (height, width))
    elevation += noise

    elevation = np.clip(elevation, 0.5, 110.0).astype(np.float32)

    transform = from_origin(lon_start, lat_start, lon_res, lat_res)
    
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype='float32',
        crs='EPSG:4326',
        transform=transform,
        nodata=-9999
    ) as dst:
        dst.write(elevation, 1)
        
    print(f"DEM created: {width}×{height} cells covering lon {lon_start}–{lon_end}, lat {lat_end}–{lat_start}")

def generate_osm_gpkg(output_path):
    print("Generating mock OSM GeoPackage...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Realistic roads, waterways and buildings spread across greater Mumbai
    # (lon range: 72.80-72.99, lat range: 18.89-19.27)
    roads = [
        {"name": "Western Express Highway",      "geojson": '{"type":"LineString","coordinates":[[72.838,18.920],[72.840,18.955],[72.842,18.985],[72.843,19.020],[72.845,19.055],[72.848,19.090],[72.851,19.130],[72.855,19.170],[72.858,19.210],[72.860,19.250]]}'},
        {"name": "Eastern Express Highway",      "geojson": '{"type":"LineString","coordinates":[[72.900,18.925],[72.905,18.960],[72.912,18.995],[72.918,19.030],[72.920,19.065],[72.922,19.100],[72.925,19.135],[72.930,19.170]]}'},
        {"name": "Sion-Panvel Highway",          "geojson": '{"type":"LineString","coordinates":[[72.863,18.895],[72.880,18.910],[72.900,18.925]]}'},
        {"name": "Jogeshwari-Vikhroli Link Road","geojson": '{"type":"LineString","coordinates":[[72.845,19.125],[72.862,19.120],[72.880,19.115],[72.898,19.110]]}'},
        {"name": "Andheri-Kurla Road",           "geojson": '{"type":"LineString","coordinates":[[72.848,19.110],[72.860,19.107],[72.875,19.103],[72.888,19.100]]}'},
        {"name": "LBS Marg",                     "geojson": '{"type":"LineString","coordinates":[[72.875,18.900],[72.877,18.940],[72.879,18.980],[72.882,19.020],[72.885,19.060]]}'},
        {"name": "Bandra-Kurla Complex Road",    "geojson": '{"type":"LineString","coordinates":[[72.860,19.056],[72.870,19.055],[72.880,19.052],[72.890,19.048]]}'},
        {"name": "Mahim Causeway",               "geojson": '{"type":"LineString","coordinates":[[72.838,19.033],[72.845,19.038],[72.852,19.040]]}'},
        {"name": "Gokhale Bridge",               "geojson": '{"type":"LineString","coordinates":[[72.833,19.068],[72.840,19.070],[72.848,19.072]]}'},
        {"name": "Malad-Poisar Link",            "geojson": '{"type":"LineString","coordinates":[[72.840,19.188],[72.852,19.185],[72.862,19.183],[72.875,19.180]]}'},
    ]
    
    waterways = [
        {"name": "Mithi River",  "geojson": '{"type":"LineString","coordinates":[[72.895,19.120],[72.880,19.100],[72.868,19.082],[72.857,19.060],[72.848,19.042],[72.838,19.020],[72.835,19.000]]}'},
        {"name": "Oshiwara River","geojson": '{"type":"LineString","coordinates":[[72.832,19.165],[72.835,19.148],[72.838,19.130],[72.840,19.110]]}'},
        {"name": "Dahisar River", "geojson": '{"type":"LineString","coordinates":[[72.840,19.250],[72.838,19.235],[72.835,19.220],[72.833,19.200]]}'},
        {"name": "Ulhas Creek",   "geojson": '{"type":"LineString","coordinates":[[72.950,19.260],[72.940,19.230],[72.928,19.200],[72.918,19.170]]}'},
    ]
    
    buildings = [
        {"type": "residential",  "geojson": '{"type":"Polygon","coordinates":[[[72.838,18.930],[72.842,18.930],[72.842,18.935],[72.838,18.935],[72.838,18.930]]]}'},
        {"type": "commercial",   "geojson": '{"type":"Polygon","coordinates":[[[72.860,19.056],[72.866,19.056],[72.866,19.062],[72.860,19.062],[72.860,19.056]]]}'},
        {"type": "industrial",   "geojson": '{"type":"Polygon","coordinates":[[[72.900,19.070],[72.908,19.070],[72.908,19.078],[72.900,19.078],[72.900,19.070]]]}'},
        {"type": "residential",  "geojson": '{"type":"Polygon","coordinates":[[[72.850,19.150],[72.855,19.150],[72.855,19.155],[72.850,19.155],[72.850,19.150]]]}'},
        {"type": "commercial",   "geojson": '{"type":"Polygon","coordinates":[[[72.878,19.105],[72.884,19.105],[72.884,19.112],[72.878,19.112],[72.878,19.105]]]}'},
        {"type": "residential",  "geojson": '{"type":"Polygon","coordinates":[[[72.832,19.200],[72.836,19.200],[72.836,19.204],[72.832,19.204],[72.832,19.200]]]}'},
        {"type": "commercial",   "geojson": '{"type":"Polygon","coordinates":[[[72.918,18.960],[72.924,18.960],[72.924,18.967],[72.918,18.967],[72.918,18.960]]]}'},
        {"type": "industrial",   "geojson": '{"type":"Polygon","coordinates":[[[72.935,19.050],[72.942,19.050],[72.942,19.058],[72.935,19.058],[72.935,19.050]]]}'},
    ]
    
    if not GEOPANDAS_AVAILABLE:
        print("geopandas not available. Creating a standard SQLite database for GPKG mock.")
        # Create as a standard SQLite database with geojson data columns
        conn = sqlite3.connect(output_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("CREATE TABLE IF NOT EXISTS roads (id INTEGER PRIMARY KEY, name TEXT, geojson TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS waterways (id INTEGER PRIMARY KEY, name TEXT, geojson TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS buildings (id INTEGER PRIMARY KEY, type TEXT, geojson TEXT)")
        
        # Clear existing data
        cursor.execute("DELETE FROM roads")
        cursor.execute("DELETE FROM waterways")
        cursor.execute("DELETE FROM buildings")
        
        # Insert values
        for idx, item in enumerate(roads):
            cursor.execute("INSERT INTO roads (id, name, geojson) VALUES (?, ?, ?)", (idx+1, item["name"], item["geojson"]))
        for idx, item in enumerate(waterways):
            cursor.execute("INSERT INTO waterways (id, name, geojson) VALUES (?, ?, ?)", (idx+1, item["name"], item["geojson"]))
        for idx, item in enumerate(buildings):
            cursor.execute("INSERT INTO buildings (id, type, geojson) VALUES (?, ?, ?)", (idx+1, item["type"], item["geojson"]))
            
        conn.commit()
        conn.close()
        print(f"Mock SQLite GPKG created successfully at {output_path}")
        return

    # If geopandas is available, generate official GPKG layers
    import json
    from shapely.geometry import shape
    
    roads_data = [{"name": item["name"], "geometry": shape(json.loads(item["geojson"]))} for item in roads]
    roads_gdf = gpd.GeoDataFrame(roads_data, crs="EPSG:4326")
    
    waterways_data = [{"name": item["name"], "geometry": shape(json.loads(item["geojson"]))} for item in waterways]
    waterways_gdf = gpd.GeoDataFrame(waterways_data, crs="EPSG:4326")
    
    buildings_data = [{"type": item["type"], "geometry": shape(json.loads(item["geojson"]))} for item in buildings]
    buildings_gdf = gpd.GeoDataFrame(buildings_data, crs="EPSG:4326")
    
    # Write to GPKG
    roads_gdf.to_file(output_path, layer="roads", driver="GPKG")
    waterways_gdf.to_file(output_path, layer="waterways", driver="GPKG")
    buildings_gdf.to_file(output_path, layer="buildings", driver="GPKG")
    print(f"Official OSM GeoPackage created successfully at {output_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dem_file = os.path.join(base_dir, "data", "dem", "mumbai_dem.tif")
    gpkg_file = os.path.join(base_dir, "data", "osm", "mumbai_osm.gpkg")
    
    generate_dem(dem_file)
    generate_osm_gpkg(gpkg_file)
