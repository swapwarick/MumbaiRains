# Hydraulic Network — Architectural & Topological Specifications

This document outlines the directed graph architecture, data models, loading pipeline, and validation rules of the `HydraulicNetworkEngine` (Sprint 5).

---

## 1. Directed Graph Architecture

The Hydraulic Network is modeled as a **Directed Graph** ($G = (V, E)$) using the Python `networkx` library. Coordinates and physical attributes are stored as node and edge properties.

```
       [INLET Node 1] \
                       -> [JUNCTION Node 3] -> [PIPE Edge 3] -> [OUTFALL Node 4]
       [INLET Node 2] /
```

Topology is decoupled from specific physical dimensions and hydraulics. The graph focuses strictly on connectivity, routing directions, and topological consistency.

---

## 2. Public API Specification

### `HydraulicNetworkEngine`
* `__init__()`: Initializes an empty directed graph (`DiGraph`).
* `add_node(node: NetworkNode) -> None`: Adds a node with `type` (NodeType), `x`, `y`, and metadata.
* `add_edge(edge: NetworkEdge) -> None`: Adds a directed edge between two existing nodes with `type` (EdgeType) and metadata.
* `load_from_geojson(feature_collection: Dict[str, Any]) -> None`: Parses LineStrings (edges + vertices) and Points (nodes) from GeoJSON format.
* `load_from_gpkg(gpkg_path: str, layers: List[str]) -> None`: Queries layers from a SQLite GeoPackage, converting geometries to nodes and edges.
* `validate_topology(tolerance_m: float = 0.001) -> Dict[str, Any]`: Run audits to find disconnected components, cycles, duplicate nodes, invalid edges, and unreachable nodes.
* `generate_report(coverage_pct: float, avg_spacing_m: float) -> NetworkReport`: Compiles graph metrics (nodes, edges, components, cycles, spacing) into a serializable report.

### Enums & Data Models:
* **`NodeType`**: `INLET`, `JUNCTION`, `PUMP`, `OUTFALL`, `STORAGE`.
* **`EdgeType`**: `PIPE` (Underground conduit), `NULLAH` (Open drain), `RIVER` (River channel).

---

## 3. Topology Validation Audits

To ensure numerical stability in future hydraulic routing, the engine validates:
1. **Disconnected Nodes**: Identifies nodes that have no incoming or outgoing connections (degree = 0).
2. **Duplicate Nodes**: Flag nodes that are located within `tolerance_m` (default 1mm) of each other.
3. **Cycles**: Detects directed loops using NetworkX simple cycles.
4. **Missing Outfalls**: Checks if at least one node is designated as `NodeType.OUTFALL`.
5. **Unreachable Nodes**: Identifies any node that cannot reach a designated outfall by traversing the directed graph. Calculated in linear time $\mathcal{O}(V + E)$ by reversing the graph and performing a breadth-first search from all outfalls.
6. **Duplicate Inlet Assignments**: Flags duplicate inlets sharing the same coordinate space.

---

## 4. Known Limitations
* **Connectivity Gaps in OSM**: OpenStreetMap datasets often contain disconnected segments due to missing survey data. Validation reports will flag these as warnings.
* **No Hydraulic Calculations**: This module does not solve flow routing, water levels, or backwater effects; it is strictly a topological connectivity model.
