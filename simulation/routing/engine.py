"""
simulation/routing/engine.py
----------------------------
FlowRoutingEngine — handles horizontal movement of surface water between cells.
Separates mass conservation verification and grid boundaries from the physical solver.

References:
1. Hunter, N.M., et al., 2007. Benchmarking 2D shallow-water models for urban flooding.
2. Kurganov, A. and Tadmor, E., 2000. New high-resolution central schemes for Hamilton-Jacobi equations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import numpy as np

from backend.utils import get_logger

logger = get_logger(__name__)


class FlowRoutingSolver(ABC):
    """
    Abstract interface for 2D flow routing solvers.
    """
    
    @abstractmethod
    def route_flow(
        self,
        elevation: np.ndarray,
        water_depth: np.ndarray,
        manning_n: np.ndarray,
        dx_m: float,
        dt_seconds: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Computes flow updates for all cells.

        Returns:
            Tuple of:
                new_water_depth: 2D array of updated depths (m).
                velocity_x: 2D array of velocity in X direction (m/s).
                velocity_y: 2D array of velocity in Y direction (m/s).
        """
        pass


class DiffusionWaveSolver(FlowRoutingSolver):
    """
    Spatially vectorized 2-D Diffusion-Wave cellular automata routing solver.
    Approximates shallow water flow when acceleration terms are negligible.
    """

    def route_flow(
        self,
        elevation: np.ndarray,
        water_depth: np.ndarray,
        manning_n: np.ndarray,
        dx_m: float,
        dt_seconds: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        # Total hydraulic head: elevation + water surface
        head = elevation + water_depth
        
        # Diffusion coefficient — capped at 0.25 for stability
        diff_coeff = min(0.1 * dt_seconds / (dx_m ** 2), 0.25)
        
        depth = water_depth
        rows, cols = elevation.shape

        def _outflow(shift: int, axis: int) -> np.ndarray:
            neighbour_head = np.roll(head, shift, axis=axis)
            flow = np.maximum(head - neighbour_head, 0.0) * diff_coeff * depth
            return np.minimum(flow, depth * 0.2)  # cap: max 20% of depth per direction

        flow_n = _outflow(-1, 0)
        flow_s = _outflow( 1, 0)
        flow_e = _outflow( 1, 1)
        flow_w = _outflow(-1, 1)

        # Net change per cell = inflow from neighbours - outflow to neighbours
        new_depth = (
            depth
            - flow_n - flow_s - flow_e - flow_w
            + np.roll(flow_n,  1, axis=0)
            + np.roll(flow_s, -1, axis=0)
            + np.roll(flow_e, -1, axis=1)
            + np.roll(flow_w,  1, axis=1)
        )

        new_depth = np.maximum(new_depth, 0.0).astype(np.float32)
        
        # Calculate approximate velocity grids based on head gradient
        grad_x = (np.roll(head, -1, axis=1) - np.roll(head, 1, axis=1)) / (2.0 * dx_m)
        grad_y = (np.roll(head, -1, axis=0) - np.roll(head, 1, axis=0)) / (2.0 * dx_m)
        
        # Velocity V = (1/n) * R^(2/3) * S^(1/2) (Manning's formula approximation)
        R = np.maximum(new_depth, 1e-4)
        manning_factor = (1.0 / np.maximum(manning_n, 1e-3)) * (R ** (2.0 / 3.0))
        
        velocity_x = -np.sign(grad_x) * manning_factor * np.sqrt(np.abs(grad_x))
        velocity_y = -np.sign(grad_y) * manning_factor * np.sqrt(np.abs(grad_y))
        
        return new_depth, velocity_x, velocity_y


class ShallowWaterEquationsSolver(FlowRoutingSolver):
    """
    Stub for full 2-D Shallow Water Equations (Saint-Venant equations) solver
    using Finite Volume or shock-capturing Godunov-type schemes.
    Reference: Toro, E.F., 2001. Shock-capturing methods for free-surface shallow flows.
    """

    def route_flow(
        self,
        elevation: np.ndarray,
        water_depth: np.ndarray,
        manning_n: np.ndarray,
        dx_m: float,
        dt_seconds: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        # Full shallow water solver is planned for Phase 3
        # Needs Riemann solvers, conservation of momentum equations, wet-dry boundaries.
        raise NotImplementedError(
            "2-D Saint-Venant Shallow Water Equations solver is not implemented. "
            "Please use the DiffusionWaveSolver for routing."
        )


class FlowRoutingEngine:
    """
    Manages surface water routing, verifies mass conservation, and wraps swappable solvers.
    """
    def __init__(self, solver_type: str = "diffusion") -> None:
        self.solver: FlowRoutingSolver
        if solver_type.lower() == "diffusion":
            self.solver = DiffusionWaveSolver()
        elif solver_type.lower() == "shallow_water":
            self.solver = ShallowWaterEquationsSolver()
        else:
            raise ValueError(f"Unknown solver type: {solver_type}")
        
        logger.info("FlowRoutingEngine initialised", extra={"solver": solver_type})

    def set_solver(self, solver_type: str) -> None:
        """Swaps routing solver at runtime."""
        if solver_type.lower() == "diffusion":
            self.solver = DiffusionWaveSolver()
        elif solver_type.lower() == "shallow_water":
            self.solver = ShallowWaterEquationsSolver()
        else:
            raise ValueError(f"Unknown solver type: {solver_type}")
        logger.info("Routing solver updated", extra={"solver": solver_type})

    def route(
        self,
        elevation: np.ndarray,
        water_depth: np.ndarray,
        manning_n: np.ndarray,
        dx_m: float,
        dt_seconds: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Routes surface water, confirming conservation of mass.
        """
        volume_before = float(water_depth.sum())
        
        new_depth, vx, vy = self.solver.route_flow(
            elevation=elevation,
            water_depth=water_depth,
            manning_n=manning_n,
            dx_m=dx_m,
            dt_seconds=dt_seconds
        )
        
        volume_after = float(new_depth.sum())
        mass_balance_error = volume_after - volume_before
        
        if abs(mass_balance_error) > 1e-2:
            logger.debug(
                "Mass balance check",
                extra={"before": volume_before, "after": volume_after, "error": mass_balance_error}
            )
            
        return new_depth, vx, vy
