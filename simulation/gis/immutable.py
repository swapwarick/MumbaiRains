"""
simulation/gis/immutable.py
---------------------------
Implements ImmutableDataset wrappers to prevent in-place modifications
and enforce parent-child lineage tracking for geoprocessing steps.
"""

from typing import List, Optional, Any
from simulation.gis.layers import BaseLayer


class ImmutableDataset:
    """
    Wrapper for spatial layers enforcing immutability and parent-child tracking.
    Original layers wrapped inside this class cannot be overwritten directly.
    """
    def __init__(
        self,
        layer: BaseLayer,
        parent: Optional["ImmutableDataset"] = None,
        lineage_operation: Optional[str] = None
    ) -> None:
        """
        Initializes an immutable wrapper.
        """
        self._layer: BaseLayer = layer
        self._parent: Optional[ImmutableDataset] = parent
        self._lineage_operation: Optional[str] = lineage_operation
        self._children: List[ImmutableDataset] = []

        if parent:
            parent._add_child(self)

    @property
    def layer(self) -> BaseLayer:
        """Returns the read-only layer instance."""
        return self._layer

    @property
    def parent(self) -> Optional["ImmutableDataset"]:
        """Returns the parent dataset that this dataset was derived from."""
        return self._parent

    @property
    def lineage_operation(self) -> Optional[str]:
        """Returns the geoprocessing operation used to derive this dataset."""
        return self._lineage_operation

    @property
    def children(self) -> List["ImmutableDataset"]:
        """Returns list of derived child datasets."""
        return list(self._children)

    def derive(self, derived_layer: BaseLayer, operation_name: str) -> "ImmutableDataset":
        """
        Derives a new immutable dataset from the current one.
        Ensures parents cannot be mutated or overwritten by geoprocessing steps.

        Args:
            derived_layer: The resulting processed layer.
            operation_name: Name of the geoprocessing step (e.g. 'Clipping', 'Slope').

        Returns:
            A new child ImmutableDataset.
        """
        return ImmutableDataset(
            layer=derived_layer,
            parent=self,
            lineage_operation=operation_name
        )

    def _add_child(self, child: "ImmutableDataset") -> None:
        self._children.append(child)

    def get_lineage_path(self) -> List[str]:
        """
        Traces back the parent hierarchy and returns a list of operations
        leading to this dataset.
        """
        path = []
        curr = self
        while curr is not None:
            if curr.lineage_operation:
                path.append(f"{curr.layer.name} ({curr.lineage_operation})")
            else:
                path.append(f"{curr.layer.name} (Source)")
            curr = curr.parent
        return list(reversed(path))
