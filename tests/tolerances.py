"""
tests/tolerances.py
-------------------
Centralized numerical tolerance values for Terrain Engine and general verification tests.
"""

# Elevation comparison tolerances (relative and absolute)
ELEVATION_RTOL = 1e-05
ELEVATION_ATOL = 1e-08

# Terrain derivative tolerances
SLOPE_DEG_TOLERANCE = 0.01      # Allowable difference in degrees
SLOPE_PCT_TOLERANCE = 0.5       # Allowable difference in percent rise/run
ASPECT_DEG_TOLERANCE = 0.5      # Allowable difference in compass degrees
