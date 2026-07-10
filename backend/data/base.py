"""
backend/data/base.py
--------------------
DataProvider abstraction base interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class DataProvider(ABC):
    """
    Abstract Base Class for Data Providers.
    Ensures simulation controllers never access files or databases directly.
    """
    @abstractmethod
    def get_data(self, key: str, **kwargs) -> Any:
        """Retrieve data by key with optional query arguments."""
        pass
