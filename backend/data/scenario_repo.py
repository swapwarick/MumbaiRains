"""
backend/data/scenario_repo.py
----------------------------
ScenarioRepository discovering and loading packaged scenarios from the scenarios/ directory.
"""

from typing import Dict, Any, List, Optional
import os
import json
import csv
from pathlib import Path

from backend.config import settings
from backend.exceptions import SimulationException

class ScenarioPackage:
    """
    Data container representing a fully packaged simulation scenario.
    """
    def __init__(
        self,
        name: str,
        manifest: Dict[str, Any],
        config: Dict[str, Any],
        notes: str,
        rainfall_time_series: Optional[List[float]] = None,
        rainfall_depth_series: Optional[List[float]] = None
    ) -> None:
        self.name = name
        self.manifest = manifest
        self.config = config
        self.notes = notes
        self.rainfall_time_series = rainfall_time_series or []
        self.rainfall_depth_series = rainfall_depth_series or []

        # Map typical attributes for SimulationController interface
        self.rainfall_intensity = float(self.config.get("intensity_mm_hr", 30.0))
        self.rainfall_duration = float(self.config.get("duration_hours", 4.0))
        self.rainfall_mode = str(self.manifest.get("rainfall_mode", "constant"))
        self.msl = float(self.config.get("mean_sea_level_m", 0.0))
        self.tidal_range = float(self.config.get("tidal_range_m", 4.5))
        self.surge = float(self.config.get("storm_surge_m", 0.0))
        self.clogging_factor = float(self.config.get("drainage_clogging_factor", 0.0))
        self.description = str(self.manifest.get("description", ""))


class ScenarioRepository:
    """
    Repository for discovering, validating, and loading packaged scenarios.
    """
    def __init__(self, scenarios_dir: str = "") -> None:
        self.scenarios_dir = scenarios_dir or os.path.join(str(settings.project_root), "scenarios")
        os.makedirs(self.scenarios_dir, exist_ok=True)

    def list_scenarios(self) -> List[str]:
        """Discovers scenario packages in the scenarios folder."""
        if not os.path.exists(self.scenarios_dir):
            return []
        return [
            d for d in os.listdir(self.scenarios_dir)
            if os.path.isdir(os.path.join(self.scenarios_dir, d))
        ]

    def load_scenario(self, scenario_name: str) -> ScenarioPackage:
        """
        Loads a scenario package by folder name.
        """
        scenario_path = os.path.join(self.scenarios_dir, scenario_name.lower().strip())
        if not os.path.exists(scenario_path):
            # Fallback/Dummy logic if scenario folder is missing in development/testing
            if getattr(settings, "environment", "development") != "production":
                return self._create_dummy_scenario_package(scenario_name)
            raise SimulationException(f"Production validation failed: Scenario package directory {scenario_path} not found.")

        # Parse manifest.json
        manifest_file = os.path.join(scenario_path, "manifest.json")
        if not os.path.exists(manifest_file):
            raise SimulationException(f"Scenario package manifest missing at {manifest_file}")
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # Parse config.json
        config_file = os.path.join(scenario_path, "config.json")
        if not os.path.exists(config_file):
            raise SimulationException(f"Scenario package config missing at {config_file}")
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Parse notes.md
        notes_file = os.path.join(scenario_path, "notes.md")
        notes = ""
        if os.path.exists(notes_file):
            with open(notes_file, "r", encoding="utf-8") as f:
                notes = f.read()

        # Parse rainfall.csv (optional, for historical/custom storms)
        rainfall_file = os.path.join(scenario_path, "rainfall.csv")
        time_series = []
        rain_series = []
        if os.path.exists(rainfall_file):
            with open(rainfall_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    time_series.append(float(row["time_min"]))
                    rain_series.append(float(row["rainfall_mm"]))

        return ScenarioPackage(
            name=scenario_name,
            manifest=manifest,
            config=config,
            notes=notes,
            rainfall_time_series=time_series,
            rainfall_depth_series=rain_series
        )

    def _create_dummy_scenario_package(self, scenario_name: str) -> ScenarioPackage:
        """Generates a default synthetic ScenarioPackage on the fly for fallbacks."""
        return ScenarioPackage(
            name=scenario_name,
            manifest={
                "name": scenario_name,
                "description": "Auto-generated dummy scenario fallback.",
                "rainfall_mode": "constant"
            },
            config={
                "intensity_mm_hr": 30.0,
                "duration_hours": 4.0,
                "mean_sea_level_m": 0.0,
                "tidal_range_m": 4.5,
                "storm_surge_m": 0.0,
                "drainage_clogging_factor": 0.0
            },
            notes="No notes. md provided."
        )
