"""
simulation/gis/provenance.py
----------------------------
ProvenanceContext — implements stateless processing lineages for scientific auditability.
Each simulation context owns its own provenance logs, dataset versions, and error tracing.
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Dict, Any, List, Optional


@dataclass
class AuditRecord:
    """
    Structured audit log for a single spatial geoprocessing operation.
    """
    operation: str
    input_datasets: List[str]
    output_datasets: List[str]
    duration_ms: float
    tool_version: str
    parameters: Dict[str, Any]
    result: str
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ProvenanceContext:
    """
    Stateless log container tracking lineage and metadata for a specific simulation run.
    No global shared state.
    """
    def __init__(
        self,
        simulation_id: str,
        configuration: Optional[Dict[str, Any]] = None,
        dataset_versions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Initializes a unique ProvenanceContext.
        """
        self.simulation_id: str = simulation_id
        self.timestamp: str = datetime.now().isoformat()
        self.dataset_versions: Dict[str, str] = dataset_versions or {}
        self.configuration: Dict[str, Any] = configuration or {}
        self.processing_history: List[AuditRecord] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.export_history: List[str] = []

    def record_operation(
        self,
        operation: str,
        input_datasets: List[str],
        output_datasets: List[str],
        duration_ms: float,
        tool_version: str,
        parameters: Dict[str, Any],
        result: str,
        warnings: Optional[List[str]] = None,
        errors: Optional[List[str]] = None
    ) -> AuditRecord:
        """
        Adds a structured audit log of a geoprocessing operation to this simulation history.
        """
        rec = AuditRecord(
            operation=operation,
            input_datasets=input_datasets,
            output_datasets=output_datasets,
            duration_ms=duration_ms,
            tool_version=tool_version,
            parameters=parameters,
            result=result,
            warnings=warnings or [],
            errors=errors or []
        )
        self.processing_history.append(rec)
        return rec

    def add_warning(self, message: str) -> None:
        """Logs a warning to the simulation context."""
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """Logs an error to the simulation context."""
        self.errors.append(message)

    def log_export(self, export_path: str) -> None:
        """Logs an export file creation to the context."""
        self.export_history.append(export_path)

    def export_json(self) -> str:
        """
        Serializes this ProvenanceContext into a JSON string.
        """
        return json.dumps({
            "simulation_id": self.simulation_id,
            "timestamp": self.timestamp,
            "dataset_versions": self.dataset_versions,
            "configuration": self.configuration,
            "warnings": self.warnings,
            "errors": self.errors,
            "export_history": self.export_history,
            "processing_history": [
                {
                    "operation": r.operation,
                    "input_datasets": r.input_datasets,
                    "output_datasets": r.output_datasets,
                    "duration_ms": r.duration_ms,
                    "tool_version": r.tool_version,
                    "parameters": r.parameters,
                    "result": r.result,
                    "warnings": r.warnings,
                    "errors": r.errors
                }
                for r in self.processing_history
            ]
        }, indent=2)
