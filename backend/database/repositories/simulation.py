"""
backend/database/repositories/simulation.py
--------------------------------------------
SimulationRepository handles importing and exporting simulation runs, scenarios,
timesteps, and statistical logs. It supports file storage or PostGIS stubs.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class SimulationRepository:
    """
    Data Repository for saving and loading flood simulation runs and scenario settings.
    """
    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = output_dir or settings.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_run(self, run_id: str, results: Dict[str, Any]) -> Path:
        """
        Saves the complete simulation run results (depth history + metadata) as JSON.

        Args:
            run_id: A unique identifier for the run.
            results: The simulation response dictionary.

        Returns:
            The Path where the file was written.
        """
        file_path = self.output_dir / f"run_{run_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(results, f)
        logger.info("Simulation run saved to disk", extra={"run_id": run_id, "path": str(file_path)})
        return file_path

    def load_run(self, run_id: str) -> Dict[str, Any]:
        """
        Loads simulation run results from disk.

        Args:
            run_id: A unique identifier for the run.

        Returns:
            The simulation response dictionary.
        """
        file_path = self.output_dir / f"run_{run_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Simulation run '{run_id}' not found.")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def list_runs(self) -> List[str]:
        """Returns a list of all saved simulation run IDs."""
        return [p.name.replace("run_", "").replace(".json", "") for p in self.output_dir.glob("run_*.json")]
