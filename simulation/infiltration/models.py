"""
simulation/infiltration/models.py
---------------------------------
Concrete implementations of soil infiltration models:
1. Constant Infiltration (Infiltration rate is fixed based on saturated conductivity)
2. Green-Ampt Infiltration (Green & Ampt, 1911. Flow of air and water through soils)
3. Horton Infiltration (Horton, R.E., 1933. The role of infiltration in the hydrologic cycle)
4. SCS Curve Number Infiltration (USDA Soil Conservation Service, 1972)
"""

import numpy as np
from typing import Dict, Any

from simulation.infiltration.base import InfiltrationModel
from simulation.hydrology.runoff import calculate_scs_runoff


class ConstantInfiltration(InfiltrationModel):
    """
    Constant Infiltration model. Soil absorbs water at a fixed rate (Ks)
    independent of time, capped by surface water depth and rainfall rate.
    """
    def __init__(self, default_rate_m_s: float = 1.38e-6) -> None:  # ~5 mm/hr default
        self.rate_m_s = default_rate_m_s

    def calculate_infiltration(
        self,
        rainfall_rate_m_s: np.ndarray,
        water_depth_m: np.ndarray,
        cumulative_infiltration_m: np.ndarray,
        manning_n: np.ndarray,
        dt_seconds: float
    ) -> np.ndarray:
        # Maximum water available is water_depth_m + rainfall_rate_m_s * dt_seconds
        available_m = water_depth_m + (rainfall_rate_m_s * dt_seconds)
        potential_m = self.rate_m_s * dt_seconds
        
        # Infiltrated depth cannot exceed available surface water
        return np.minimum(potential_m, available_m).astype(np.float32)


class GreenAmptInfiltration(InfiltrationModel):
    """
    Green-Ampt Infiltration model.
    Reference: Green, W.H. and Ampt, G.A., 1911. Studies on Soil Physics.
    Equation: f = Ks * (1 + (psi + d) * d_theta / F)
    """
    def __init__(
        self,
        saturated_conductivity_ks: float = 1.38e-6,  # 5 mm/hr in m/s
        suction_head_psi: float = 0.11,               # 110 mm in m
        moisture_deficit_d_theta: float = 0.34
    ) -> None:
        self.ks = saturated_conductivity_ks
        self.psi = suction_head_psi
        self.d_theta = moisture_deficit_d_theta

    def calculate_infiltration(
        self,
        rainfall_rate_m_s: np.ndarray,
        water_depth_m: np.ndarray,
        cumulative_infiltration_m: np.ndarray,
        manning_n: np.ndarray,
        dt_seconds: float
    ) -> np.ndarray:
        available_m = water_depth_m + (rainfall_rate_m_s * dt_seconds)
        
        # Calculate infiltration rate: f = Ks * (1 + ((psi + d) * d_theta) / F)
        # Avoid division by zero when cumulative infiltration F = 0
        f_rate_m_s = np.zeros_like(available_m)
        
        mask = cumulative_infiltration_m > 0
        # If F = 0, rate is initially infinite, capped by availability
        f_rate_m_s[~mask] = self.ks * 100.0  # Safe high initial rate
        
        if np.any(mask):
            f_rate_m_s[mask] = self.ks * (
                1.0 + ((self.psi + water_depth_m[mask]) * self.d_theta) / cumulative_infiltration_m[mask]
            )

        potential_m = f_rate_m_s * dt_seconds
        return np.minimum(potential_m, available_m).astype(np.float32)


class HortonInfiltration(InfiltrationModel):
    """
    Horton Infiltration model.
    Reference: Horton, R.E., 1933. The role of infiltration in the hydrologic cycle.
    Equation: f = fc + (f0 - fc) * exp(-k * t)
    """
    def __init__(
        self,
        initial_rate_f0: float = 1.38e-5,   # 50 mm/hr in m/s
        final_rate_fc: float = 1.38e-6,     # 5 mm/hr in m/s
        decay_constant_k: float = 0.0005     # per second (approx 1.8 per hour)
    ) -> None:
        self.f0 = initial_rate_f0
        self.fc = final_rate_fc
        self.k = decay_constant_k

    def calculate_infiltration(
        self,
        rainfall_rate_m_s: np.ndarray,
        water_depth_m: np.ndarray,
        cumulative_infiltration_m: np.ndarray,
        manning_n: np.ndarray,
        dt_seconds: float
    ) -> np.ndarray:
        # Calculate elapsed time in seconds from cumulative infiltration as a proxy:
        # Since cumulative infiltration increases, we estimate decay index based on F.
        available_m = water_depth_m + (rainfall_rate_m_s * dt_seconds)
        
        # Estimate equivalent time: t = -ln((f_t - fc)/(f0 - fc))/k
        # Instead, direct proxy using Horton curve over elapsed time:
        # To avoid global tracking of time per cell, we use the average timestep clock or cumulative F.
        # Let's approximate based on cumulative infiltration volume:
        f_rate_m_s = self.fc + (self.f0 - self.fc) * np.exp(-self.k * (cumulative_infiltration_m / max(self.fc, 1e-9)))
        
        potential_m = f_rate_m_s * dt_seconds
        return np.minimum(potential_m, available_m).astype(np.float32)


class CurveNumberInfiltration(InfiltrationModel):
    """
    SCS Curve Number infiltration model mapping.
    Calculates infiltration as: Infiltration = Rainfall - Runoff.
    """
    def __init__(self, cn_value: float = 85.0) -> None:
        self.cn = cn_value

    def calculate_infiltration(
        self,
        rainfall_rate_m_s: np.ndarray,
        water_depth_m: np.ndarray,
        cumulative_infiltration_m: np.ndarray,
        manning_n: np.ndarray,
        dt_seconds: float
    ) -> np.ndarray:
        # SCS runoff operates on cumulative rainfall depths in mm
        # P = total rainfall, Q = total runoff, Infiltration = P - Q
        # For a single timestep, we estimate infiltration as a fraction of the rain
        rain_mm = rainfall_rate_m_s * dt_seconds * 1000.0
        cn_grid = np.full_like(rainfall_rate_m_s, self.cn)
        
        runoff_mm = calculate_scs_runoff(rain_mm, cn_grid)
        infil_mm = np.maximum(rain_mm - runoff_mm, 0.0)
        
        infil_m = infil_mm / 1000.0
        available_m = water_depth_m + (rainfall_rate_m_s * dt_seconds)
        return np.minimum(infil_m, available_m).astype(np.float32)
