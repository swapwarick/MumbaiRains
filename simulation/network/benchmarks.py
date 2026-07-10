"""
simulation/network/benchmarks.py
--------------------------------
Benchmark datasets for Hydraulic Network topology and validations.
"""

from typing import Dict, Any, Tuple
import numpy as np

from .types import NodeType, EdgeType, NetworkNode, NetworkEdge
from .engine import HydraulicNetworkEngine


def create_network_benchmark(name: str) -> Tuple[HydraulicNetworkEngine, Dict[str, Any]]:
    """
    Creates a benchmark network topology for testing and validation.
    
    Args:
        name: Name of the benchmark ("single_pipe", "junction", "blocked_pipe", 
              "dual_outfall", "river_connection", "multiple_inlets").
              
    Returns:
        engine: HydraulicNetworkEngine pre-populated with nodes and edges.
        metadata: Dict detailing expected nodes, edges, components, outfalls, dead ends.
    """
    name_lower = name.lower().strip()
    engine = HydraulicNetworkEngine()
    
    if name_lower == "single_pipe":
        # Node 1 (Inlet) -> Node 2 (Outfall)
        n1 = NetworkNode("node_1", NodeType.INLET, 0.0, 0.0, {})
        n2 = NetworkNode("node_2", NodeType.OUTFALL, 100.0, 0.0, {})
        engine.add_node(n1)
        engine.add_node(n2)
        
        e1 = NetworkEdge("pipe_1", "node_1", "node_2", EdgeType.PIPE, {})
        engine.add_edge(e1)
        
        meta = {
            "name": "single_pipe",
            "expected_nodes": 2,
            "expected_edges": 1,
            "expected_components": 1,
            "expected_outfalls": 1,
            "expected_dead_ends": 0,
            "expected_cycles": 0,
            "expected_disconnected": 0,
            "expected_unreachable": 0
        }
        return engine, meta

    elif name_lower == "junction":
        # Two inlets merge at a junction, then discharge to an outfall
        # node_1 (Inlet) \
        #                 -> node_3 (Junction) -> node_4 (Outfall)
        # node_2 (Inlet) /
        n1 = NetworkNode("node_1", NodeType.INLET, 0.0, 50.0, {})
        n2 = NetworkNode("node_2", NodeType.INLET, 0.0, -50.0, {})
        n3 = NetworkNode("node_3", NodeType.JUNCTION, 50.0, 0.0, {})
        n4 = NetworkNode("node_4", NodeType.OUTFALL, 100.0, 0.0, {})
        
        for n in [n1, n2, n3, n4]:
            engine.add_node(n)
            
        engine.add_edge(NetworkEdge("pipe_1", "node_1", "node_3", EdgeType.PIPE, {}))
        engine.add_edge(NetworkEdge("pipe_2", "node_2", "node_3", EdgeType.PIPE, {}))
        engine.add_edge(NetworkEdge("pipe_3", "node_3", "node_4", EdgeType.PIPE, {}))
        
        meta = {
            "name": "junction",
            "expected_nodes": 4,
            "expected_edges": 3,
            "expected_components": 1,
            "expected_outfalls": 1,
            "expected_dead_ends": 0,
            "expected_cycles": 0,
            "expected_disconnected": 0,
            "expected_unreachable": 0
        }
        return engine, meta

    elif name_lower == "blocked_pipe":
        # A disconnected or blocked component:
        # node_1 (Inlet) -> node_2 (Junction) (blocked pipe) -> node_3 (Outfall)
        # Actually, if the pipe is blocked, we can represent it as disconnected (no edge)
        # or we can flag the edge with metadata {"blocked": True}.
        # Let's represent it as disconnected: node_2 and node_3 have no edge connecting them.
        n1 = NetworkNode("node_1", NodeType.INLET, 0.0, 0.0, {})
        n2 = NetworkNode("node_2", NodeType.JUNCTION, 50.0, 0.0, {})
        n3 = NetworkNode("node_3", NodeType.OUTFALL, 100.0, 0.0, {})
        
        for n in [n1, n2, n3]:
            engine.add_node(n)
            
        engine.add_edge(NetworkEdge("pipe_1", "node_1", "node_2", EdgeType.PIPE, {}))
        # pipe_2 is missing (or blocked)
        
        meta = {
            "name": "blocked_pipe",
            "expected_nodes": 3,
            "expected_edges": 1,
            "expected_components": 2, # {node_1, node_2} and {node_3}
            "expected_outfalls": 1,
            "expected_dead_ends": 1,   # node_2 has out-degree 0 but is JUNC
            "expected_cycles": 0,
            "expected_disconnected": 1, # node_3 is disconnected (degree 0)
            "expected_unreachable": 2   # node_1, node_2 cannot reach outfall node_3
        }
        return engine, meta

    elif name_lower == "dual_outfall":
        # Split topology with two outfalls:
        # node_1 (Inlet) -> node_2 (Junction) -> node_3 (Outfall 1)
        #                                     -> node_4 (Outfall 2)
        n1 = NetworkNode("node_1", NodeType.INLET, 0.0, 0.0, {})
        n2 = NetworkNode("node_2", NodeType.JUNCTION, 50.0, 0.0, {})
        n3 = NetworkNode("node_3", NodeType.OUTFALL, 100.0, 20.0, {})
        n4 = NetworkNode("node_4", NodeType.OUTFALL, 100.0, -20.0, {})
        
        for n in [n1, n2, n3, n4]:
            engine.add_node(n)
            
        engine.add_edge(NetworkEdge("pipe_1", "node_1", "node_2", EdgeType.PIPE, {}))
        engine.add_edge(NetworkEdge("pipe_2", "node_2", "node_3", EdgeType.PIPE, {}))
        engine.add_edge(NetworkEdge("pipe_3", "node_2", "node_4", EdgeType.PIPE, {}))
        
        meta = {
            "name": "dual_outfall",
            "expected_nodes": 4,
            "expected_edges": 3,
            "expected_components": 1,
            "expected_outfalls": 2,
            "expected_dead_ends": 0,
            "expected_cycles": 0,
            "expected_disconnected": 0,
            "expected_unreachable": 0
        }
        return engine, meta

    elif name_lower == "river_connection":
        # Outfall connected to a river line:
        # node_1 (Inlet) -> node_2 (Outfall) -> node_3 (River Node) -> node_4 (River Outflow)
        n1 = NetworkNode("node_1", NodeType.INLET, 0.0, 0.0, {})
        n2 = NetworkNode("node_2", NodeType.OUTFALL, 50.0, 0.0, {})
        n3 = NetworkNode("node_3", NodeType.JUNCTION, 50.0, -50.0, {"type": "river"})
        n4 = NetworkNode("node_4", NodeType.OUTFALL, 100.0, -50.0, {"type": "river"})
        
        for n in [n1, n2, n3, n4]:
            engine.add_node(n)
            
        engine.add_edge(NetworkEdge("pipe_1", "node_1", "node_2", EdgeType.PIPE, {}))
        engine.add_edge(NetworkEdge("river_channel_1", "node_2", "node_3", EdgeType.RIVER, {}))
        engine.add_edge(NetworkEdge("river_channel_2", "node_3", "node_4", EdgeType.RIVER, {}))
        
        meta = {
            "name": "river_connection",
            "expected_nodes": 4,
            "expected_edges": 3,
            "expected_components": 1,
            "expected_outfalls": 2, # node_2 and node_4 are outfalls
            "expected_dead_ends": 0,
            "expected_cycles": 0,
            "expected_disconnected": 0,
            "expected_unreachable": 0
        }
        return engine, meta

    elif name_lower == "multiple_inlets":
        # Grid of 4 inlets at coordinates (10, 10), (10, 80), (80, 10), (80, 80)
        # Used for testing inlet mapping and spatial stats
        n1 = NetworkNode("inlet_1", NodeType.INLET, 10.0, 10.0, {})
        n2 = NetworkNode("inlet_2", NodeType.INLET, 10.0, 80.0, {})
        n3 = NetworkNode("inlet_3", NodeType.INLET, 80.0, 10.0, {})
        n4 = NetworkNode("inlet_4", NodeType.INLET, 80.0, 80.0, {})
        n5 = NetworkNode("outfall_1", NodeType.OUTFALL, 50.0, 50.0, {})
        
        for n in [n1, n2, n3, n4, n5]:
            engine.add_node(n)
            
        engine.add_edge(NetworkEdge("pipe_1", "inlet_1", "outfall_1", EdgeType.PIPE, {}))
        engine.add_edge(NetworkEdge("pipe_2", "inlet_2", "outfall_1", EdgeType.PIPE, {}))
        engine.add_edge(NetworkEdge("pipe_3", "inlet_3", "outfall_1", EdgeType.PIPE, {}))
        engine.add_edge(NetworkEdge("pipe_4", "inlet_4", "outfall_1", EdgeType.PIPE, {}))
        
        meta = {
            "name": "multiple_inlets",
            "expected_nodes": 5,
            "expected_edges": 4,
            "expected_components": 1,
            "expected_outfalls": 1,
            "expected_dead_ends": 0,
            "expected_cycles": 0,
            "expected_disconnected": 0,
            "expected_unreachable": 0,
            "expected_spacing": 70.0  # Spacing between adjacent inlets is exactly 70.0m
        }
        return engine, meta
        
    else:
        raise ValueError(f"Unknown network benchmark: {name}")
