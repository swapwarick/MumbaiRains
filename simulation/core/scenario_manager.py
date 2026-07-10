"""
simulation/core/scenario_manager.py
-----------------------------------
ScenarioManager configures simulation states and boundaries to simulate specific scenarios:
1. Historical Scenario (e.g. July 2005 deluge)
2. Synthetic Scenario (design storm profiles)
3. Blocked Drain Scenario (simulates storm network clogging)
4. High Tide Scenario (spring tide tidal surge)
5. Extreme Rainfall Scenario (cloudburst / extreme weather)
"""

from typing import Dict, Any, Optional
from backend.utils import get_logger

logger = get_logger(__name__)


class Scenario:
    """
    Data container representing a simulation scenario configuration.
    """
    def __init__(
        self,
        name: str,
        rainfall_intensity_mm_hr: float,
        rainfall_duration_hours: float,
        rainfall_mode: str,
        mean_sea_level_m: float = 0.0,
        tidal_range_m: float = 4.5,
        storm_surge_m: float = 0.0,
        drainage_clogging_factor: float = 0.0,  # 0.0 = clear drains, 1.0 = 100% blocked
        description: str = ""
    ) -> None:
        self.name = name
        self.rainfall_intensity = rainfall_intensity_mm_hr
        self.rainfall_duration = rainfall_duration_hours
        self.rainfall_mode = rainfall_mode
        self.msl = mean_sea_level_m
        self.tidal_range = tidal_range_m
        self.surge = storm_surge_m
        self.clogging_factor = drainage_clogging_factor
        self.description = description


class HistoricalRainfallScenario(Scenario):
    """
    Scenario that loads custom observed/historical rainfall records from a file (Task 4).
    """
    def __init__(
        self,
        name: str,
        rainfall_time_series: list[float],
        rainfall_depth_series: list[float],
        mean_sea_level_m: float = 0.0,
        tidal_range_m: float = 4.5,
        storm_surge_m: float = 0.0,
        drainage_clogging_factor: float = 0.0,
        description: str = ""
    ) -> None:
        self.rainfall_time_series = rainfall_time_series
        self.rainfall_depth_series = rainfall_depth_series
        
        # Determine duration from time series
        duration_hours = max(rainfall_time_series) / 60.0 if rainfall_time_series else 1.0
        # Determine average intensity
        total_rain = sum(rainfall_depth_series)
        avg_intensity = total_rain / duration_hours if duration_hours > 0 else 0.0

        super().__init__(
            name=name,
            rainfall_intensity_mm_hr=avg_intensity,
            rainfall_duration_hours=duration_hours,
            rainfall_mode="historical",
            mean_sea_level_m=mean_sea_level_m,
            tidal_range_m=tidal_range_m,
            storm_surge_m=storm_surge_m,
            drainage_clogging_factor=drainage_clogging_factor,
            description=description
        )



class ScenarioManager:
    """
    Manages and configures predefined simulation scenarios.
    """
    def __init__(self) -> None:
        self.scenarios: Dict[str, Scenario] = {}
        self._register_default_scenarios()

    def get_scenario(self, name: str) -> Scenario:
        """
        Retrieves a scenario configuration by name.

        Args:
            name: Name of the scenario.

        Returns:
            The Scenario instance.
        """
        key = name.lower().strip()
        if key not in self.scenarios:
            logger.warning(f"Scenario '{name}' not found. Defaulting to synthetic scenario.")
            return self.scenarios["synthetic"]
        return self.scenarios[key]

    def _register_default_scenarios(self) -> None:
        """Registers default scenarios based on Mumbai flood risk profiles."""
        
        # 1. Historical Scenario: July 2005 Mumbai Deluge (944 mm in 24 hours)
        self.scenarios["historical_2005"] = Scenario(
            name="historical_2005",
            rainfall_intensity_mm_hr=39.3,   # Average rate over peak hours
            rainfall_duration_hours=24.0,
            rainfall_mode="synthetic",        # ABM profile
            mean_sea_level_m=0.5,
            tidal_range_m=4.8,               # High spring tide
            storm_surge_m=0.8,               # Estimated cyclonic storm surge
            drainage_clogging_factor=0.2,    # Standard clogging rate
            description="Re-enactment of the catastrophic 26 July 2005 flood event."
        )

        # 2. Standard Synthetic Scenario
        self.scenarios["synthetic"] = Scenario(
            name="synthetic",
            rainfall_intensity_mm_hr=30.0,
            rainfall_duration_hours=4.0,
            rainfall_mode="constant",
            mean_sea_level_m=0.0,
            tidal_range_m=4.5,
            storm_surge_m=0.0,
            drainage_clogging_factor=0.0,
            description="Standard synthetic rainstorm profile."
        )

        # 3. Blocked Drain Scenario (Heavy drainage system clogging)
        self.scenarios["blocked_drain"] = Scenario(
            name="blocked_drain",
            rainfall_intensity_mm_hr=50.0,
            rainfall_duration_hours=4.0,
            rainfall_mode="constant",
            mean_sea_level_m=0.0,
            tidal_range_m=4.5,
            storm_surge_m=0.0,
            drainage_clogging_factor=0.8,    # 80% drain network capacity blocked
            description="Simulates storm drain clogging by plastic waste and siltation."
        )

        # 4. High Tide / Backwater Scenario
        self.scenarios["high_tide"] = Scenario(
            name="high_tide",
            rainfall_intensity_mm_hr=40.0,
            rainfall_duration_hours=6.0,
            rainfall_mode="constant",
            mean_sea_level_m=0.5,
            tidal_range_m=5.2,               # Extreme spring tide
            storm_surge_m=1.2,               # High storm surge
            drainage_clogging_factor=0.1,
            description="Simulates extreme tidal backwater effects blocking river outlets."
        )

        # 5. Extreme Rainfall / Cloudburst Scenario
        self.scenarios["extreme_rainfall"] = Scenario(
            name="extreme_rainfall",
            rainfall_intensity_mm_hr=120.0,  # 120 mm/hr extreme intensity
            rainfall_duration_hours=2.0,
            rainfall_mode="synthetic",
            mean_sea_level_m=0.0,
            tidal_range_m=4.5,
            storm_surge_m=0.0,
            drainage_clogging_factor=0.3,
            description="Simulates a localized cloudburst / extreme convective precipitation event."
        )
