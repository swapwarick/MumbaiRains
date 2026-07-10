"""
simulation/checkpoints/manager.py
---------------------------------
CheckpointManager for saving, loading, and resuming simulation states.
"""

import pickle
import random
from typing import Dict, Any, Optional
import numpy as np

from backend.utils import get_logger
from backend.config import settings

logger = get_logger(__name__)

class CheckpointManager:
    """
    Handles serialisation and deserialisation of simulation checkpoints.
    Supports complete state preservation (state grids, hydraulic pipes/junctions,
    simulation clock, manifests, random seeds, and mass balance histories).
    """

    @staticmethod
    def save_checkpoint(
        filepath: str,
        state: Any,
        hydraulic_state: Optional[Any],
        clock: Any,
        manifest: Dict[str, Any],
        mass_balance_history: Any,
        current_step: int,
        seed: Optional[int] = None
    ) -> None:
        """
        Saves all simulation state parameters to a pickle checkpoint file.
        """
        checkpoint_data = {
            "state": state,
            "hydraulic_state": hydraulic_state,
            "clock": clock,
            "manifest": manifest,
            "mass_balance_history": mass_balance_history,
            "current_step": current_step,
            "seed": seed or 42,
            "numpy_random_state": np.random.get_state(),
            "python_random_state": random.getstate()
        }
        
        try:
            with open(filepath, "wb") as f:
                pickle.dump(checkpoint_data, f)
            logger.info("Simulation checkpoint saved successfully", extra={"path": filepath, "step": current_step})
        except Exception as exc:
            logger.error(f"Failed to save simulation checkpoint: {exc}", extra={"path": filepath})
            raise exc

    @staticmethod
    def load_checkpoint(filepath: str) -> Dict[str, Any]:
        """
        Loads checkpoint data from a file.
        """
        try:
            with open(filepath, "rb") as f:
                checkpoint_data = pickle.load(f)
            logger.info("Simulation checkpoint loaded successfully", extra={"path": filepath, "step": checkpoint_data.get("current_step")})
            return checkpoint_data
        except Exception as exc:
            logger.error(f"Failed to load simulation checkpoint: {exc}", extra={"path": filepath})
            raise exc

    @classmethod
    def resume(cls, controller: Any, filepath: str) -> None:
        """
        Resumes simulation progress by applying checkpoint data back onto a controller.
        """
        data = cls.load_checkpoint(filepath)
        
        # Apply states back to controller
        controller.state = data["state"]
        controller.hydraulic_state = data["hydraulic_state"]
        controller.clock = data["clock"]
        controller.state.current_timestep = data["current_step"]
        
        # Restore random states for reproducibility
        if data.get("numpy_random_state") is not None:
            np.random.set_state(data["numpy_random_state"])
        if data.get("python_random_state") is not None:
            random.setstate(data["python_random_state"])
            
        # Restore mass balance histories if engines are present
        if hasattr(controller, "routing") and controller.routing is not None:
            # Check if flow routing has history
            if hasattr(controller.routing, "mass_balance_history"):
                controller.routing.mass_balance_history = data["mass_balance_history"].get("surface", [])
        if hasattr(controller, "hydraulic_routing") and controller.hydraulic_routing is not None:
            # For hydraulic engine
            if hasattr(controller.hydraulic_routing, "cumulative_inflow_m3"):
                hist = data["mass_balance_history"].get("hydraulic", {})
                controller.hydraulic_routing.cumulative_inflow_m3 = hist.get("cumulative_inflow_m3", 0.0)
                controller.hydraulic_routing.cumulative_outflow_m3 = hist.get("cumulative_outflow_m3", 0.0)
                controller.hydraulic_routing.cumulative_overflow_m3 = hist.get("cumulative_overflow_m3", 0.0)
                controller.hydraulic_routing.cumulative_boundary_loss_m3 = hist.get("cumulative_boundary_loss_m3", 0.0)
                
        logger.info("Simulation resumed from checkpoint", extra={"step": data["current_step"]})
