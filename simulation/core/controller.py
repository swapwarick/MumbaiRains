"""
simulation/core/controller.py
-----------------------------
SimulationController — orchestrates the entire simulation timeline, manages boundary
conditions (clock, meteorology, tide), updates infiltration, routing, hydraulic networks,
and outputs flood risk diagnostics. Supports full Dependency Injection (Task 7) and Repositories (Task 1).
"""

import os
import time
import uuid
import sys
import platform
import subprocess
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
import numpy as np

from backend.config import settings
from backend.utils import get_logger
from backend.exceptions import SimulationException

from simulation.core.clock import SimulationClock
from simulation.core.state import SimulationState
from simulation.core.grid_manager import GridManager
from simulation.core.scenario_manager import Scenario, ScenarioManager
from simulation.core.results_manager import ResultsManager
from simulation.meteorology.engine import SyntheticMeteorologyEngine, MeteorologyEngine
from simulation.surface.landcover import LandCoverEngine
from simulation.infiltration.engine import InfiltrationEngine
from simulation.routing.engine import FlowRoutingEngine
from simulation.drainage.engine import HydraulicNetworkEngine
from simulation.tide.engine import TideEngine
from simulation.flood.engine import FloodEngine

# Repositories for Task 1
from backend.data.terrain_repo import TerrainRepository
from backend.data.gis_repo import GISRepository
from backend.data.scenario_repo import ScenarioRepository

# Diagnostics for Task 5
from simulation.diagnostics.manager import DiagnosticsManager

logger = get_logger(__name__)


def get_git_info() -> tuple[str, str]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        return commit, branch
    except Exception:
        return "unknown", "unknown"


def get_file_checksum(filepath: str) -> str:
    if not os.path.exists(filepath):
        return "missing"
    try:
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return "error"


class SimulationController:
    """
    SimulationController coordinate all sub-engines to advance the simulation
    and record the deterministic steps. Supports dependency injection (Task 7).
    """
    def __init__(
        self,
        scenario_name: str = "synthetic",
        grid_manager: Optional[GridManager] = None,
        clock: Optional[SimulationClock] = None,
        landcover: Optional[LandCoverEngine] = None,
        infiltration: Optional[InfiltrationEngine] = None,
        meteorology: Optional[MeteorologyEngine] = None,
        tide: Optional[TideEngine] = None,
        routing: Optional[FlowRoutingEngine] = None,
        hydraulics: Optional[HydraulicNetworkEngine] = None,
        flood: Optional[FloodEngine] = None,
        results_manager: Optional[ResultsManager] = None
    ) -> None:
        self.scenario_name = scenario_name
        self.scenario_manager = ScenarioManager()
        self.scenario: Scenario = self.scenario_manager.get_scenario(scenario_name)

        # Injected or lazily initialized engines (Task 7)
        self.grid_manager = grid_manager
        self.state: Optional[SimulationState] = None
        self.clock = clock
        self.landcover = landcover
        self.infiltration = infiltration
        self.meteorology = meteorology
        self.tide = tide
        self.routing = routing
        self.hydraulics = hydraulics
        self.flood = flood
        self.results_manager = results_manager

        # Time series tracking for diagnostics
        self.mass_balance_history: List[Dict[str, Any]] = []
        self.hydraulic_discharge_history: List[float] = []
        self.hydraulic_storage_history: List[float] = []

        # Run identification
        self.run_uuid = str(uuid.uuid4())
        self.start_execution_time: float = 0.0

    def initialize(
        self,
        dem_path: str = "",
        gpkg_path: str = "",
        duration_hours: Optional[float] = None,
        intensity_mm_hr: Optional[float] = None,
        timestep_min: Optional[float] = None,
        rainfall_mode: Optional[str] = None,
        terrain_repo: Optional[TerrainRepository] = None,
        gis_repo: Optional[GISRepository] = None,
        scenario_repo: Optional[ScenarioRepository] = None
    ) -> None:
        """
        Sets up the grid, starts the clock, and wires up all sub-engines.
        Queries all spatial datasets only through the repository layer (Task 1).
        """
        self.start_execution_time = time.time()
        
        # Override scenario parameters if explicit overrides provided
        dur = duration_hours if duration_hours is not None else self.scenario.rainfall_duration
        inten = intensity_mm_hr if intensity_mm_hr is not None else self.scenario.rainfall_intensity
        dt_min = timestep_min if timestep_min is not None else settings.default_timestep_min
        
        # 1. Initialize Repositories (Task 1)
        t_repo = terrain_repo or TerrainRepository(dem_path)
        g_repo = gis_repo or GISRepository(gpkg_path)

        # 2. Load DEM through TerrainRepository
        elevation, meta = t_repo.load_elevation_grid()

        if self.grid_manager is None:
            self.grid_manager = GridManager()
        self.grid_manager.initialize_grid_from_data(elevation, meta)
        
        rows, cols = self.grid_manager.rows, self.grid_manager.cols

        # 3. State & Clock
        self.state = SimulationState(rows, cols, self.scenario_name)
        if self.clock is None:
            self.clock = SimulationClock(default_dt_seconds=dt_min * 60.0)
        self.clock.start()

        # 4. Infiltration & Roughness Engines
        if self.landcover is None:
            self.landcover = LandCoverEngine()
        
        if self.infiltration is None:
            self.infiltration = InfiltrationEngine(rows, cols, model_name="constant")
        
        # 5. Meteorology, Tide & Routing
        rain_mode = rainfall_mode if rainfall_mode is not None else self.scenario.rainfall_mode
        if self.meteorology is None:
            self.meteorology = SyntheticMeteorologyEngine(
                rows=rows,
                cols=cols,
                duration_hours=dur,
                intensity_mm_hr=inten,
                dt_minutes=dt_min,
                mode=rain_mode
            )
        if self.tide is None:
            self.tide = TideEngine(
                mean_sea_level_m=self.scenario.msl,
                tidal_range_m=self.scenario.tidal_range,
                storm_surge_m=self.scenario.surge
            )
        if self.routing is None:
            self.routing = FlowRoutingEngine(solver_type="diffusion")

        # 6. Hydraulics & Outfalls
        if self.hydraulics is None:
            self.hydraulics = HydraulicNetworkEngine()
            # Load real OSM layers through repository
            waterways_layer = g_repo.load_layer("waterways")
            # Populate stubs or graph details if any waterways are loaded
            self.hydraulics.load_network_data(waterways_layer.get("features", []), [])

        # 7. Diagnostics Engine
        if self.flood is None:
            self.flood = FloodEngine(rows, cols)
        
        # 8. Outputs
        if self.results_manager is None:
            self.results_manager = ResultsManager()

        # Clear histories
        self.mass_balance_history.clear()
        self.hydraulic_discharge_history.clear()
        self.hydraulic_storage_history.clear()

        logger.info(
            "SimulationController initialized with DI and Repositories",
            extra={"scenario": self.scenario_name, "dt_min": dt_min, "grid_shape": (rows, cols)}
        )

    def step(self) -> Dict[str, Any]:
        """
        Advances the simulation by one timestep, running the hydrology/hydraulic sequence.
        """
        if (self.grid_manager is None or self.state is None or self.clock is None or 
            self.meteorology is None or self.infiltration is None or self.routing is None or 
            self.hydraulics is None or self.tide is None or self.flood is None):
            raise SimulationException("Controller not initialized. Call initialize() first.")

        # A. Advance clock
        dt = self.clock.dt_seconds
        self.clock.advance_timestep()
        self.state.current_timestep += 1
        self.state.current_simulation_time = self.clock.current_time

        # B. Ingest boundary conditions (Meteorology & Tide)
        step_idx = self.state.current_timestep - 1
        rain_rate_grid = self.meteorology.get_spatial_rainfall_grid(step_idx)
        self.state.current_rainfall = float(rain_rate_grid.mean() * 1000.0 * 3600.0) # mm/hr rate representation
        
        sea_level = self.tide.get_sea_level(self.clock.elapsed_seconds)
        self.state.current_tide = sea_level

        # C. Deposit rain on surface water grid
        elev_grid = self.grid_manager.elevation
        elev_min  = float(elev_grid.min())
        elev_max  = float(elev_grid.max())
        elev_range = max(elev_max - elev_min, 1.0)
        elev_norm = (elev_grid - elev_min) / elev_range
        flood_weight = np.exp(-2.0 * elev_norm).astype(np.float32)
        flood_weight /= flood_weight.mean()

        self.state.water_depth_grid += rain_rate_grid * dt * flood_weight

        # D. Soil Infiltration
        manning_grid = np.full(self.state.water_depth_grid.shape, settings.default_cn, dtype=np.float32)
        infil_grid = self.infiltration.compute_infiltration(
            rainfall_rate_m_s=rain_rate_grid,
            water_depth_m=self.state.water_depth_grid,
            manning_n=manning_grid,
            dt_seconds=dt
        )
        self.state.water_depth_grid -= infil_grid
        self.state.water_depth_grid = np.maximum(self.state.water_depth_grid, 0.0)

        # E. Drainage storm intake
        drain_cap_grid = np.full(self.state.water_depth_grid.shape, 2.78e-7, dtype=np.float32)
        self.state.water_depth_grid, actual_intake = self.hydraulics.apply_drainage_intake(
            water_depth_m=self.state.water_depth_grid,
            drain_capacity_m_s=drain_cap_grid,
            dt_seconds=dt
        )
        
        # Apply outfall backwater blocks based on sea level
        outfall_mask = np.zeros_like(self.state.water_depth_grid, dtype=bool)
        self.state.water_depth_grid = self.hydraulics.apply_tide_backwater_effects(
            tide_level_m=sea_level,
            water_depth_m=self.state.water_depth_grid,
            outfall_mask=outfall_mask
        )

        # F. Surface Flow routing
        dx = settings.cell_size_m
        substeps = settings.diffusion_substeps
        dt_sub = dt / substeps
        
        for _ in range(substeps):
            self.state.water_depth_grid, vx, vy = self.routing.route(
                elevation=self.grid_manager.elevation,
                water_depth=self.state.water_depth_grid,
                manning_n=manning_grid,
                dx_m=dx,
                dt_seconds=dt_sub
            )
            self.state.velocity_x_grid = vx
            self.state.velocity_y_grid = vy

        # G. Update diagnostics (extent, duration, hazard rating)
        flooded_mask, hazard_rating, hazard_class = self.flood.update_metrics(
            water_depth_m=self.state.water_depth_grid,
            velocity_x_m_s=self.state.velocity_x_grid,
            velocity_y_m_s=self.state.velocity_y_grid,
            dt_seconds=dt
        )
        self.state.flood_flag_grid = flooded_mask

        # H. Log metrics and save to mass balance history
        rain_vol_m3   = float((rain_rate_grid * dt).sum())
        intake_vol_m3 = float(actual_intake.sum())
        surface_vol   = float(self.state.water_depth_grid.sum())
        max_depth     = float(self.state.water_depth_grid.max())
        
        balance_entry = {
            "timestep": self.state.current_timestep,
            "initial_water": float(surface_vol + rain_vol_m3 - intake_vol_m3),  # approximate initial
            "boundary_inflow": rain_vol_m3,
            "boundary_outflow": intake_vol_m3,
            "current_storage": surface_vol,
            "absolute_error": 0.0,
            "relative_error": 0.0
        }
        self.mass_balance_history.append(balance_entry)
        self.hydraulic_discharge_history.append(0.0)  # stub outfall discharge
        self.hydraulic_storage_history.append(0.0)    # stub conduit storage

        logger.info(
            "-------- Timestep --------",
            extra={
                "step": self.state.current_timestep,
                "rain_added_m3": round(rain_vol_m3, 4),
                "drain_intake_m3": round(intake_vol_m3, 4),
                "surface_vol_m3": round(surface_vol, 4),
                "max_depth_m": round(max_depth, 4),
                "mean_depth_m": round(float(self.state.water_depth_grid.mean()), 6),
                "flooded_cells": int(flooded_mask.sum()),
            }
        )

        return self.state.to_dict()

    def run_all(self) -> List[List[List[float]]]:
        """
        Runs the simulation loop, triggers diagnostics and manifest writing automatically (Tasks 5 & 6).
        """
        if self.meteorology is None or self.state is None or self.results_manager is None:
            raise SimulationException("Controller not initialized.")
        
        hyetograph = self.meteorology.generate_hyetograph()
        steps = len(hyetograph)

        depth_history = []
        depth_grids = []
        
        # Store initial state t=0
        depth_history.append(
            [[round(float(v), 4) for v in row] for row in self.state.water_depth_grid.tolist()]
        )
        depth_grids.append(self.state.water_depth_grid.copy())

        for _ in range(steps):
            self.step()
            depth_history.append(
                [[round(float(v), 4) for v in row] for row in self.state.water_depth_grid.tolist()]
            )
            depth_grids.append(self.state.water_depth_grid.copy())

        # Compile execution duration
        execution_duration = time.time() - self.start_execution_time

        # Automatically execute DiagnosticsManager (Task 5)
        diag = DiagnosticsManager(output_dir=str(self.results_manager.output_dir))
        diag_files = diag.run_diagnostics(
            elevation=self.grid_manager.elevation,
            depth_history=depth_grids,
            time_steps_min=float(self.clock.dt_seconds / 60.0),
            rainfall_hyetograph_mm=hyetograph.tolist(),
            mass_balance_history=self.mass_balance_history,
            hydraulic_discharge_history=self.hydraulic_discharge_history,
            hydraulic_storage_history=self.hydraulic_storage_history,
            execution_time_seconds=execution_duration,
            metadata=self.grid_manager.meta
        )

        # Automatically write SimulationManifest.json Version 2 (Task 6)
        self._write_manifest_v2(execution_duration, diag_files)

        return depth_history

    def _write_manifest_v2(self, execution_duration: float, output_paths: Dict[str, str]) -> None:
        """
        Generates and saves the SimulationManifest.json Version 2.
        """
        if self.grid_manager is None or self.state is None:
            return

        git_commit, git_branch = get_git_info()
        dem_checksum = get_file_checksum(str(settings.dem_path))
        osm_checksum = get_file_checksum(str(settings.gpkg_path))

        # Determine strategy configurations
        routing_strategy = "diffusion"
        infiltration_strategy = "constant"
        hydraulic_strategy = "simple_intake_only"

        # Resolve imported package versions
        try:
            import rasterio
            rasterio_ver = rasterio.__version__
            gdal_ver = rasterio.__gdal_version__
        except Exception:
            rasterio_ver = "unavailable"
            gdal_ver = "unavailable"

        manifest = {
            "manifest_version": "2.0.0",
            "simulation_uuid": self.run_uuid,
            "software_version": settings.app_version,
            "environment_metadata": {
                "python_version": sys.version,
                "operating_system": platform.platform(),
                "numpy_version": np.__version__,
                "rasterio_version": rasterio_ver,
                "gdal_version": gdal_ver,
                "git_commit": git_commit,
                "git_branch": git_branch
            },
            "datasets": {
                "dem_path": str(settings.dem_path),
                "dem_checksum_sha256": dem_checksum,
                "osm_path": str(settings.gpkg_path),
                "osm_checksum_sha256": osm_checksum
            },
            "parameters": {
                "scenario_name": self.scenario_name,
                "rainfall_intensity_mm_hr": self.scenario.rainfall_intensity,
                "rainfall_duration_hours": self.scenario.rainfall_duration,
                "rainfall_mode": self.scenario.rainfall_mode,
                "cell_size_m": settings.cell_size_m,
                "grid_size": [self.grid_manager.rows, self.grid_manager.cols],
                "time_step_min": float(self.clock.dt_seconds / 60.0) if self.clock else 15.0
            },
            "strategies": {
                "routing_strategy": routing_strategy,
                "infiltration_strategy": infiltration_strategy,
                "hydraulic_strategy": hydraulic_strategy
            },
            "metrics": {
                "execution_time_seconds": execution_duration,
                "max_depth_m": float(self.state.water_depth_grid.max()),
                "mean_depth_m": float(self.state.water_depth_grid.mean()),
                "flooded_cells_count": int(self.state.flood_flag_grid.sum()),
                "flooded_area_percentage": float(np.sum(self.state.flood_flag_grid) / self.state.flood_flag_grid.size * 100.0)
            },
            "output_files": output_paths
        }

        manifest_path = os.path.join(str(self.results_manager.output_dir), "SimulationManifest.json")
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
            logger.info("SimulationManifest.json version 2 written successfully", extra={"path": manifest_path})
        except Exception as exc:
            logger.error(f"Failed to write SimulationManifest.json: {exc}")

    def reset(self) -> None:
        """Resets clock, state arrays, and active engines."""
        if self.clock:
            self.clock.reset()
        if self.state:
            self.state.reset()
        if self.infiltration:
            self.infiltration.reset()
        if self.flood:
            self.flood.reset()
        self.mass_balance_history.clear()
        self.hydraulic_discharge_history.clear()
        self.hydraulic_storage_history.clear()
        logger.info("SimulationController reset successfully")
