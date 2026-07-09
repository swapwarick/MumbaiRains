import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "project" in response.json()
    assert response.json()["phase"] == "Phase 2 - Hydrological Simulation Engine"

def test_get_terrain():
    response = client.get("/api/terrain")
    assert response.status_code == 200
    data = response.json()
    assert "elevation" in data
    assert "slope" in data
    assert "aspect" in data
    assert "flow_direction" in data
    assert "flow_accumulation" in data
    assert "width" in data
    assert "height" in data
    assert data["width"] == 200
    assert data["height"] == 200

def test_get_roads():
    response = client.get("/api/roads")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0
    assert data["features"][0]["geometry"]["type"] == "LineString"

def test_get_buildings():
    response = client.get("/api/buildings")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0
    assert data["features"][0]["geometry"]["type"] == "Polygon"

def test_get_waterways():
    response = client.get("/api/waterways")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0
    assert data["features"][0]["geometry"]["type"] == "LineString"

def test_simulation_status():
    response = client.get("/api/simulation/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

