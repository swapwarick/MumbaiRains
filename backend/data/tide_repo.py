"""
backend/data/tide_repo.py
-------------------------
TideRepository stub.
"""

from typing import Dict, Any, List

class TideRepository:
    """
    Repository stub for historical tide level measurements and predictions.
    """
    def __init__(self, data_path: str = "") -> None:
        self.data_path = data_path

    def get_tide_observations(self) -> List[Dict[str, Any]]:
        """Return list of tide observations."""
        return []
