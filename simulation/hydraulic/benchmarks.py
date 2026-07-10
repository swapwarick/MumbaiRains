"""
simulation/hydraulic/benchmarks.py
----------------------------------
Benchmark scenarios for sub-surface hydraulic network flow routing (Sprint 6).
"""

from typing import List, Tuple, Dict, Any

from .pipe import Pipe
from .junction import Junction
from .state import HydraulicState


def create_hydraulic_benchmark(name: str) -> Tuple[List[Pipe], List[Junction], HydraulicState, Dict[str, Any]]:
    """
    Creates a benchmark drainage network with configured pipes and junctions,
    initial state, and validation expectations.
    
    Args:
        name: Benchmark identifier.
        
    Returns:
        pipes: List of Pipe objects.
        junctions: List of Junction objects.
        initial_state: Pre-populated HydraulicState.
        metadata: Expectations dictionary.
    """
    name_lower = name.lower().strip()
    
    if name_lower == "single_pipe_flow":
        # node_1 (Inlet) -> pipe_1 -> outfall_1 (Outfall)
        j1 = Junction("node_1", ground_elevation=10.0, invert_elevation=5.0, overflow_elevation=11.0, max_storage_volume=10.0)
        j2 = Junction("outfall_1", ground_elevation=4.0, invert_elevation=4.0, overflow_elevation=4.0, max_storage_volume=1.0)
        
        p1 = Pipe("pipe_1", length_m=100.0, diameter_m=0.3, roughness_n=0.013, 
                  invert_upstream=5.0, invert_downstream=4.0, upstream_node="node_1", downstream_node="outfall_1")
                  
        state = HydraulicState(
            pipe_flow={"pipe_1": 0.0},
            pipe_storage={"pipe_1": 0.0},
            junction_storage={"node_1": 0.0, "outfall_1": 0.0}
        )
        
        meta = {
            "name": "single_pipe_flow",
            "inflows": {"node_1": 0.05},  # 0.05 m3/s constant inflow
            "outfalls": ["outfall_1"],
            "expected_steady_state_flow": 0.05
        }
        return [p1], [j1, j2], state, meta

    elif name_lower == "junction_split":
        # node_1 (Inlet) -> pipe_1 -> node_2 (Junction) -> pipe_2 -> outfall_1
        #                                               -> pipe_3 -> outfall_2
        j1 = Junction("node_1", ground_elevation=10.0, invert_elevation=8.0, overflow_elevation=11.0, max_storage_volume=10.0)
        j2 = Junction("node_2", ground_elevation=7.0, invert_elevation=6.0, overflow_elevation=8.0, max_storage_volume=10.0)
        j3 = Junction("outfall_1", ground_elevation=5.0, invert_elevation=5.0, overflow_elevation=5.0, max_storage_volume=1.0)
        j4 = Junction("outfall_2", ground_elevation=5.0, invert_elevation=5.0, overflow_elevation=5.0, max_storage_volume=1.0)
        
        p1 = Pipe("pipe_1", 100.0, 0.5, 0.013, 8.0, 6.0, "node_1", "node_2")
        p2 = Pipe("pipe_2", 50.0, 0.3, 0.013, 6.0, 5.0, "node_2", "outfall_1")
        p3 = Pipe("pipe_3", 50.0, 0.3, 0.013, 6.0, 5.0, "node_2", "outfall_2")
        
        state = HydraulicState(
            pipe_flow={"pipe_1": 0.0, "pipe_2": 0.0, "pipe_3": 0.0},
            pipe_storage={"pipe_1": 0.0, "pipe_2": 0.0, "pipe_3": 0.0},
            junction_storage={"node_1": 0.0, "node_2": 0.0, "outfall_1": 0.0, "outfall_2": 0.0}
        )
        
        meta = {
            "name": "junction_split",
            "inflows": {"node_1": 0.10},  # 0.10 m3/s total inflow
            "outfalls": ["outfall_1", "outfall_2"],
            "expected_split_ratio": 0.5   # symmetric split (0.05 each outfall)
        }
        return [p1, p2, p3], [j1, j2, j3, j4], state, meta

    elif name_lower == "pipe_capacity":
        # Throttled inlet flow: node_1 -> pipe_1 (tiny diameter) -> outfall_1
        j1 = Junction("node_1", 10.0, 8.0, 11.0, 5.0)
        j2 = Junction("outfall_1", 5.0, 5.0, 5.0, 1.0)
        
        # Diameter 0.1m, slope 0.03, roughness 0.015
        p1 = Pipe("pipe_1", 100.0, 0.1, 0.015, 8.0, 5.0, "node_1", "outfall_1")
        
        state = HydraulicState(
            pipe_flow={"pipe_1": 0.0},
            pipe_storage={"pipe_1": 0.0},
            junction_storage={"node_1": 0.0, "outfall_1": 0.0}
        )
        
        import math
        # Calculate full flow capacity of p1 analytically:
        d = 0.1
        r = d / 4.0
        area = 3.14159 * (d**2) / 4.0
        v = (1.0 / 0.015) * (r ** (2.0/3.0)) * math.sqrt(0.03)
        q_cap = v * area
        
        meta = {
            "name": "pipe_capacity",
            "inflows": {"node_1": 0.50},  # inflow rate is huge, far exceeds pipe capacity
            "outfalls": ["outfall_1"],
            "calculated_capacity_m3_s": q_cap
        }
        return [p1], [j1, j2], state, meta

    elif name_lower == "storage_node":
        # Large storage junction acts as a detention reservoir
        j1 = Junction("node_1", ground_elevation=10.0, invert_elevation=5.0, overflow_elevation=12.0, max_storage_volume=500.0)
        j2 = Junction("outfall_1", ground_elevation=4.0, invert_elevation=4.0, overflow_elevation=4.0, max_storage_volume=1.0)
        
        p1 = Pipe("pipe_1", 200.0, 0.3, 0.013, 5.0, 4.0, "node_1", "outfall_1")
        
        state = HydraulicState(
            pipe_flow={"pipe_1": 0.0},
            pipe_storage={"pipe_1": 0.0},
            junction_storage={"node_1": 0.0, "outfall_1": 0.0}
        )
        
        meta = {
            "name": "storage_node",
            "inflows": {"node_1": 0.20},  # moderate inflow
            "outfalls": ["outfall_1"],
            "expected_delay_minutes": 5.0
        }
        return [p1], [j1, j2], state, meta

    elif name_lower == "overflow_node":
        # Tiny storage junction that spills excess flow immediately
        j1 = Junction("node_1", 10.0, 9.0, 10.0, 1.0)  # max_storage_volume = 1.0 m3
        j2 = Junction("outfall_1", 5.0, 5.0, 5.0, 1.0)
        
        p1 = Pipe("pipe_1", 100.0, 0.2, 0.02, 9.0, 5.0, "node_1", "outfall_1")
        
        state = HydraulicState(
            pipe_flow={"pipe_1": 0.0},
            pipe_storage={"pipe_1": 0.0},
            junction_storage={"node_1": 0.0, "outfall_1": 0.0}
        )
        
        meta = {
            "name": "overflow_node",
            "inflows": {"node_1": 0.80},  # massive inflow will trigger overflow
            "outfalls": ["outfall_1"]
        }
        return [p1], [j1, j2], state, meta

    elif name_lower == "dual_outfall":
        # Parallel outfalls connected to the same junction:
        # node_1 -> pipe_1 -> outfall_1
        #        -> pipe_2 -> outfall_2
        j1 = Junction("node_1", 10.0, 6.0, 11.0, 10.0)
        j2 = Junction("outfall_1", 5.0, 5.0, 5.0, 1.0)
        j3 = Junction("outfall_2", 5.0, 5.0, 5.0, 1.0)
        
        p1 = Pipe("pipe_1", 100.0, 0.3, 0.013, 6.0, 5.0, "node_1", "outfall_1")
        p2 = Pipe("pipe_2", 100.0, 0.3, 0.013, 6.0, 5.0, "node_1", "outfall_2")
        
        state = HydraulicState(
            pipe_flow={"pipe_1": 0.0, "pipe_2": 0.0},
            pipe_storage={"pipe_1": 0.0, "pipe_2": 0.0},
            junction_storage={"node_1": 0.0, "outfall_1": 0.0, "outfall_2": 0.0}
        )
        
        meta = {
            "name": "dual_outfall",
            "inflows": {"node_1": 0.15},
            "outfalls": ["outfall_1", "outfall_2"]
        }
        return [p1, p2], [j1, j2, j3], state, meta

    elif name_lower == "pump_stub":
        # node_1 (Inlet) -> pipe_1 -> pump_station (Junc) -> pipe_2 -> outfall_1
        j1 = Junction("node_1", 10.0, 8.0, 11.0, 10.0)
        j2 = Junction("pump_station", 8.0, 4.0, 9.0, 20.0)
        j3 = Junction("outfall_1", 5.0, 5.0, 5.0, 1.0)
        
        p1 = Pipe("pipe_1", 100.0, 0.3, 0.013, 8.0, 4.0, "node_1", "pump_station")
        p2 = Pipe("pipe_2", 100.0, 0.3, 0.013, 4.0, 5.0, "pump_station", "outfall_1")
        
        state = HydraulicState(
            pipe_flow={"pipe_1": 0.0, "pipe_2": 0.0},
            pipe_storage={"pipe_1": 0.0, "pipe_2": 0.0},
            junction_storage={"node_1": 0.0, "pump_station": 0.0, "outfall_1": 0.0}
        )
        
        meta = {
            "name": "pump_stub",
            "inflows": {"node_1": 0.06},
            "outfalls": ["outfall_1"]
        }
        return [p1, p2], [j1, j2, j3], state, meta
        
    else:
        raise ValueError(f"Unknown hydraulic benchmark: {name}")
