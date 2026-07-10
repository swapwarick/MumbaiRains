"""
simulation/forcing/manifest.py
------------------------------
SimulationManifest system to capture reproducibility details.
"""

import os
import platform
import subprocess
import sys
import uuid
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from typing import Dict, Any, Optional
import numpy as np


@dataclass
class SimulationManifest:
    simulation_uuid: str
    git_branch: str
    git_commit: str
    python_version: str
    numpy_version: str
    rasterio_version: str
    operating_system: str
    configuration_uuid: str
    dataset_uuids: Dict[str, str]
    algorithm_versions: Dict[str, str]
    random_seed: Optional[int]
    timestamp: str
    dem_checksum: str
    osm_checksum: str
    simulation_version: str

    @classmethod
    def create(
        cls,
        configuration_uuid: Optional[str] = None,
        dataset_uuids: Optional[Dict[str, str]] = None,
        algorithm_versions: Optional[Dict[str, str]] = None,
        random_seed: Optional[int] = None,
        simulation_version: str = "1.0.0"
    ) -> "SimulationManifest":
        """
        Creates a new, fully populated SimulationManifest.
        """
        sim_uuid = str(uuid.uuid4())
        cfg_uuid = configuration_uuid or str(uuid.uuid4())
        
        # Safe Git resolution
        git_branch = "unknown"
        git_commit = "unknown"
        try:
            # We check branch and commit by executing git commands
            git_branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            git_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
        except Exception:
            pass
            
        python_ver = sys.version
        numpy_ver = np.__version__
        
        rasterio_ver = "not_installed"
        try:
            import rasterio
            rasterio_ver = getattr(rasterio, "__version__", "mocked_or_unknown")
        except ImportError:
            pass
            
        os_ver = f"{platform.system()} {platform.release()}"
        
        # DEM / OSM checksums on disk
        dem_path = "data/dem/mumbai_dem.tif"
        osm_path = "data/osm/mumbai_osm.gpkg"
        
        dem_checksum = cls._compute_file_checksum(dem_path)
        osm_checksum = cls._compute_file_checksum(osm_path)
        
        ds_uuids = dataset_uuids or {
            "dem": dem_checksum[:16] if dem_checksum != "missing" else "missing",
            "osm": osm_checksum[:16] if osm_checksum != "missing" else "missing"
        }
        
        alg_versions = algorithm_versions or {
            "TerrainEngine": "2.0.0",
            "SurfaceRoutingEngine": "3.0.0",
            "ForcingEngine": "4.0.0"
        }
        
        return cls(
            simulation_uuid=sim_uuid,
            git_branch=git_branch,
            git_commit=git_commit,
            python_version=python_ver,
            numpy_version=numpy_ver,
            rasterio_version=rasterio_ver,
            operating_system=os_ver,
            configuration_uuid=cfg_uuid,
            dataset_uuids=ds_uuids,
            algorithm_versions=alg_versions,
            random_seed=random_seed,
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            dem_checksum=dem_checksum,
            osm_checksum=osm_checksum,
            simulation_version=simulation_version
        )

    @staticmethod
    def _compute_file_checksum(file_path: str) -> str:
        """Compute SHA-256 of file, return 'missing' if file doesn't exist."""
        if not os.path.exists(file_path):
            return "missing"
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return "error_reading"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save_to_file(self, file_path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(self.to_dict(), f, indent=4)
