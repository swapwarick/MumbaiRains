"""
simulation/surface/landcover.py
-------------------------------
LandCoverEngine mapping land cover classifications to hydraulic parameters.
References Manning's roughness coefficients from Chow (1959) "Open-Channel Hydraulics".
Infiltration parameters based on USDA NRCS National Engineering Handbook Section 4.
"""

from typing import Dict, Any
from backend.utils import get_logger

logger = get_logger(__name__)


class LandCoverEngine:
    """
    Translates land cover classification codes into physical hydraulic parameters:
    Manning's roughness coefficient (n), runoff coefficients, and soil permeability parameters.
    """
    
    # Manning's n and runoff coefficients registry
    # Reference: Chow, V.T., 1959. Open-channel hydraulics. McGraw-Hill, New York.
    LAND_COVER_REGISTRY: Dict[str, Dict[str, Any]] = {
        "roads": {
            "manning_n": 0.016,          # Asphalt/concrete pavement (Chow 1959)
            "runoff_coefficient": 0.90,  # Highly impervious surface
            "infiltration_model": "constant",
            "saturated_conductivity_ks": 0.0,  # Completely impermeable
            "suction_head_psi": 0.0
        },
        "buildings": {
            "manning_n": 0.015,          # Concrete/slate roof structures
            "runoff_coefficient": 0.95,  # Max imperviousness
            "infiltration_model": "constant",
            "saturated_conductivity_ks": 0.0,
            "suction_head_psi": 0.0
        },
        "concrete": {
            "manning_n": 0.013,          # Smooth concrete pavement
            "runoff_coefficient": 0.85,
            "infiltration_model": "constant",
            "saturated_conductivity_ks": 0.0,
            "suction_head_psi": 0.0
        },
        "grass": {
            "manning_n": 0.035,          # Short grass / lawn cover
            "runoff_coefficient": 0.25,  # Moderately pervious
            "infiltration_model": "horton",
            "saturated_conductivity_ks": 5.0,  # mm/hr (representative)
            "suction_head_psi": 110.0
        },
        "forest": {
            "manning_n": 0.100,          # Dense timberland with underbrush
            "runoff_coefficient": 0.10,  # High interception
            "infiltration_model": "green_ampt",
            "saturated_conductivity_ks": 12.0,  # mm/hr
            "suction_head_psi": 200.0
        },
        "mangroves": {
            "manning_n": 0.150,          # High resistance coastal mangrove swamps
            "runoff_coefficient": 0.05,
            "infiltration_model": "constant",
            "saturated_conductivity_ks": 1.0,
            "suction_head_psi": 50.0
        },
        "water": {
            "manning_n": 0.025,          # Natural river channel (Mithi river)
            "runoff_coefficient": 1.00,  # Immediate saturation
            "infiltration_model": "constant",
            "saturated_conductivity_ks": 0.0,
            "suction_head_psi": 0.0
        }
    }

    def get_parameters(self, land_cover_type: str) -> Dict[str, Any]:
        """
        Retrieves Manning's n, runoff coefficient, and infiltration parameters for a classification.

        Args:
            land_cover_type: Name of the classification (e.g. roads, grass, water).

        Returns:
            Dictionary containing manning_n, runoff_coefficient, infiltration_model,
            saturated_conductivity_ks, and suction_head_psi.
        """
        lc = land_cover_type.lower().strip()
        if lc not in self.LAND_COVER_REGISTRY:
            logger.debug(f"Land cover '{lc}' not in registry. Defaulting to concrete parameters.")
            return self.LAND_COVER_REGISTRY["concrete"]
        return self.LAND_COVER_REGISTRY[lc]

    def get_manning_n(self, land_cover_type: str) -> float:
        """Retrieves only the Manning's roughness coefficient (n)."""
        return float(self.get_parameters(land_cover_type)["manning_n"])

    def get_runoff_coefficient(self, land_cover_type: str) -> float:
        """Retrieves only the runoff coefficient."""
        return float(self.get_parameters(land_cover_type)["runoff_coefficient"])
