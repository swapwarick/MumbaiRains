"""
backend/data/rainfall_repo.py
----------------------------
RainfallRepository for loading custom observed and historical rainfall records.
"""

from typing import List, Tuple, Dict, Any
import csv
import os

from backend.config import settings
from backend.exceptions import RainfallException

class RainfallRepository:
    """
    Repository for rainfall time-series data.
    """
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.join(str(settings.project_root), "data", "rainfall")
        os.makedirs(self.data_dir, exist_ok=True)

    def load_rainfall_csv(self, filename: str) -> Tuple[List[float], List[float]]:
        """
        Loads time series from a CSV file containing time_min, rainfall_mm columns.
        Returns (time_min_list, rainfall_mm_list).
        """
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            raise RainfallException(f"Rainfall profile file not found: {filepath}")

        time_series = []
        rain_series = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    time_series.append(float(row["time_min"]))
                    rain_series.append(float(row["rainfall_mm"]))
            return time_series, rain_series
        except Exception as exc:
            raise RainfallException(f"Failed to parse rainfall CSV at {filepath}: {exc}") from exc
