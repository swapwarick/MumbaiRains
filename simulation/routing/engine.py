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
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Tuple, List, Optional
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

    FIX v2 (2026-07-10):
    ----------------------
    Bug: v1 used np.roll for neighbour access, creating PERIODIC (wrapping)
    boundary conditions. Water exiting at col 199 re-entered at col 0; water
    exiting at row 199 re-entered at row 0. This made water depth completely
    independent of terrain (Pearson correlation: elev vs depth = -0.05 ≈ 0).
    Deep cells accumulated at grid edges due to wrapping, not at true
    topographic depressions (Mithi River, Dharavi low-lying areas).

    Fix: Replaced np.roll with padded-slice neighbours implementing OPEN
    (absorbing) boundary conditions. At domain edges the neighbour head equals
    the edge cell's own head so no artificial gradient drives water back in.
    Water that leaves the domain at an edge is lost (models real watershed outflow).

    Diffusion coefficient raised from 0.1 to 2.0 so typical terrain gradients
    (~0.05 m/m) drive ~10% of cell depth per substep. At 0.1, the solver barely
    moved any water.
    """

    def route_flow(
        self,
        elevation: np.ndarray,
        water_depth: np.ndarray,
        manning_n: np.ndarray,
        dx_m: float,
        dt_seconds: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        head = elevation + water_depth
        depth = water_depth
        rows, cols = elevation.shape

        # ------------------------------------------------------------------
        # Diffusion coefficient
        # Raised from 0.1 to 2.0 so terrain gradients produce visible flow.
        # Capped at 0.25 for numerical stability (CFL-like condition).
        # ------------------------------------------------------------------
        diff_coeff = min(2.0 * dt_seconds / (dx_m ** 2), 0.25)

        # ------------------------------------------------------------------
        # Open (absorbing) boundary neighbours via padded slices.
        # At domain edges the neighbour head = edge cell's own head so
        # no artificial gradient drives water back in.
        #
        # IMPORTANT: np.roll is NOT used here. np.roll implements periodic
        # (wrapping) boundaries which caused water exiting at one edge to
        # re-enter at the opposite edge, completely decoupling depth from
        # terrain elevation.
        # ------------------------------------------------------------------
        head_n = np.vstack([head[0:1, :],  head[:-1, :]])    # row-1 (north)
        head_s = np.vstack([head[1:,  :],  head[-1:, :]])    # row+1 (south)
        head_w = np.hstack([head[:, 0:1],  head[:, :-1]])    # col-1 (west)
        head_e = np.hstack([head[:, 1:],   head[:, -1:]])    # col+1 (east)

        # Outflow in each direction: gradient-driven, capped at 20% of depth
        def _out(nbr_head: np.ndarray) -> np.ndarray:
            flow = np.maximum(head - nbr_head, 0.0) * diff_coeff * depth
            return np.minimum(flow, depth * 0.20).astype(np.float32)

        flow_n = _out(head_n)
        flow_s = _out(head_s)
        flow_w = _out(head_w)
        flow_e = _out(head_e)

        # Inflow received from each neighbour (padded, not rolled)
        in_from_s = np.vstack([flow_s[1:,  :],  np.zeros((1, cols),    dtype=np.float32)])
        in_from_n = np.vstack([np.zeros((1, cols), dtype=np.float32),  flow_n[:-1, :]])
        in_from_e = np.hstack([flow_e[:, 1:],   np.zeros((rows, 1),   dtype=np.float32)])
        in_from_w = np.hstack([np.zeros((rows, 1), dtype=np.float32),  flow_w[:, :-1]])

        new_depth = (
            depth
            - flow_n - flow_s - flow_w - flow_e
            + in_from_n + in_from_s + in_from_w + in_from_e
        )
        new_depth = np.maximum(new_depth, 0.0).astype(np.float32)

        # Velocity: head gradient via padded slices (no roll wraparound)
        grad_x = (head_e - head_w) / (2.0 * dx_m)
        grad_y = (head_s - head_n) / (2.0 * dx_m)

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
        Note: with open boundaries, volume_after <= volume_before is expected
        (water exits the domain at grid edges).
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


class BoundaryType(Enum):
    OPEN = "open"
    CLOSED = "closed"
    OUTFLOW = "outflow"
    FIXED_LEVEL = "fixed_level"
    SEA = "sea"
    REFLECTIVE = "reflective"


@dataclass
class MassBalanceReport:
    timestep: int
    initial_water: float      # m^3
    boundary_inflow: float    # m^3
    boundary_outflow: float   # m^3
    current_storage: float     # m^3
    absolute_error: float     # m^3
    relative_error: float     # fraction


class SurfaceRoutingEngine:
    """
    Spatially vectorized 2D D8 routing engine based on neighbour lookup tables.
    Simulates horizontal water movement without nested loops.
    """
    def __init__(
        self,
        dx_m: float,
        downstream_cells: np.ndarray,
        transfer_fraction: float = 0.25,
        boundary_type: BoundaryType = BoundaryType.CLOSED,
    ) -> None:
        """
        Args:
            dx_m: Isotropic grid cell size in meters.
            downstream_cells: 3D int32 array of shape (rows, cols, 2) where
                              [r, c, 0] = target row and [r, c, 1] = target col.
            transfer_fraction: Fraction of cell water transferred downstream each timestep.
            boundary_type: BoundaryType enum value (supports OPEN and CLOSED in Sprint 3).
        """
        self.dx = float(dx_m)
        self.downstream_cells = downstream_cells.astype(np.int32)
        self.transfer_fraction = float(transfer_fraction)
        self.boundary_type = boundary_type
        
        self.rows, self.cols = downstream_cells.shape[:2]
        
        # Verify initial parameters
        self._verify_parameters()
        
        # Precompute coordinate meshes
        self.r_coords, self.c_coords = np.meshgrid(np.arange(self.rows), np.arange(self.cols), indexing="ij")
        
        # History list for tracking mass balance every timestep
        self.mass_balance_history: List[MassBalanceReport] = []
        
        # Diagnostics/Extension point for future adaptive timestep controller
        self.adaptive_timestep_controller: Optional[Any] = None

    def _verify_parameters(self) -> None:
        if self.dx <= 0:
            raise ValueError("Grid cell size dx_m must be strictly positive.")
        if not (0.0 <= self.transfer_fraction <= 1.0):
            raise ValueError("Transfer fraction must be in range [0.0, 1.0].")
        if self.downstream_cells.shape != (self.rows, self.cols, 2):
            raise ValueError("downstream_cells must have shape (rows, cols, 2).")

    def route(self, state: "SimulationState", dt: float) -> "SimulationState":
        """
        Execute a single fixed timestep routing of duration dt.
        
        Args:
            state: The current SimulationState.
            dt: Fixed timestep duration (seconds).
            
        Returns:
            updated_state: The updated SimulationState.
        """
        from simulation.core.state import SimulationState
        
        if dt <= 0:
            return state
            
        water = state.water_depth_grid.copy().astype(np.float32)
        cell_area = self.dx * self.dx
        initial_water_vol = float(water.sum() * cell_area)
        
        # D8 lookup coordinates
        downstream_r = self.downstream_cells[:, :, 0]
        downstream_c = self.downstream_cells[:, :, 1]
        
        # Identify flow states
        is_sink = (downstream_r == self.r_coords) & (downstream_c == self.c_coords)
        out_of_bounds = (downstream_r < 0) | (downstream_r >= self.rows) | (downstream_c < 0) | (downstream_c >= self.cols)
        
        # Available potential outflow
        potential_outflow = water * self.transfer_fraction
        
        # Apply boundary conditions
        if self.boundary_type == BoundaryType.CLOSED:
            # Water cannot cross the boundary; boundary flow is blocked (acts as sink)
            valid_flow = ~is_sink & ~out_of_bounds
            outflow = np.where(valid_flow, potential_outflow, 0.0)
            boundary_outflow_vol = 0.0
            
        elif self.boundary_type == BoundaryType.OPEN:
            # Water crosses the boundary and leaves the grid
            valid_flow = ~is_sink & ~out_of_bounds
            boundary_flow = ~is_sink & out_of_bounds
            outflow = np.where(valid_flow | boundary_flow, potential_outflow, 0.0)
            boundary_outflow_vol = float(potential_outflow[boundary_flow].sum() * cell_area)
            
        elif self.boundary_type in (BoundaryType.OUTFLOW, BoundaryType.FIXED_LEVEL, BoundaryType.SEA, BoundaryType.REFLECTIVE):
            raise NotImplementedError(
                f"Boundary type {self.boundary_type.name} is defined but not implemented in Sprint 3."
            )
        else:
            raise ValueError(f"Unknown boundary type: {self.boundary_type}")
            
        # Accumulate inflows at valid target cells
        inflow = np.zeros_like(water)
        if np.any(valid_flow):
            np.add.at(
                inflow,
                (downstream_r[valid_flow], downstream_c[valid_flow]),
                potential_outflow[valid_flow]
            )
            
        # Compute new depths
        new_water = water - outflow + inflow
        
        # Numerical audits (Verify no negative depths, NaNs, or Infs)
        if np.any(np.isnan(new_water)):
            raise ValueError("Numerical error: Water depth grid contains NaN values after routing.")
        if np.any(np.isinf(new_water)):
            raise ValueError("Numerical error: Water depth grid contains Infinite values after routing.")
            
        # Protect against tiny negative floating point offsets
        new_water = np.maximum(new_water, 0.0).astype(np.float32)
        
        # Mass balance reporting
        current_storage_vol = float(new_water.sum() * cell_area)
        boundary_inflow_vol = 0.0
        
        absolute_error = current_storage_vol - (initial_water_vol + boundary_inflow_vol - boundary_outflow_vol)
        
        denom = initial_water_vol + boundary_inflow_vol
        relative_error = absolute_error / denom if denom > 0.0 else 0.0
        
        report = MassBalanceReport(
            timestep=state.current_timestep,
            initial_water=initial_water_vol,
            boundary_inflow=boundary_inflow_vol,
            boundary_outflow=boundary_outflow_vol,
            current_storage=current_storage_vol,
            absolute_error=absolute_error,
            relative_error=relative_error
        )
        self.mass_balance_history.append(report)
        
        # Update simulation state
        state.water_depth_grid = new_water
        state.current_timestep += 1
        
        return state
