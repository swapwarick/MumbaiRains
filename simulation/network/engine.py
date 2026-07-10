"""
simulation/network/engine.py
---------------------------
HydraulicNetworkEngine managing drainage graph connectivity and validation.
"""

from typing import List, Dict, Any, Tuple, Set, Optional
import numpy as np
import networkx as nx

from .types import NodeType, EdgeType, NetworkNode, NetworkEdge, NetworkReport
from backend.database.repositories.gis import GISRepository


class HydraulicNetworkEngine:
    """
    Manages the topological representation of the sub-surface drainage network.
    Constructs the directed graph using NetworkX, parses GIS layers, and performs validations.
    """
    def __init__(self) -> None:
        # Directed graph internally representing the network
        self._graph = nx.DiGraph()

    def add_node(self, node: NetworkNode) -> None:
        """Adds a node to the network."""
        self._graph.add_node(
            node.node_id,
            type=node.node_type,
            x=float(node.x),
            y=float(node.y),
            metadata=node.metadata or {}
        )

    def add_edge(self, edge: NetworkEdge) -> None:
        """Adds a directed edge to the network."""
        # Ensure start and end nodes exist
        if not self._graph.has_node(edge.from_node):
            raise ValueError(f"Edge start node '{edge.from_node}' does not exist.")
        if not self._graph.has_node(edge.to_node):
            raise ValueError(f"Edge end node '{edge.to_node}' does not exist.")
            
        self._graph.add_edge(
            edge.from_node,
            edge.to_node,
            id=edge.edge_id,
            type=edge.edge_type,
            metadata=edge.metadata or {}
        )

    def load_from_geojson(self, feature_collection: Dict[str, Any]) -> None:
        """
        Parses a GeoJSON FeatureCollection into nodes and edges.
        
        Args:
            feature_collection: Dictionary representing GeoJSON.
        """
        features = feature_collection.get("features", [])
        
        for idx, feat in enumerate(features):
            geom = feat.get("geometry", {})
            props = feat.get("properties", {})
            g_type = geom.get("type", "")
            
            # Map type to EdgeType or NodeType
            feat_type_str = props.get("type", "").lower()
            
            if g_type == "LineString":
                coords = geom.get("coordinates", [])
                node_ids = []
                
                # 1. Create nodes for all coordinates
                for x, y in coords:
                    n_id = f"node_{x:.6f}_{y:.6f}"
                    node_ids.append(n_id)
                    if not self._graph.has_node(n_id):
                        n_type = NodeType.JUNCTION
                        if "inlet" in feat_type_str:
                            n_type = NodeType.INLET
                        elif "outfall" in feat_type_str:
                            n_type = NodeType.OUTFALL
                            
                        self.add_node(NetworkNode(
                            node_id=n_id,
                            node_type=n_type,
                            x=x,
                            y=y,
                            metadata={"source": "geojson_linestring"}
                        ))
                        
                # 2. Add edges between adjacent coordinates
                e_type = EdgeType.PIPE
                if "river" in feat_type_str:
                    e_type = EdgeType.RIVER
                elif "nullah" in feat_type_str or "canal" in feat_type_str:
                    e_type = EdgeType.NULLAH
                    
                for i in range(len(node_ids) - 1):
                    from_node = node_ids[i]
                    to_node = node_ids[i+1]
                    edge_id = f"edge_{from_node}_{to_node}_{idx}"
                    self.add_edge(NetworkEdge(
                        edge_id=edge_id,
                        from_node=from_node,
                        to_node=to_node,
                        edge_type=e_type,
                        metadata=props
                    ))
                    
            elif g_type == "Point":
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    x, y = coords[0], coords[1]
                    n_id = props.get("id") or f"node_{x:.6f}_{y:.6f}"
                    
                    n_type = NodeType.JUNCTION
                    if "inlet" in feat_type_str or props.get("node_type") == "inlet":
                        n_type = NodeType.INLET
                    elif "outfall" in feat_type_str or props.get("node_type") == "outfall":
                        n_type = NodeType.OUTFALL
                    elif "pump" in feat_type_str or props.get("node_type") == "pump":
                        n_type = NodeType.PUMP
                    elif "storage" in feat_type_str or props.get("node_type") == "storage":
                        n_type = NodeType.STORAGE
                        
                    self.add_node(NetworkNode(
                        node_id=n_id,
                        node_type=n_type,
                        x=x,
                        y=y,
                        metadata=props
                    ))

    def load_from_gpkg(self, gpkg_path: str, layers: List[str]) -> None:
        """
        Loads vector layers from a SQLite GeoPackage into the network.
        
        Args:
            gpkg_path: Path to the GeoPackage file.
            layers: List of layer names to load (e.g. ["waterways", "roads"]).
        """
        repo = GISRepository(gpkg_path)
        for layer in layers:
            geojson = repo.load_vector_layer(layer)
            self.load_from_geojson(geojson)

    def validate_topology(self, tolerance_m: float = 0.001) -> Dict[str, Any]:
        """
        Validates graph topology to identify errors before routing.
        
        Returns:
            report: Dict of validation errors and warnings.
        """
        # A. Disconnected nodes (degree = 0)
        disconnected = [
            node for node, deg in self._graph.degree()
            if deg == 0
        ]
        
        # B. Duplicate nodes (nodes closer than tolerance)
        nodes = list(self._graph.nodes(data=True))
        duplicates = []
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                n1_id, n1_data = nodes[i]
                n2_id, n2_data = nodes[j]
                d = np.sqrt((n1_data["x"] - n2_data["x"])**2 + (n1_data["y"] - n2_data["y"])**2)
                if d <= tolerance_m:
                    duplicates.append((n1_id, n2_id, d))
                    
        # C. Cycles
        cycles = list(nx.simple_cycles(self._graph))
        
        # D. Outfalls (nodes designated as outfall or sink nodes with positive in-degree)
        outfalls = []
        sinks_not_labeled = []
        for node, data in self._graph.nodes(data=True):
            is_labeled_outfall = (data.get("type") == NodeType.OUTFALL)
            in_deg = self._graph.in_degree(node)
            out_deg = self._graph.out_degree(node)
            
            if is_labeled_outfall:
                outfalls.append(node)
            elif out_deg == 0 and in_deg > 0:
                sinks_not_labeled.append(node)
                
        # E. Unreachable nodes (nodes that have no path to any outfall)
        targets = set(outfalls) if outfalls else set(sinks_not_labeled)
        unreachable = []
        if targets:
            rev_g = self._graph.reverse(copy=True)
            reachable = set()
            for t in targets:
                reachable.update(nx.descendants(rev_g, t))
                reachable.add(t)
            unreachable = list(set(self._graph.nodes) - reachable)
        else:
            # If no outfalls, all nodes are technically unreachable
            unreachable = list(self._graph.nodes)

        # F. Invalid edges (self loops or empty IDs)
        invalid_edges = []
        for u, v, data in self._graph.edges(data=True):
            if u == v:
                invalid_edges.append((u, v, "Self-loop edge"))
                
        # G. Duplicate inlet assignments (same coordinates or too close)
        inlet_nodes = [
            (node, data)
            for node, data in self._graph.nodes(data=True)
            if data.get("type") == NodeType.INLET
        ]
        duplicate_inlets = []
        for i in range(len(inlet_nodes)):
            for j in range(i + 1, len(inlet_nodes)):
                n1_id, n1_data = inlet_nodes[i]
                n2_id, n2_data = inlet_nodes[j]
                d = np.sqrt((n1_data["x"] - n2_data["x"])**2 + (n1_data["y"] - n2_data["y"])**2)
                if d <= tolerance_m:
                    duplicate_inlets.append((n1_id, n2_id, d))
                    
        return {
            "disconnected_nodes": disconnected,
            "duplicate_nodes": duplicates,
            "cycles": cycles,
            "outfalls": outfalls,
            "missing_outfalls": len(outfalls) == 0,
            "unlabeled_sinks": sinks_not_labeled,
            "unreachable_nodes": unreachable,
            "invalid_edges": invalid_edges,
            "duplicate_inlets": duplicate_inlets
        }

    def generate_report(self, coverage_pct: float = 0.0, avg_spacing_m: float = 0.0) -> NetworkReport:
        """
        Gathers topological statistics into a NetworkReport.
        """
        node_count = self._graph.number_of_nodes()
        edge_count = self._graph.number_of_edges()
        connected_components = nx.number_weakly_connected_components(self._graph)
        
        # Outfalls
        outfalls = sum(1 for _, data in self._graph.nodes(data=True) if data.get("type") == NodeType.OUTFALL)
        # Dead ends (out_degree = 0, excluding outfalls)
        dead_ends = sum(
            1 for node in self._graph.nodes
            if self._graph.out_degree(node) == 0 and self._graph.nodes[node].get("type") != NodeType.OUTFALL
        )
        
        cycles = len(list(nx.simple_cycles(self._graph)))
        inlet_count = sum(1 for _, data in self._graph.nodes(data=True) if data.get("type") == NodeType.INLET)
        
        # Calculate inlet spacing if not passed explicitly
        if avg_spacing_m == 0.0 and inlet_count >= 2:
            inlet_coords = np.array([
                [data["x"], data["y"]]
                for _, data in self._graph.nodes(data=True)
                if data.get("type") == NodeType.INLET
            ])
            avg_spacing_m = self._calculate_avg_spacing(inlet_coords)
            
        return NetworkReport(
            node_count=node_count,
            edge_count=edge_count,
            connected_components=connected_components,
            outfalls=outfalls,
            dead_ends=dead_ends,
            cycles=cycles,
            inlet_count=inlet_count,
            average_inlet_spacing=avg_spacing_m,
            coverage_percentage=coverage_pct
        )

    def _calculate_avg_spacing(self, coords: np.ndarray) -> float:
        if len(coords) < 2:
            return 0.0
        try:
            from scipy.spatial import KDTree
            tree = KDTree(coords)
            dist, _ = tree.query(coords, k=2)
            return float(np.mean(dist[:, 1]))
        except ImportError:
            diff = coords[:, None, :] - coords[None, :, :]
            dists = np.sqrt(np.sum(diff ** 2, axis=2))
            np.fill_diagonal(dists, np.inf)
            return float(np.mean(np.min(dists, axis=1)))
