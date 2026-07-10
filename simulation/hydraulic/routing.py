"""
simulation/hydraulic/routing.py
------------------------------
HydraulicRoutingEngine and RoutingStrategy interface for kinematic routing.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

from .pipe import Pipe
from .junction import Junction
from .state import HydraulicState, OverflowEvent, DischargeRequest
from .reports import HydraulicReport


class RoutingStrategy(ABC):
    """
    Abstract interface for hydraulic network routing solvers.
    Allows swappable strategies (Kinematic, Diffusive, Saint-Venant)
    without redesigning the engine.
    """
    
    @abstractmethod
    def route_step(
        self,
        pipes: Dict[str, Pipe],
        junctions: Dict[str, Junction],
        state: HydraulicState,
        inflows: Dict[str, float],
        dt: float,
        current_time_seconds: float
    ) -> Tuple[HydraulicState, float]:
        """
        Computes flow and storage updates for one timestep.
        Does NOT directly remove outfall water (creates requests).
        
        Returns:
            new_state: Updated instantaneous HydraulicState.
            added_water_m3: Water volume injected from inlets.
        """
        pass


class KinematicRoutingStrategy(RoutingStrategy):
    """
    Deterministic Kinematic Routing strategy for sub-surface network flow.
    Computes capacity via Manning's equation, translates water using convective
    travel delays, and enforces mass conservation.
    """
    
    def route_step(
        self,
        pipes: Dict[str, Pipe],
        junctions: Dict[str, Junction],
        state: HydraulicState,
        inflows: Dict[str, float],
        dt: float,
        current_time_seconds: float
    ) -> Tuple[HydraulicState, float]:
        
        # 1. Initialize new state variables
        new_pipe_storage = state.pipe_storage.copy()
        new_pipe_flow = state.pipe_flow.copy()
        new_junc_storage = state.junction_storage.copy()
        overflow_events: List[OverflowEvent] = []
        discharge_requests: List[DischargeRequest] = []
        
        # 2. Inject external inflows into junction storages
        added_water_m3 = 0.0
        for j_id, inflow_rate in inflows.items():
            if j_id in new_junc_storage:
                vol_in = inflow_rate * dt
                new_junc_storage[j_id] += vol_in
                added_water_m3 += vol_in

        # 3. Compute outflows from pipe storage (convective translation)
        # Travel time delay tau = L / V. Released volume = S_pipe * min(1.0, dt/tau)
        pipe_outflows_vol: Dict[str, float] = {}
        for p_id, pipe in pipes.items():
            s_pipe = state.pipe_storage.get(p_id, 0.0)
            
            # Compute Manning full flow velocity
            d = pipe.diameter
            r = d / 4.0  # hydraulic radius for circular full pipe
            area = np.pi * (d ** 2) / 4.0
            
            # Manning velocity V = (1/n) * R^(2/3) * S^(1/2)
            v_manning = (1.0 / pipe.roughness) * (r ** (2.0 / 3.0)) * np.sqrt(pipe.slope)
            v_actual = max(v_manning, 0.1)  # minimum velocity to prevent static locking
            
            tau = pipe.length / v_actual
            
            # Released volume from pipe
            v_out = s_pipe * min(1.0, dt / tau)
            pipe_outflows_vol[p_id] = v_out
            new_pipe_flow[p_id] = v_out / dt if dt > 0 else 0.0

        # 4. Compute inflows into pipes from upstream junctions
        # Group pipes by their upstream node to allocate junction water proportionally
        nodes_with_outgoing_pipes: Dict[str, List[str]] = {}
        for p_id, pipe in pipes.items():
            nodes_with_outgoing_pipes.setdefault(pipe.upstream_node, []).append(p_id)
            
        pipe_inflows_vol: Dict[str, float] = {}
        
        for j_id, outgoing_pids in nodes_with_outgoing_pipes.items():
            s_junc = new_junc_storage.get(j_id, 0.0)
            if s_junc <= 0:
                for p_id in outgoing_pids:
                    pipe_inflows_vol[p_id] = 0.0
                continue
                
            # Calculate potential draw volume for each outgoing pipe (capped by Manning full-flow capacity)
            potential_draws: Dict[str, float] = {}
            for p_id in outgoing_pids:
                pipe = pipes[p_id]
                d = pipe.diameter
                area = np.pi * (d ** 2) / 4.0
                v_manning = (1.0 / pipe.roughness) * ((d / 4.0) ** (2.0 / 3.0)) * np.sqrt(pipe.slope)
                v_actual = max(v_manning, 0.1)
                q_full = v_actual * area
                
                potential_draws[p_id] = q_full * dt
                
            total_potential_draw = sum(potential_draws.values())
            
            # Proportional allocation if total draw exceeds available storage
            if total_potential_draw > s_junc:
                for p_id in outgoing_pids:
                    fraction = potential_draws[p_id] / total_potential_draw if total_potential_draw > 0 else 0.0
                    pipe_inflows_vol[p_id] = s_junc * fraction
            else:
                for p_id in outgoing_pids:
                    pipe_inflows_vol[p_id] = potential_draws[p_id]
                    
            # Subtract inflows from upstream junction storage
            for p_id in outgoing_pids:
                new_junc_storage[j_id] -= pipe_inflows_vol[p_id]

        # 5. Move water out of pipes and into downstream junctions
        for p_id, pipe in pipes.items():
            v_out = pipe_outflows_vol.get(p_id, 0.0)
            if pipe.downstream_node in new_junc_storage:
                new_junc_storage[pipe.downstream_node] += v_out

        # 6. Update pipe storage
        for p_id in pipes:
            v_in = pipe_inflows_vol.get(p_id, 0.0)
            v_out = pipe_outflows_vol.get(p_id, 0.0)
            new_pipe_storage[p_id] = max(0.0, state.pipe_storage.get(p_id, 0.0) + v_in - v_out)

        # 7. Generate outfall discharge requests (do not remove water directly)
        for j_id, junc in junctions.items():
            if junc.ground_elevation == 0.0 and junc.overflow_elevation == 0.0:
                # Labeled as outfall in benchmark meta, or check NodeType.OUTFALL
                # Since Junction class does not store NodeType directly, we can check max_storage_volume = 0
                # or label outfalls via metadata or design: outfalls have ground_elevation = invert_elevation.
                # Let's check if the junction represents a system outfall.
                # In our benchmarks, outfall junctions are explicitly configured.
                # We can store a node_type or flag in the junction. Let's use metadata or invert/ground elevation.
                # Actually, let's check if junction_id has "outfall" in it, or if it has ground_elevation == invert_elevation.
                pass

        # Since we want to determine outfalls cleanly, let's identify outfalls by:
        # - Any junction where invert_elevation == ground_elevation (often outfalls in simplified models)
        # - Or if it has ground_elevation == 0.0 (dummy outfalls)
        # To be precise, let's inspect the junction details from the network graph!
        # In a directed network graph, outfalls are nodes of type NodeType.OUTFALL.
        # So we can pass a set of outfall node IDs, or check:
        for j_id, junc in junctions.items():
            # If the junction acts as an outfall:
            # Let's assume outfalls are junctions whose max_storage_volume is very small (e.g. 0.0 or <= 1e-3)
            # or which are explicitly tagged. Let's add an is_outfall check:
            is_outfall = (junc.ground_elevation == junc.invert_elevation) or ("outfall" in j_id.lower())
            
            if is_outfall:
                vol_avail = new_junc_storage.get(j_id, 0.0)
                if vol_avail > 0:
                    req_flow = vol_avail / dt if dt > 0 else 0.0
                    discharge_requests.append(DischargeRequest(
                        outfall_id=j_id,
                        requested_flow_m3_s=req_flow,
                        elevation=junc.invert_elevation
                    ))
                    # Note: We do NOT subtract the volume from new_junc_storage here!
                    # The engine will subtract it after verifying boundary conditions (TideEngine).

        # 8. Generate overflow events for junctions exceeding max capacity
        for j_id, junc in junctions.items():
            # Skip outfall nodes (their overflow is handled via outfall discharge requests)
            is_outfall = (junc.ground_elevation == junc.invert_elevation) or ("outfall" in j_id.lower())
            if is_outfall:
                continue
                
            s_junc = new_junc_storage.get(j_id, 0.0)
            if s_junc > junc.max_storage_volume:
                v_over = s_junc - junc.max_storage_volume
                overflow_events.append(OverflowEvent(
                    junction_id=j_id,
                    volume_m3=v_over,
                    elevation=junc.overflow_elevation,
                    timestamp_seconds=current_time_seconds
                ))
                new_junc_storage[j_id] = junc.max_storage_volume

        # Protect against tiny negative values
        for j_id in new_junc_storage:
            new_junc_storage[j_id] = max(0.0, new_junc_storage[j_id])

        # Return updated state
        new_state = HydraulicState(
            pipe_flow=new_pipe_flow,
            pipe_storage=new_pipe_storage,
            junction_storage=new_junc_storage,
            overflow_events=overflow_events,
            discharge_requests=discharge_requests
        )
        
        return new_state, added_water_m3


class HydraulicRoutingEngine:
    """
    Manages the overall hydraulic network simulation, delegates calculations
    to a RoutingStrategy, and maintains cumulative mass budgets.
    """
    def __init__(self, pipes: List[Pipe], junctions: List[Junction], strategy: RoutingStrategy) -> None:
        self.pipes = {p.pipe_id: p for p in pipes}
        self.junctions = {j.junction_id: j for j in junctions}
        self.strategy = strategy
        
        # Cumulative accounts
        self.cumulative_inflow_m3 = 0.0
        self.cumulative_outflow_m3 = 0.0
        self.cumulative_overflow_m3 = 0.0
        self.cumulative_boundary_loss_m3 = 0.0
        
        self.current_time_seconds = 0.0

    def route(self, state: HydraulicState, inflows: Dict[str, float], dt: float) -> Tuple[HydraulicState, HydraulicReport]:
        """
        Advance hydraulic network simulation by dt seconds.
        
        Returns:
            updated_state: Instantaneous state copy.
            report: HydraulicReport detailing mass conservation.
        """
        if dt <= 0:
            # Return identical report if dt is zero
            storage_m3 = sum(state.junction_storage.values()) + sum(state.pipe_storage.values())
            report = HydraulicReport(
                timestep=0,
                initial_water_m3=storage_m3,
                water_added_m3=0.0,
                boundary_loss_m3=0.0,
                current_storage_m3=storage_m3,
                residual_error_m3=0.0,
                relative_error=0.0,
                cumulative_inflow_m3=self.cumulative_inflow_m3,
                cumulative_outflow_m3=self.cumulative_outflow_m3,
                cumulative_overflow_m3=self.cumulative_overflow_m3,
                cumulative_boundary_loss_m3=self.cumulative_boundary_loss_m3
            )
            return state, report

        # Calculate initial total storage (junctions + pipes)
        initial_storage = sum(state.junction_storage.get(j_id, 0.0) for j_id in self.junctions) + \
                          sum(state.pipe_storage.get(p_id, 0.0) for p_id in self.pipes)

        # 1. Advance routing strategy
        new_state, added_water = self.strategy.route_step(
            pipes=self.pipes,
            junctions=self.junctions,
            state=state,
            inflows=inflows,
            dt=dt,
            current_time_seconds=self.current_time_seconds
        )
        
        # 2. Process Outfall Discharge Requests (100% accepted in Sprint 6)
        boundary_outflow_vol = 0.0
        for req in new_state.discharge_requests:
            v_out = req.requested_flow_m3_s * dt
            # Evacuate water from outfall storage
            new_state.junction_storage[req.outfall_id] = max(0.0, new_state.junction_storage[req.outfall_id] - v_out)
            boundary_outflow_vol += v_out

        # 3. Process Overflow Events
        boundary_overflow_vol = sum(evt.volume_m3 for evt in new_state.overflow_events)

        # 4. Update cumulative statistics
        self.cumulative_inflow_m3 += added_water
        self.cumulative_outflow_m3 += boundary_outflow_vol
        self.cumulative_overflow_m3 += boundary_overflow_vol
        
        step_boundary_loss = boundary_outflow_vol + boundary_overflow_vol
        self.cumulative_boundary_loss_m3 += step_boundary_loss

        # Calculate final total storage
        final_storage = sum(new_state.junction_storage.get(j_id, 0.0) for j_id in self.junctions) + \
                        sum(new_state.pipe_storage.get(p_id, 0.0) for p_id in self.pipes)

        # 5. Compute Mass Balance metrics
        residual = final_storage - (initial_storage + added_water - step_boundary_loss)
        denom = initial_storage + added_water
        rel_err = residual / denom if denom > 0.0 else 0.0

        report = HydraulicReport(
            timestep=len(new_state.overflow_events) + 1,  # nominal timestep ID
            initial_water_m3=initial_storage,
            water_added_m3=added_water,
            boundary_loss_m3=step_boundary_loss,
            current_storage_m3=final_storage,
            residual_error_m3=residual,
            relative_error=rel_err,
            cumulative_inflow_m3=self.cumulative_inflow_m3,
            cumulative_outflow_m3=self.cumulative_outflow_m3,
            cumulative_overflow_m3=self.cumulative_overflow_m3,
            cumulative_boundary_loss_m3=self.cumulative_boundary_loss_m3
        )

        self.current_time_seconds += dt
        
        return new_state, report
