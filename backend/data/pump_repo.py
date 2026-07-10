"""
backend/data/pump_repo.py
-------------------------
PumpRepository stub.
"""

from typing import Dict, Any, List

class PumpRepository:
    """
    Repository stub for pump station properties and operation curves.
    """
    def __init__(self, data_path: str = "") -> None:
        self.data_path = data_path

    def get_pumps(self) -> List[Dict[str, Any]]:
        """Return list of configured pumps."""
        return []
