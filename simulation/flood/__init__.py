"""
simulation/flood package
------------------------
Calculates flood duration, extent, and hazard class classifications from simulation state.
"""

from .engine import FloodEngine

__all__ = ["FloodEngine"]
