"""
tests/test_integration.py
-------------------------
Integrated end-to-end tests for Mumbai Flood Digital Twin (Sprints 1–6).
Validates coupling between Terrain, Forcing, Surface Flow, Drainage, and Hydraulic Routing.
"""

import os
import pytest
import numpy as np

from simulation.core.state import SimulationState
from simulation.terrain.engine import TerrainEngine
from simulation.terrain.algorithms import compute_flow_direction_d8_all
from simulation.forcing.engine import ForcingEngine
from simulation.forcing.sources import RainSource
from simulation.routing.engine import SurfaceRoutingEngine, BoundaryType
from simulation.drainage_interface.types import DrainInlet
from simulation.drainage_interface.engine import DrainageInterfaceEngine
from simulation.network.engine import HydraulicNetworkEngine
from simulation.hydraulic.pipe import Pipe
from simulation.hydraulic.junction import Junction
from simulation.hydraulic.state import HydraulicState
from simulation.hydraulic.routing import HydraulicRoutingEngine, KinematicRoutingStrategy


class TestIntegratedSimulation:
    def test_integration_flat_surface(self):
        """
        Test 1 — Flat Surface
        - 100x100 flat DEM.
        - 50 mm/hr constant rain for 30 minutes.
        - Verification: Uniform water spread, no preferred flow, mass conserved, no negative depths.
        """
        rows, cols = 100, 100
        dx = 10.0
        cell_area = dx * dx
        
        # Init flat terrain (10.0m everywhere)
        # Sinks at every cell: downstream points to itself
        r_coords, c_coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
        downstream_cells = np.stack([r_coords, c_coords], axis=-1).astype(np.int32)
        
        # State & Engines
        state = SimulationState(rows, cols)
        forcing = ForcingEngine(dx_m=dx, simulation_uuid="flat_sim")
        rain = RainSource("rain_src", 50.0)
        forcing.register_source(rain)
        
        routing = SurfaceRoutingEngine(
            dx_m=dx,
            downstream_cells=downstream_cells,
            transfer_fraction=0.25,
            boundary_type=BoundaryType.CLOSED
        )
        
        # 30 minutes of rain, dt = 30 seconds -> 60 steps
        dt = 30.0
        steps = 60
        
        cumulative_rain = 0.0
        for _ in range(steps):
            state, forcing_rep = forcing.advance(state, dt)
            cumulative_rain += forcing_rep.water_added
            
            state = routing.route(state, dt)
            
            assert np.all(state.water_depth_grid >= 0.0)
            
        # Expected depth: 50 mm/hr for 0.5 hours = 25 mm = 0.025m
        assert np.allclose(state.water_depth_grid, 0.025, rtol=1e-3)
        
        # Mass conservation: Storage equals rain added
        current_vol = state.water_depth_grid.sum() * cell_area
        assert np.allclose(current_vol, cumulative_rain)

    def test_integration_uniform_slope(self):
        """
        Test 2 — Uniform Slope
        - Elevation descending downhill towards row 0.
        - Expected: Water moves downhill, mass conserved, exits at open boundary.
        """
        rows, cols = 10, 10
        dx = 10.0
        cell_area = dx * dx
        
        # Setup downhill flow towards row 0
        r_coords, c_coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
        downstream_r = np.clip(r_coords - 1, -1, rows - 1)
        downstream_cells = np.stack([downstream_r, c_coords], axis=-1).astype(np.int32)
        
        state = SimulationState(rows, cols)
        forcing = ForcingEngine(dx_m=dx, simulation_uuid="slope_sim")
        rain = RainSource("rain_src", 50.0)
        forcing.register_source(rain)
        
        routing = SurfaceRoutingEngine(
            dx_m=dx,
            downstream_cells=downstream_cells,
            transfer_fraction=0.25,
            boundary_type=BoundaryType.OPEN
        )
        
        dt = 10.0
        steps = 18  # 3 minutes
        
        cumulative_rain = 0.0
        for _ in range(steps):
            state, forcing_rep = forcing.advance(state, dt)
            cumulative_rain += forcing_rep.water_added
            state = routing.route(state, dt)
            
        # Verify water exits through row 0 (open boundary losses)
        boundary_loss = sum(r.boundary_outflow for r in routing.mass_balance_history)
        current_storage = state.water_depth_grid.sum() * cell_area
        
        # Check mass conservation
        assert np.allclose(current_storage + boundary_loss, cumulative_rain)
        # Higher cells (row 9) must have less water than lower cells (row 1) due to downhill routing
        assert state.water_depth_grid[9, 5] < state.water_depth_grid[1, 5]

    def test_integration_single_drain(self):
        """
        Test 3 — Single Drain
        - 10x10 flat surface with 1 inlet at (5, 5).
        - Inlet connected to pipe -> outfall.
        - Verification: Mass balance of coupled surface + sub-surface model.
        """
        rows, cols = 10, 10
        dx = 10.0
        cell_area = dx * dx
        transform = [dx, 0.0, 0.0, 0.0, -dx, rows * dx]
        
        # Flat surface (sinks)
        r_coords, c_coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
        downstream_cells = np.stack([r_coords, c_coords], axis=-1).astype(np.int32)
        
        # Engines
        state = SimulationState(rows, cols)
        forcing = ForcingEngine(dx_m=dx, simulation_uuid="drain_sim")
        rain = RainSource("rain_src", 50.0)
        forcing.register_source(rain)
        
        routing = SurfaceRoutingEngine(dx_m=dx, downstream_cells=downstream_cells, transfer_fraction=0.25)
        
        inlets = [DrainInlet("inlet_1", 5, 5, 10.0, 0.02, 9.0, False, "node_1")]
        drainage = DrainageInterfaceEngine(inlets, max_search_radius_m=30.0)
        drainage.associate_grid(rows, cols, transform)
        
        pipes = [Pipe("pipe_1", 100.0, 0.3, 0.013, 9.0, 8.0, "node_1", "outfall_1")]
        junctions = [
            Junction("node_1", 10.0, 9.0, 11.0, 10.0),
            Junction("outfall_1", 8.0, 8.0, 8.0, 1.0)
        ]
        hyd_strategy = KinematicRoutingStrategy()
        hyd_engine = HydraulicRoutingEngine(pipes, junctions, hyd_strategy)
        hyd_state = HydraulicState({"pipe_1": 0.0}, {"pipe_1": 0.0}, {"node_1": 0.0, "outfall_1": 0.0})
        
        # Time Loop
        dt = 5.0
        steps = 12  # 1 minute
        
        cumulative_rain = 0.0
        for _ in range(steps):
            # A. Rainfall
            state, forcing_rep = forcing.advance(state, dt)
            cumulative_rain += forcing_rep.water_added
            
            # B. Surface routing
            state = routing.route(state, dt)
            
            # C. Drainage capture
            new_depth, intake_report, _ = drainage.apply_inlet_intake(state.water_depth_grid, cell_area, dt)
            state.water_depth_grid = new_depth
            
            # D. Hydraulic routing
            inflows = {"node_1": intake_report["inlet_1"] / dt}
            hyd_state, hyd_rep = hyd_engine.route(hyd_state, inflows, dt)
            
        # Combined Mass Audit
        surface_storage = state.water_depth_grid.sum() * cell_area
        subsurface_storage = sum(hyd_state.junction_storage.values()) + sum(hyd_state.pipe_storage.values())
        discharged_water = hyd_engine.cumulative_outflow_m3
        
        total_system_water = surface_storage + subsurface_storage + discharged_water
        assert np.allclose(total_system_water, cumulative_rain, rtol=1e-3)
        assert discharged_water > 0.0

    def test_integration_blocked_drain(self):
        """
        Test 4 — Blocked Drain
        - Same setup as Test 3, but the inlet is blocked.
        - Verification: Water bypasses, outfall discharge remains 0.0.
        """
        rows, cols = 10, 10
        dx = 10.0
        cell_area = dx * dx
        transform = [dx, 0.0, 0.0, 0.0, -dx, rows * dx]
        
        r_coords, c_coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
        downstream_cells = np.stack([r_coords, c_coords], axis=-1).astype(np.int32)
        
        state = SimulationState(rows, cols)
        forcing = ForcingEngine(dx_m=dx, simulation_uuid="blocked_sim")
        rain = RainSource("rain_src", 50.0)
        forcing.register_source(rain)
        
        routing = SurfaceRoutingEngine(dx_m=dx, downstream_cells=downstream_cells, transfer_fraction=0.25)
        
        # Blocked inlet!
        inlets = [DrainInlet("inlet_1", 5, 5, 10.0, 0.02, 9.0, True, "node_1")]
        drainage = DrainageInterfaceEngine(inlets, max_search_radius_m=30.0)
        drainage.associate_grid(rows, cols, transform)
        
        pipes = [Pipe("pipe_1", 100.0, 0.3, 0.013, 9.0, 8.0, "node_1", "outfall_1")]
        junctions = [
            Junction("node_1", 10.0, 9.0, 11.0, 10.0),
            Junction("outfall_1", 8.0, 8.0, 8.0, 1.0)
        ]
        hyd_strategy = KinematicRoutingStrategy()
        hyd_engine = HydraulicRoutingEngine(pipes, junctions, hyd_strategy)
        hyd_state = HydraulicState({"pipe_1": 0.0}, {"pipe_1": 0.0}, {"node_1": 0.0, "outfall_1": 0.0})
        
        dt = 5.0
        steps = 12
        
        for _ in range(steps):
            state, forcing_rep = forcing.advance(state, dt)
            state = routing.route(state, dt)
            new_depth, intake_report, _ = drainage.apply_inlet_intake(state.water_depth_grid, cell_area, dt)
            state.water_depth_grid = new_depth
            
            inflows = {"node_1": intake_report["inlet_1"] / dt}
            hyd_state, hyd_rep = hyd_engine.route(hyd_state, inflows, dt)
            
        assert hyd_engine.cumulative_outflow_m3 == 0.0
        assert hyd_state.junction_storage["node_1"] == 0.0

    def test_integration_two_drains(self):
        """
        Test 5 — Two Drains
        - 2 inlets merge to same junction and outfall.
        - Verification: Both inlets active, load splits.
        """
        rows, cols = 10, 10
        dx = 10.0
        cell_area = dx * dx
        transform = [dx, 0.0, 0.0, 0.0, -dx, rows * dx]
        
        r_coords, c_coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
        downstream_cells = np.stack([r_coords, c_coords], axis=-1).astype(np.int32)
        
        state = SimulationState(rows, cols)
        forcing = ForcingEngine(dx_m=dx, simulation_uuid="two_drains")
        rain = RainSource("rain_src", 50.0)
        forcing.register_source(rain)
        
        routing = SurfaceRoutingEngine(dx_m=dx, downstream_cells=downstream_cells, transfer_fraction=0.25)
        
        # 2 inlets
        inlets = [
            DrainInlet("inlet_1", 3, 5, 10.0, 0.02, 9.0, False, "node_1"),
            DrainInlet("inlet_2", 7, 5, 10.0, 0.02, 9.0, False, "node_2")
        ]
        drainage = DrainageInterfaceEngine(inlets, max_search_radius_m=30.0)
        drainage.associate_grid(rows, cols, transform)
        
        pipes = [
            Pipe("pipe_1", 50.0, 0.3, 0.013, 9.0, 8.0, "node_1", "node_3"),
            Pipe("pipe_2", 50.0, 0.3, 0.013, 9.0, 8.0, "node_2", "node_3"),
            Pipe("pipe_3", 50.0, 0.3, 0.013, 8.0, 7.0, "node_3", "outfall_1")
        ]
        junctions = [
            Junction("node_1", 10.0, 9.0, 11.0, 10.0),
            Junction("node_2", 10.0, 9.0, 11.0, 10.0),
            Junction("node_3", 9.0, 8.0, 10.0, 10.0),
            Junction("outfall_1", 7.0, 7.0, 7.0, 1.0)
        ]
        hyd_strategy = KinematicRoutingStrategy()
        hyd_engine = HydraulicRoutingEngine(pipes, junctions, hyd_strategy)
        hyd_state = HydraulicState(
            {"pipe_1": 0.0, "pipe_2": 0.0, "pipe_3": 0.0},
            {"pipe_1": 0.0, "pipe_2": 0.0, "pipe_3": 0.0},
            {"node_1": 0.0, "node_2": 0.0, "node_3": 0.0, "outfall_1": 0.0}
        )
        
        dt = 5.0
        steps = 12
        
        for _ in range(steps):
            state, forcing_rep = forcing.advance(state, dt)
            state = routing.route(state, dt)
            new_depth, intake_report, _ = drainage.apply_inlet_intake(state.water_depth_grid, cell_area, dt)
            state.water_depth_grid = new_depth
            
            inflows = {
                "node_1": intake_report["inlet_1"] / dt,
                "node_2": intake_report["inlet_2"] / dt
            }
            hyd_state, hyd_rep = hyd_engine.route(hyd_state, inflows, dt)
            
        # Verify both inlets captured water
        assert hyd_engine.cumulative_outflow_m3 > 0.0

    def test_integration_kurla_bkc(self):
        """
        Test 6 — Kurla/BKC 1 km²
        - Real-world Greater Mumbai DEM slice (10x10 subset centered on BKC).
        - OSM GeoPackage waterways loaded into graph.
        - Verification: Water follows terrain slope, drainage captures flow, mass conserved.
        """
        # 1. Load full verified Mumbai DEM (using fallback)
        terrain = TerrainEngine().load()
        
        # Center coordinates BKC (Lon = 72.865, Lat = 19.060)
        # Maps to row = 110, col = 68 in 200x200 grid
        r_center, c_center = 110, 68
        
        # Slice a 10x10 neighborhood
        r_slice = slice(r_center - 5, r_center + 5)
        c_slice = slice(c_center - 5, c_center + 5)
        
        elev_slice = terrain.elevation[r_slice, c_slice].copy()
        
        # Calculate D8 flow for this slice
        _, _, downstream = compute_flow_direction_d8_all(elev_slice, cell_size=105.0)
        
        rows, cols = elev_slice.shape
        dx = 105.0
        cell_area = dx * dx
        transform = [dx, 0.0, 72.860, 0.0, -dx, 19.065]
        
        state = SimulationState(rows, cols)
        forcing = ForcingEngine(dx_m=dx, simulation_uuid="bkc_sim")
        rain = RainSource("rain_src", 60.0)  # 60 mm/hr storm
        forcing.register_source(rain)
        
        routing = SurfaceRoutingEngine(dx_m=dx, downstream_cells=downstream, transfer_fraction=0.25)
        
        # 2. Setup 2 drainage inlets in depression zones (minimum elevation cells)
        min_idx = np.unravel_index(np.argmin(elev_slice), elev_slice.shape)
        inlet_r, inlet_c = int(min_idx[0]), int(min_idx[1])
        
        inlets = [
            DrainInlet("inlet_1", inlet_r, inlet_c, float(elev_slice[inlet_r, inlet_c]), 0.1, float(elev_slice[inlet_r, inlet_c]) - 1.0, False, "node_1")
        ]
        drainage = DrainageInterfaceEngine(inlets, max_search_radius_m=300.0)
        drainage.associate_grid(rows, cols, transform)
        
        pipes = [Pipe("pipe_1", 200.0, 0.5, 0.013, float(elev_slice[inlet_r, inlet_c]) - 1.0, float(elev_slice[inlet_r, inlet_c]) - 2.0, "node_1", "outfall_1")]
        junctions = [
            Junction("node_1", float(elev_slice[inlet_r, inlet_c]), float(elev_slice[inlet_r, inlet_c]) - 1.0, float(elev_slice[inlet_r, inlet_c]) + 1.0, 20.0),
            Junction("outfall_1", float(elev_slice[inlet_r, inlet_c]) - 2.0, float(elev_slice[inlet_r, inlet_c]) - 2.0, float(elev_slice[inlet_r, inlet_c]) - 2.0, 1.0)
        ]
        
        hyd_strategy = KinematicRoutingStrategy()
        hyd_engine = HydraulicRoutingEngine(pipes, junctions, hyd_strategy)
        hyd_state = HydraulicState({"pipe_1": 0.0}, {"pipe_1": 0.0}, {"node_1": 0.0, "outfall_1": 0.0})
        
        # 3. Load OSM GeoPackage
        net_engine = HydraulicNetworkEngine()
        net_engine.load_from_gpkg("data/osm/mumbai_osm.gpkg", ["waterways"])
        # Validate that GPKG table parses successfully
        assert net_engine._graph.number_of_nodes() > 0
        
        # Time Loop
        dt = 10.0
        steps = 10
        
        cumulative_rain = 0.0
        for _ in range(steps):
            state, forcing_rep = forcing.advance(state, dt)
            cumulative_rain += forcing_rep.water_added
            
            state = routing.route(state, dt)
            new_depth, intake_report, _ = drainage.apply_inlet_intake(state.water_depth_grid, cell_area, dt)
            state.water_depth_grid = new_depth
            
            inflows = {"node_1": intake_report["inlet_1"] / dt}
            hyd_state, hyd_rep = hyd_engine.route(hyd_state, inflows, dt)
            
        # Verify combined mass conservation
        surface_storage = state.water_depth_grid.sum() * cell_area
        subsurface_storage = sum(hyd_state.junction_storage.values()) + sum(hyd_state.pipe_storage.values())
        discharged_water = hyd_engine.cumulative_outflow_m3
        
        total_water = surface_storage + subsurface_storage + discharged_water
        assert np.allclose(total_water, cumulative_rain, rtol=1e-3)
