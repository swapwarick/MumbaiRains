"""
tests/test_refactoring.py
-------------------------
Unit tests verifying Version 1.0 Beta architectural refactoring:
1. Data repositories (Terrain, GIS, Rainfall, Scenario, Observation)
2. Checkpoint manager (save, load, resume, random seeds)
3. Plugin registry and adapters
4. Scenario folder loading
"""

import os
import json
import csv
import pickle
import pytest
import numpy as np

from backend.data.terrain_repo import TerrainRepository
from backend.data.gis_repo import GISRepository
from backend.data.rainfall_repo import RainfallRepository
from backend.data.scenario_repo import ScenarioRepository, ScenarioPackage
from backend.data.observation_repo import ObservationRepository

from simulation.checkpoints.manager import CheckpointManager
from simulation.plugins import registry, RoutingPluginAdapter, InfiltrationPluginAdapter, HydraulicPluginAdapter
from simulation.core.controller import SimulationController
from simulation.core.clock import SimulationClock
from simulation.core.state import SimulationState


def test_repositories(tmp_path):
    # 1. Test TerrainRepository
    dem_file = tmp_path / "mumbai_dem.tif"
    # write mock tif or stub
    dem_file.write_bytes(b"dummy_dem")
    repo = TerrainRepository(str(dem_file))
    assert repo.dem_path == str(dem_file)

    # 2. Test RainfallRepository
    rain_dir = tmp_path / "rainfall"
    rain_dir.mkdir()
    csv_file = rain_dir / "test_storm.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_min", "rainfall_mm"])
        writer.writerow([0, 5.0])
        writer.writerow([15, 12.0])

    rain_repo = RainfallRepository(str(rain_dir))
    times, depths = rain_repo.load_rainfall_csv("test_storm.csv")
    assert times == [0.0, 15.0]
    assert depths == [5.0, 12.0]

    # 3. Test ObservationRepository
    obs_dir = tmp_path / "validation"
    obs_dir.mkdir()
    obs_csv = obs_dir / "gauge_bkc.csv"
    with open(obs_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_min", "depth_m"])
        writer.writerow([0.0, 0.0])
        writer.writerow([30.0, 0.15])
        
    obs_repo = ObservationRepository(str(obs_dir))
    records = obs_repo.load_gauge_observations("bkc")
    assert records == [(0.0, 0.0), (30.0, 0.15)]


def test_scenario_package_loading(tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    
    # Create scenario folder
    scen_folder = scenarios_dir / "historical_2005"
    scen_folder.mkdir()
    
    # Write manifest.json
    with open(scen_folder / "manifest.json", "w") as f:
        json.dump({"name": "historical_2005", "rainfall_mode": "historical", "description": "Test"}, f)
        
    # Write config.json
    with open(scen_folder / "config.json", "w") as f:
        json.dump({"intensity_mm_hr": 40.0, "duration_hours": 2.0}, f)
        
    # Write rainfall.csv
    with open(scen_folder / "rainfall.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_min", "rainfall_mm"])
        writer.writerow([0, 10.0])
        writer.writerow([15, 20.0])

    repo = ScenarioRepository(str(scenarios_dir))
    assert repo.list_scenarios() == ["historical_2005"]
    
    scen = repo.load_scenario("historical_2005")
    assert scen.name == "historical_2005"
    assert scen.rainfall_mode == "historical"
    assert scen.rainfall_intensity == 40.0
    assert scen.rainfall_duration == 2.0
    assert scen.rainfall_time_series == [0.0, 15.0]
    assert scen.rainfall_depth_series == [10.0, 20.0]


def test_plugin_registry():
    # Verify plugins are registered
    diff_plug = registry.get_routing("diffusion")
    assert isinstance(diff_plug, RoutingPluginAdapter)
    
    const_infil = registry.get_infiltration("constant")
    assert isinstance(const_infil, InfiltrationPluginAdapter)

    kin_hyd = registry.get_hydraulic("kinematic")
    assert isinstance(kin_hyd, HydraulicPluginAdapter)


def test_checkpoint_save_and_resume(tmp_path):
    # Setup dummy objects
    state = SimulationState(10, 10, "test")
    state.water_depth_grid[5, 5] = 1.25
    
    clock = SimulationClock()
    clock.start()
    clock.advance_timestep()
    
    manifest = {"run_uuid": "12345"}
    mass_balance = {"surface": [], "hydraulic": {}}
    
    checkpoint_file = tmp_path / "checkpoint_test.pkl"
    
    # Save checkpoint
    CheckpointManager.save_checkpoint(
        filepath=str(checkpoint_file),
        state=state,
        hydraulic_state=None,
        clock=clock,
        manifest=manifest,
        mass_balance_history=mass_balance,
        current_step=1,
        seed=12345
    )
    
    # Assert file created
    assert checkpoint_file.exists()
    
    # Load checkpoint
    data = CheckpointManager.load_checkpoint(str(checkpoint_file))
    assert data["current_step"] == 1
    assert data["seed"] == 12345
    assert data["state"].water_depth_grid[5, 5] == 1.25
    
    # Resume testing using mock controller
    class DummyController:
        def __init__(self):
            self.state = None
            self.hydraulic_state = None
            self.clock = None
            
    ctrl = DummyController()
    CheckpointManager.resume(ctrl, str(checkpoint_file))
    assert ctrl.state.water_depth_grid[5, 5] == 1.25
    assert ctrl.state.current_timestep == 1
