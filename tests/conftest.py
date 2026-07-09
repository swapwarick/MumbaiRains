"""
tests/conftest.py
------------------
Shared pytest fixtures for all test modules.
"""

import numpy as np
import pytest


@pytest.fixture
def tiny_dem() -> np.ndarray:
    """
    10×10 synthetic elevation grid for fast unit tests.
    Terrain slopes from high (NW) to low (SE) with a valley in the centre.
    """
    grid = np.array([
        [50, 45, 40, 35, 30, 25, 20, 15, 10,  5],
        [45, 40, 35, 30, 25, 20, 15, 10,  5,  2],
        [40, 35, 30, 25, 20, 15, 10,  5,  2,  1],
        [35, 30, 25,  5,  5,  5,  5,  2,  1,  1],
        [30, 25, 20,  5,  0,  0,  2,  1,  1,  1],
        [25, 20, 15,  5,  0,  0,  2,  1,  1,  1],
        [20, 15, 10,  5,  5,  5,  5,  2,  1,  1],
        [15, 10,  5,  2,  1,  1,  1,  1,  1,  1],
        [10,  5,  2,  1,  1,  1,  1,  1,  1,  1],
        [ 5,  2,  1,  1,  1,  1,  1,  1,  1,  1],
    ], dtype=np.float32)
    return grid


@pytest.fixture
def flat_dem() -> np.ndarray:
    """5×5 completely flat grid — useful for testing edge cases."""
    return np.ones((5, 5), dtype=np.float32) * 10.0


@pytest.fixture
def mock_gpkg_path(tmp_path) -> str:
    """Path to a non-existent GPKG — triggers synthetic drainage fallback."""
    return str(tmp_path / "mock.gpkg")
