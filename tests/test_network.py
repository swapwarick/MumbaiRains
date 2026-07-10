"""
tests/test_network.py
---------------------
Unit, integration, benchmark, and performance tests for Drainage Interface & Hydraulic Network (Sprint 5).
"""

import time
import numpy as np
import pytest

from simulation.drainage_interface.types import DrainInlet
from simulation.drainage_interface.engine import DrainageInterfaceEngine
from simulation.network.types import NodeType, EdgeType, NetworkNode, NetworkEdge
from simulation.network.engine import HydraulicNetworkEngine
from simulation.network.benchmarks import create_network_benchmark
from simulation.core.profiler import PerformanceProfiler


class TestDrainageInterfaceUnit:
    def test_grid_association_kdtree(self):
        # 4 inlets
        inlets = [
            DrainInlet("inlet_1", 1, 1, 5.0, 1.5, 4.5, False, "node_1"),
            DrainInlet("inlet_2", 8, 8, 3.0, 2.0, 2.5, False, "node_2")
        ]
        engine = DrainageInterfaceEngine(inlets, max_search_radius_m=30.0)
        
        # Grid settings (10x10 grid with cell size 10m)
        rows, cols = 10, 10
        transform = [10.0, 0.0, 0.0, 0.0, -10.0, 100.0]
        
        lookup = engine.associate_grid(rows, cols, transform)
        assert lookup.shape == (rows, cols)
        
        # Cell (1, 1) should be associated with inlet_1
        assert lookup[1, 1] == "inlet_1"
        # Cell (8, 8) should be associated with inlet_2
        assert lookup[8, 8] == "inlet_2"
        # Cell (0, 9) is at (90, 100), distance to (10, 90) is huge, exceeds 30m, should be empty
        assert lookup[0, 9] == ""
        
        # Check statistics
        stats = engine.get_statistics(timestep=1)
        assert stats.total_inlets == 2
        assert stats.coverage_percentage > 0.0

    def test_inlet_intake_capacities(self):
        inlets = [
            DrainInlet("inlet_1", 2, 2, 5.0, 0.1, 4.0, False, "node_1"),  # Capacity: 0.1 m3/s
            DrainInlet("inlet_2", 5, 5, 5.0, 0.2, 4.0, True, "node_2")    # Blocked!
        ]
        engine = DrainageInterfaceEngine(inlets, max_search_radius_m=50.0)
        
        rows, cols = 10, 10
        transform = [10.0, 0.0, 0.0, 0.0, -10.0, 100.0]
        engine.associate_grid(rows, cols, transform)
        
        # Set water depth: 1.0m everywhere
        water = np.full((rows, cols), 1.0, dtype=np.float32)
        cell_area = 100.0
        dt = 5.0  # seconds
        
        new_water, intake_report, overflow = engine.apply_inlet_intake(water, cell_area, dt)
        
        # inlet_1 capacity for dt is 0.1 * 5 = 0.5 m^3
        assert np.allclose(intake_report["inlet_1"], 0.5)
        # inlet_2 is blocked, intake must be 0
        assert intake_report["inlet_2"] == 0.0
        
        # Check water was drained from cells associated with inlet_1
        mask = (engine.inlet_lookup == "inlet_1")
        total_drained = float(np.sum(water[mask] - new_water[mask]) * cell_area)
        assert np.allclose(total_drained, 0.5, rtol=1e-3)


class TestHydraulicNetworkTopology:
    def test_node_edge_insertions(self):
        network = HydraulicNetworkEngine()
        
        n1 = NetworkNode("n1", NodeType.INLET, 10.0, 20.0, {"tag": "inlet_A"})
        n2 = NetworkNode("n2", NodeType.JUNCTION, 10.0, 40.0, {})
        network.add_node(n1)
        network.add_node(n2)
        
        assert network._graph.has_node("n1")
        assert network._graph.nodes["n1"]["type"] == NodeType.INLET
        
        e1 = NetworkEdge("e1", "n1", "n2", EdgeType.PIPE, {"diameter": 300})
        network.add_edge(e1)
        assert network._graph.has_edge("n1", "n2")

    def test_validation_rules(self):
        network = HydraulicNetworkEngine()
        
        # Add a node, but no edges (disconnected component)
        network.add_node(NetworkNode("n1", NodeType.INLET, 0.0, 0.0, {}))
        network.add_node(NetworkNode("n2", NodeType.JUNCTION, 0.0, 0.0, {})) # Duplicate location
        network.add_node(NetworkNode("n3", NodeType.OUTFALL, 10.0, 0.0, {}))
        
        # Self-loop edge (invalid)
        network.add_edge(NetworkEdge("e1", "n1", "n2", EdgeType.PIPE, {}))
        network._graph.add_edge("n1", "n1", id="self_loop", type=EdgeType.PIPE)
        
        # Create a cycle: n2 -> n3 -> n2
        network.add_edge(NetworkEdge("e2", "n2", "n3", EdgeType.PIPE, {}))
        network.add_edge(NetworkEdge("e3", "n3", "n2", EdgeType.PIPE, {}))
        
        val = network.validate_topology(tolerance_m=0.001)
        
        # Cycles detected
        assert len(val["cycles"]) > 0
        # Duplicate location detected
        assert len(val["duplicate_nodes"]) > 0
        # Invalid edges (self loops) detected
        assert len(val["invalid_edges"]) > 0


class TestHydraulicBenchmarks:
    @pytest.mark.parametrize("bench_name", [
        "single_pipe",
        "junction",
        "blocked_pipe",
        "dual_outfall",
        "river_connection",
        "multiple_inlets"
    ])
    def test_benchmark_statistics_and_topology(self, bench_name):
        network, meta = create_network_benchmark(bench_name)
        
        # Gather statistics
        report = network.generate_report()
        
        # Verify node/edge count expectations
        assert report.node_count == meta["expected_nodes"]
        assert report.edge_count == meta["expected_edges"]
        assert report.connected_components == meta["expected_components"]
        assert report.outfalls == meta["expected_outfalls"]
        assert report.dead_ends == meta["expected_dead_ends"]
        
        # Validation checks
        errors = network.validate_topology()
        assert len(errors["cycles"]) == meta["expected_cycles"]
        assert len(errors["disconnected_nodes"]) == meta["expected_disconnected"]
        assert len(errors["unreachable_nodes"]) == meta["expected_unreachable"]
        
        if bench_name == "multiple_inlets":
            assert np.allclose(report.average_inlet_spacing, meta["expected_spacing"])


class TestHydraulicPerformance:
    @pytest.mark.parametrize("size,limit_sec", [
        (100, 0.05),
        (500, 0.30),
        (1000, 1.0)
    ])
    def test_grid_association_performance(self, size, limit_sec):
        # 10 inlets spaced out
        inlets = [
            DrainInlet(f"inlet_{i}", i * (size // 10), i * (size // 10), 5.0, 1.0, 4.0, False, f"node_{i}")
            for i in range(10)
        ]
        engine = DrainageInterfaceEngine(inlets, max_search_radius_m=100.0)
        
        transform = [10.0, 0.0, 0.0, 0.0, -10.0, 100.0]
        
        profiler = PerformanceProfiler()
        profiler.start()
        
        lookup = engine.associate_grid(size, size, transform)
        
        report = profiler.stop()
        elapsed_sec = report.execution_time_ms / 1000.0
        
        print(f"Grid {size}x{size} mapped in {elapsed_sec:.4f}s (Limit: {limit_sec}s)")
        assert elapsed_sec < limit_sec
        assert lookup.shape == (size, size)
