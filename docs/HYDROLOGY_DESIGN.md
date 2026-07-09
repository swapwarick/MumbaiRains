# Hydrology Design Document — Mumbai Flood Digital Twin

This document details the scientific models, equations, and parameters governing rainfall infiltration and runoff calculations.

## 1. Soil Infiltration Models

The platform supports modular infiltration models using an abstract plugin design. This allows the hydrologist to swap calculations without affecting the main simulation engine.

### Constant Infiltration
Assumes soil absorbs water at a fixed rate equal to the saturated hydraulic conductivity ($K_s$) of the soil type:
$$f(t) = K_s$$

* **Applications:** Suitable for fast urban screening.
* **Manning & Permeability settings:** Set to $0$ for impervious asphalt/concrete and $1.0\text{--}5.0$ mm/hr for green spaces.

### Green-Ampt Infiltration Model
Reference: *Green, W.H. and Ampt, G.A., 1911. Studies on Soil Physics. Journal of Agricultural Science.*

Calculates infiltration rate ($f$) based on suction head at the wetting front ($\psi$), moisture deficit ($\Delta\theta$), and cumulative infiltration ($F$):
$$f(t) = K_s \left(1 + \frac{(\psi + h_0) \Delta\theta}{F(t)}\right)$$

Where:
* $K_s$: Saturated hydraulic conductivity (m/s).
* $\psi$: Soil suction head (m).
* $h_0$: Ponded surface water depth (m).
* $\Delta\theta$: Soil moisture deficit (dimensionless).
* $F(t)$: Cumulative infiltrated depth (m) up to time $t$.

### Horton Infiltration Model
Reference: *Horton, R.E., 1933. The role of infiltration in the hydrologic cycle. Transactions of the American Geophysical Union.*

Models exponential decay of infiltration capacity over time as the soil becomes saturated:
$$f(t) = f_c + (f_0 - f_c)e^{-kt}$$

Where:
* $f_0$: Initial infiltration capacity (m/s).
* $f_c$: Saturated/final infiltration capacity (m/s).
* $k$: Decay constant (1/seconds).
* $t$: Estimated cumulative time or proxy based on cumulative infiltration volume.

### SCS Curve Number Infiltration Model
Reference: *USDA Soil Conservation Service, 1972. National Engineering Handbook, Section 4: Hydrology.*

Calculates runoff $Q$ using the Curve Number, mapping the remainder as infiltration:
$$S = \frac{25400}{CN} - 254$$
$$I_a = 0.2 \times S$$
$$Q = \frac{(P - I_a)^2}{P - I_a + S}$$
$$\text{Infiltration} = P - Q$$

Where:
* $CN$: Curve Number [1, 100]. Typical Mumbai values: Concrete (85), buildings (95), short grass (60).
* $P$: Accumulated precipitation (mm).
* $Q$: Direct runoff (mm).

## 2. Manning's Roughness Coefficient (n)

Overland flow velocity is highly dependent on surface roughness. The `LandCoverEngine` maps classifications to standard roughness parameters:

| Classification | Manning's n | Runoff Coefficient | Reference |
|---|---|---|---|
| Asphalt / Roads | 0.016 | 0.90 | Chow (1959) |
| Concrete / Urban | 0.013 | 0.85 | Chow (1959) |
| Building Roofs | 0.015 | 0.95 | Chow (1959) |
| Grass / Lawns | 0.035 | 0.25 | Chow (1959) |
| Dense Forest | 0.100 | 0.10 | Chow (1959) |
| Mangrove Swamps | 0.150 | 0.05 | Coastal hydraulics |
| Open Channels | 0.025 | 1.00 | Natural streams |
