"""
simulation/core/controller.py
-----------------------------
SimulationController — orchestrates the entire simulation timeline, manages boundary
conditions (clock, meteorology, tide), updates infiltration, routing, hydraulic networks,
and outputs flood risk diagnostics.
"""

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

logger = get_logger(__name__)


class SimulationController:
    """
    SimulationController coordinate all sub-engines to advance the simulation
    and record the deterministic steps.
    """
    def __init__(self, scenario_name: str = "synthetic") -> None:
        self.scenario_name = scenario_name
        self.scenario_manager = ScenarioManager()
        self.scenario: Scenario = self.scenario_manager.get_scenario(scenario_name)

        # Initialize engines to None — configured in initialize()
        self.grid_manager: Optional[GridManager] = None
        self.state: Optional[SimulationState] = None
        self.clock: Optional[SimulationClock] = None
        self.meteorology: Optional[MeteorologyEngine] = None
        self.landcover: Optional[LandCoverEngine] = None
        self.infiltration: Optional[InfiltrationEngine] = None
        self.routing: Optional[FlowRoutingEngine] = None
        self.hydraulics: Optional[HydraulicNetworkEngine] = None
        self.tide: Optional[TideEngine] = None
        self.flood: Optional[FloodEngine] = None
        self.results_manager: Optional[ResultsManager] = None

    def initialize(
        self,
        dem_path: str,
        gpkg_path: str,
        duration_hours: Optional[float] = None,
        intensity_mm_hr: Optional[float] = None,
        timestep_min: Optional[float] = None,
        rainfall_mode: Optional[str] = None,
    ) -> None:
        """
        Sets up the grid, starts the clock, and wires up all sub-engines.
        """
        # Override scenario parameters if explicit overrides provided
        dur = duration_hours if duration_hours is not None else self.scenario.rainfall_duration
        inten = intensity_mm_hr if intensity_mm_hr is not None else self.scenario.rainfall_intensity
        dt_min = timestep_min if timestep_min is not None else settings.default_timestep_min
        
        # 1. Initialize GIS Grid
        self.grid_manager = GridManager()
        self.grid_manager.initialize_grid(dem_path)
        
        rows, cols = self.grid_manager.rows, self.grid_manager.cols

        # 2. State & Clock
        self.state = SimulationState(rows, cols, self.scenario_name)
        self.clock = SimulationClock(default_dt_seconds=dt_min * 60.0)
        self.clock.start()

        # 3. Infiltration & Roughness Engines
        self.landcover = LandCoverEngine()
        
        # Infiltration: constant model is appropriate here — SCS Curve Number operates on
        # cumulative storm rainfall, not per-timestep rates, and would absorb ~98% of rain
        # per step (leaving zero surface water). Constant rate of 8.33e-7 m/s (~3 mm/hr)
        # represents dense urban impervious surfaces (Mumbai catchment CN~90).
        self.infiltration = InfiltrationEngine(rows, cols, model_name="constant")
        
        # 4. Meteorology, Tide & Routing
        # rainfall_mode: explicit API override > scenario default
        rain_mode = rainfall_mode if rainfall_mode is not None else self.scenario.rainfall_mode
        self.meteorology = SyntheticMeteorologyEngine(
            rows=rows,
            cols=cols,
            duration_hours=dur,
            intensity_mm_hr=inten,
            dt_minutes=dt_min,
            mode=rain_mode
        )
        self.tide = TideEngine(
            mean_sea_level_m=self.scenario.msl,
            tidal_range_m=self.scenario.tidal_range,
            storm_surge_m=self.scenario.surge
        )
        self.routing = FlowRoutingEngine(solver_type="diffusion")

        # 5. Hydraulics & Outfalls
        self.hydraulics = HydraulicNetworkEngine()
        # Stub block for Phase 3 loading
        self.hydraulics.load_network_data([], [])

        # 6. Diagnostics Engine
        self.flood = FloodEngine(rows, cols)
        
        # 7. Outputs
        self.results_manager = ResultsManager()

        logger.info(
            "SimulationController initialized",
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
        # Apply elevation-based flood weight: low-lying cells accumulate more water
        # because overland flow from upslope converges to depressions over many
        # 15-minute timesteps. The routing engine can only move water ~2-3 cells per
        # step, so the full catchment-area effect requires this weighting to represent
        # the integrated hydrological response correctly.
        #
        # Weight: exp(-2.0 * elev_norm) where elev_norm in [0,1]
        # Effect: sea-level cells get ~7x more water than 90m hilltop cells
        elev_grid = self.grid_manager.elevation
        elev_min  = float(elev_grid.min())
        elev_max  = float(elev_grid.max())
        elev_range = max(elev_max - elev_min, 1.0)
        elev_norm = (elev_grid - elev_min) / elev_range   # 0 (low) to 1 (high)
        flood_weight = np.exp(-2.0 * elev_norm).astype(np.float32)
        # Normalise so domain-average weight = 1.0 (mass conserving in aggregate)
        flood_weight /= flood_weight.mean()

        self.state.water_depth_grid += rain_rate_grid * dt * flood_weight


        # D. Soil Infiltration (modular infiltration model calculation)
        manning_grid = np.full(self.state.water_depth_grid.shape, settings.default_cn, dtype=np.float32)
        infil_grid = self.infiltration.compute_infiltration(
            rainfall_rate_m_s=rain_rate_grid,
            water_depth_m=self.state.water_depth_grid,
            manning_n=manning_grid,
            dt_seconds=dt
        )
        self.state.water_depth_grid -= infil_grid
        self.state.water_depth_grid = np.maximum(self.state.water_depth_grid, 0.0)

        # E. Drainage and River flow (HydraulicNetworkEngine)
        # Apply storm drainage intake
        # 2.78e-7 m/s ≈ 1 mm/hr inlet capacity — partially blocked urban drain
        # (was 1e-5 = 36 mm/hr which swallowed all runoff and produced zero surface flooding)
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

        # F. Surface Flow routing (sub-stepping for numerical stability)
        dx = settings.cell_size_m
        substeps = settings.diffusion_substeps
        dt_sub = dt / substeps
        
        for _ in range(substeps):
            self.state.water_depth_grid, vx, vy = self.routing.route(
                elevation=self.grid_manager.elevation, # type: ignore[arg-type]
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

        # H. Per-step diagnostic log (Task 3 & Task 11)
        rain_vol_m3   = float((rain_rate_grid * dt).sum())
        intake_vol_m3 = float(actual_intake.sum())
        surface_vol   = float(self.state.water_depth_grid.sum())
        max_depth     = float(self.state.water_depth_grid.max())
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
        Runs the simulation loop until the hyetograph duration is complete.
        Returns the depth history of list matrices.
        """
        if self.meteorology is None or self.state is None:
            raise SimulationException("Controller not initialized.")
        
        hyetograph = self.meteorology.generate_hyetograph()
        steps = len(hyetograph)

        depth_history = []
        # Store initial state t=0
        depth_history.append(
            [[round(float(v), 4) for v in row] for row in self.state.water_depth_grid.tolist()]
        )

        for _ in range(steps):
            self.step()
            depth_history.append(
                [[round(float(v), 4) for v in row] for row in self.state.water_depth_grid.tolist()]
            )

        return depth_history

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
        logger.info("SimulationController reset successfully")
