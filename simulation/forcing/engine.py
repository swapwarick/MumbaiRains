"""
simulation/forcing/engine.py
----------------------------
ForcingEngine coordinating active forcing sources and injecting water to state.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional
import numpy as np

from .types import ForcingType, ForcingEventType, ForcingEvent
from .sources import ForcingSource
from .units import UnitConverter
from .reports import WaterBudgetReport


class ForcingEngine:
    """
    Coordinates external water inputs, manages source registrations, advances
    them step-by-step, and applies them to the SimulationState without in-place mutation.
    """
    def __init__(self, dx_m: float, simulation_uuid: str) -> None:
        """
        Args:
            dx_m: Isotropic grid cell size in meters.
            simulation_uuid: UUID of the current simulation run.
        """
        self.dx = float(dx_m)
        self.simulation_uuid = simulation_uuid
        self.sources: Dict[str, ForcingSource] = {}
        self.events: List[ForcingEvent] = []
        self.cumulative_added_m3 = 0.0
        self.forcing_enabled = True

        self._log_event(ForcingEventType.SIMULATION_STARTED, {"message": "Forcing framework simulation started."})

    def _log_event(self, event_type: ForcingEventType, metadata: Dict[str, Any]) -> None:
        event = ForcingEvent(
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            simulation_uuid=self.simulation_uuid,
            event_type=event_type.value,
            metadata=metadata
        )
        self.events.append(event)

    def register_source(self, source: ForcingSource) -> None:
        """Register a new forcing source."""
        self.sources[source.source_id] = source
        self._log_event(
            ForcingEventType.SOURCE_ADDED,
            {"source_id": source.source_id, "forcing_type": source.forcing_type.name}
        )

    def remove_source(self, source_id: str) -> None:
        """De-register/remove an existing forcing source."""
        if source_id in self.sources:
            src = self.sources.pop(source_id)
            self._log_event(
                ForcingEventType.SOURCE_REMOVED,
                {"source_id": source_id, "forcing_type": src.forcing_type.name}
            )

    def enable_source(self, source_id: str, enabled: bool = True) -> None:
        """Enable or disable an registered source."""
        if source_id in self.sources:
            src = self.sources[source_id]
            # Log changes
            if src.enabled != enabled:
                src.enabled = enabled
                if enabled:
                    if src.forcing_type == ForcingType.RAIN:
                        self._log_event(ForcingEventType.RAIN_STARTED, {"source_id": source_id})
                else:
                    if src.forcing_type == ForcingType.RAIN:
                        self._log_event(ForcingEventType.RAIN_STOPPED, {"source_id": source_id})

    def advance(self, state: "SimulationState", dt: float) -> Tuple["SimulationState", WaterBudgetReport]:
        """
        Advance the forcing framework by one timestep dt.
        Returns a NEW SimulationState (no in-place mutation) and a WaterBudgetReport.
        
        Args:
            state: The current SimulationState.
            dt: Timestep duration (seconds).
            
        Returns:
            updated_state: A new SimulationState with injected water.
            report: WaterBudgetReport auditing the timestep.
        """
        from simulation.core.state import SimulationState
        
        if dt <= 0:
            # Return identical state copies if dt is 0
            new_state = self._clone_state(state)
            report = WaterBudgetReport(
                timestep=state.current_timestep,
                initial_water=0.0,
                water_added=0.0,
                boundary_loss=0.0,
                current_storage=0.0,
                residual_error=0.0,
                relative_error=0.0,
                max_depth=0.0,
                min_depth=0.0
            )
            return new_state, report
            
        # 1. Clone state (Immutability guarantee)
        new_state = self._clone_state(state)
        
        rows, cols = new_state.water_depth_grid.shape
        cell_area = self.dx * self.dx
        initial_water_m3 = float(new_state.water_depth_grid.sum() * cell_area)
        
        # 2. Accumulate spatial additions from all enabled sources
        water_addition_m = np.zeros((rows, cols), dtype=np.float32)
        added_volume_m3 = 0.0
        
        if self.forcing_enabled:
            for source in self.sources.values():
                if source.enabled:
                    source_input_m = source.get_water_input(rows, cols, self.dx, dt)
                    # Protect against negative additions
                    source_input_m = np.maximum(source_input_m, 0.0)
                    water_addition_m += source_input_m
                    
            added_volume_m3 = float(water_addition_m.sum() * cell_area)
            self.cumulative_added_m3 += added_volume_m3
            
        # 3. Apply water additions
        new_state.water_depth_grid += water_addition_m
        
        # Verify no negative or NaN values
        if np.any(np.isnan(new_state.water_depth_grid)):
            raise ValueError("Forcing error: Water depth grid contains NaNs after forcing injection.")
        if np.any(new_state.water_depth_grid < 0):
            raise ValueError("Forcing error: Water depth grid contains negative values after forcing injection.")
            
        # 4. Compute WaterBudgetReport metrics
        current_storage_m3 = float(new_state.water_depth_grid.sum() * cell_area)
        boundary_loss_m3 = 0.0  # Routing boundary loss is not tracked by the ForcingEngine itself
        
        residual_error = current_storage_m3 - (initial_water_m3 + added_volume_m3 - boundary_loss_m3)
        denom = initial_water_m3 + added_volume_m3
        relative_error = residual_error / denom if denom > 0.0 else 0.0
        
        max_depth = float(new_state.water_depth_grid.max())
        min_depth = float(new_state.water_depth_grid.min())
        
        report = WaterBudgetReport(
            timestep=new_state.current_timestep,
            initial_water=initial_water_m3,
            water_added=added_volume_m3,
            boundary_loss=boundary_loss_m3,
            current_storage=current_storage_m3,
            residual_error=residual_error,
            relative_error=relative_error,
            max_depth=max_depth,
            min_depth=min_depth
        )
        
        # Update simulation state metadata (e.g., set current rainfall rate equivalent in mm/hr)
        total_area = rows * cols * cell_area
        rate_m_s = (added_volume_m3 / total_area) / dt if dt > 0 else 0.0
        new_state.current_rainfall = float(UnitConverter.m_s_to_mm_hr(rate_m_s))
        
        new_state.current_timestep += 1
        
        return new_state, report

    def _clone_state(self, state: "SimulationState") -> "SimulationState":
        from simulation.core.state import SimulationState
        rows, cols = state.water_depth_grid.shape
        new_state = SimulationState(rows, cols, state.scenario)
        new_state.current_timestep = state.current_timestep
        new_state.current_simulation_time = state.current_simulation_time
        new_state.current_rainfall = state.current_rainfall
        new_state.current_tide = state.current_tide
        new_state.status = state.status
        
        new_state.water_depth_grid = state.water_depth_grid.copy()
        new_state.velocity_x_grid = state.velocity_x_grid.copy()
        new_state.velocity_y_grid = state.velocity_y_grid.copy()
        new_state.infiltration_grid = state.infiltration_grid.copy()
        new_state.flow_direction_grid = state.flow_direction_grid.copy()
        new_state.flood_flag_grid = state.flood_flag_grid.copy()
        return new_state

    def finish(self) -> None:
        """Logs simulation finished event."""
        self._log_event(ForcingEventType.SIMULATION_FINISHED, {"message": "Forcing framework simulation completed."})
