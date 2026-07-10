"""
tests/test_hydraulic.py
-----------------------
Unit, integration, benchmark, and performance tests for Hydraulic Routing Engine (Sprint 6).
"""

import time
import numpy as np
import pytest

from simulation.hydraulic.pipe import Pipe
from simulation.hydraulic.junction import Junction
from simulation.hydraulic.state import HydraulicState, OverflowEvent, DischargeRequest
from simulation.hydraulic.routing import HydraulicRoutingEngine, KinematicRoutingStrategy
from simulation.hydraulic.benchmarks import create_hydraulic_benchmark
from simulation.core.profiler import PerformanceProfiler


class TestHydraulicModels:
    def test_pipe_geometry_and_slope(self):
        # Normal pipe
        p = Pipe("p1", length_m=100.0, diameter_m=0.3, roughness_n=0.013,
                 invert_upstream=5.0, invert_downstream=4.0, upstream_node="A", downstream_node="B")
        assert p.slope == 0.01
        
        # Flat pipe -> slope corrected to 1e-4
        p_flat = Pipe("p2", length_m=100.0, diameter_m=0.3, roughness_n=0.013,
                      invert_upstream=5.0, invert_downstream=5.0, upstream_node="A", downstream_node="B")
        assert p_flat.slope == 1e-4

        # Error cases
        with pytest.raises(ValueError):
            Pipe("err1", length_m=-10.0, diameter_m=0.3, roughness_n=0.013,
                 invert_upstream=5.0, invert_downstream=4.0, upstream_node="A", downstream_node="B")
        with pytest.raises(ValueError):
            Pipe("err2", length_m=100.0, diameter_m=0.3, roughness_n=0.013,
                 invert_upstream=5.0, invert_downstream=4.0, upstream_node="A", downstream_node="A")

    def test_junction_elevations(self):
        # Normal junction
        j = Junction("j1", ground_elevation=10.0, invert_elevation=5.0, overflow_elevation=11.0, max_storage_volume=10.0)
        assert j.ground_elevation == 10.0
        
        # Invert > Ground
        with pytest.raises(ValueError):
            Junction("err1", ground_elevation=10.0, invert_elevation=12.0, overflow_elevation=13.0)
            
        # Overflow < Ground
        with pytest.raises(ValueError):
            Junction("err2", ground_elevation=10.0, invert_elevation=5.0, overflow_elevation=9.0)


class TestHydraulicBenchmarks:
    @pytest.mark.parametrize("bench_name", [
        "single_pipe_flow",
        "junction_split",
        "pipe_capacity",
        "storage_node",
        "overflow_node",
        "dual_outfall",
        "pump_stub"
    ])
    def test_routing_benchmark_mass_conservation(self, bench_name):
        pipes, junctions, init_state, meta = create_hydraulic_benchmark(bench_name)
        
        strategy = KinematicRoutingStrategy()
        engine = HydraulicRoutingEngine(pipes, junctions, strategy)
        
        state = init_state
        inflows = meta["inflows"]
        dt = 10.0  # 10s steps
        
        # Run 30 steps to simulate propagation
        for step in range(30):
            state, report = engine.route(state, inflows, dt)
            
            # 1. Mass conservation check per step:
            # residual error must be extremely small (due to float precision, check < 1e-7)
            assert abs(report.residual_error_m3) < 1e-7
            assert abs(report.relative_error) < 1e-5
            
            # 2. Assert no negative storages or flows
            assert all(v >= 0.0 for v in state.junction_storage.values())
            assert all(v >= 0.0 for v in state.pipe_storage.values())
            assert all(v >= 0.0 for v in state.pipe_flow.values())
            
        # Benchmark-specific assertions
        if bench_name == "single_pipe_flow":
            # Flow should propagate through pipe to outfall_1
            # Check discharge request generated
            assert len(state.discharge_requests) > 0
            assert state.discharge_requests[0].requested_flow_m3_s > 0.0
            
        elif bench_name == "junction_split":
            # Flow should split symmetrically to both outfalls
            reqs = {req.outfall_id: req.requested_flow_m3_s for req in state.discharge_requests}
            assert "outfall_1" in reqs
            assert "outfall_2" in reqs
            if reqs["outfall_1"] > 0:
                assert np.allclose(reqs["outfall_1"], reqs["outfall_2"], rtol=1e-3)
                
        elif bench_name == "pipe_capacity":
            # Flow leaving pipe is capped at calculated full-flow capacity
            for f in state.pipe_flow.values():
                assert f <= meta["calculated_capacity_m3_s"] + 1e-5
                
        elif bench_name == "overflow_node":
            # Tiny junction with huge inflow must trigger overflow events
            assert len(state.overflow_events) > 0
            assert state.overflow_events[0].volume_m3 > 0.0
            assert state.overflow_events[0].junction_id == "node_1"


class TestHydraulicPerformance:
    def test_large_network_routing_performance(self):
        # Build a large network of 1000 nodes, 999 pipes
        num_nodes = 1000
        junctions = []
        pipes = []
        
        # Root outfall node
        junctions.append(Junction("outfall", ground_elevation=5.0, invert_elevation=5.0, overflow_elevation=5.0))
        
        for i in range(1, num_nodes):
            j_id = f"node_{i}"
            upstream_j_id = f"node_{i-1}" if i > 1 else "outfall"
            
            # Ground slope descends towards outfall
            j = Junction(j_id, ground_elevation=100.0 - i*0.05, invert_elevation=95.0 - i*0.05, overflow_elevation=101.0 - i*0.05)
            junctions.append(j)
            
            p = Pipe(f"pipe_{i}", length_m=50.0, diameter_m=0.3, roughness_n=0.013,
                     invert_upstream=95.0 - i*0.05, invert_downstream=95.0 - (i-1)*0.05,
                     upstream_node=j_id, downstream_node=upstream_j_id)
            pipes.append(p)
            
        # Init state
        pipe_flow = {p.pipe_id: 0.0 for p in pipes}
        pipe_storage = {p.pipe_id: 0.0 for p in pipes}
        junc_storage = {j.junction_id: 0.0 for j in junctions}
        state = HydraulicState(pipe_flow, pipe_storage, junc_storage)
        
        inflows = {f"node_{i}": 0.01 for i in range(1, num_nodes, 10)}  # scattered inflows
        
        strategy = KinematicRoutingStrategy()
        engine = HydraulicRoutingEngine(pipes, junctions, strategy)
        
        # Profile 5 advance runs
        profiler = PerformanceProfiler()
        profiler.start()
        
        for _ in range(5):
            state, report = engine.route(state, inflows, dt=10.0)
            
        perf_report = profiler.stop()
        avg_step_sec = (perf_report.execution_time_ms / 5.0) / 1000.0
        
        print(f"Large 1000-node network routed in {avg_step_sec:.4f}s per step (Limit: 0.1s)")
        assert avg_step_sec < 0.1
        assert abs(report.residual_error_m3) < 1e-5
