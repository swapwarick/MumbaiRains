# Hydrological Modeling Reference — Mumbai Flood Digital Twin

This document explains the hydrological theory, equations, and spatial processing models implemented in the Mumbai Flood Digital Twin.

## Core Hydrology Model

The platform uses the **SCS Curve Number (CN) Method** to estimate direct surface runoff from rainfall events. It is a widely accepted empirical model developed by the USDA Soil Conservation Service.

### SCS CN Equations

The primary equations used in `simulation/hydrology/runoff.py` are:

1. **Potential Maximum Retention ($S$):**
   $$S = \frac{25400}{CN} - 254$$
   Where $CN$ is the Curve Number representing soil classification, land use, and imperviousness. We use $CN = 85$ for urban Mumbai, which indicates high imperviousness.

2. **Initial Abstraction ($I_a$):**
   $$I_a = 0.2 \times S$$
   This represents water intercepted by vegetation, surface depression storage, and initial infiltration before runoff begins.

3. **Cumulative Runoff Depth ($Q$):**
   $$Q = \frac{(P - I_a)^2}{P - I_a + S} \quad \text{for } P > I_a$$
   $$Q = 0.0 \quad \text{for } P \le I_a$$
   Where $P$ is the accumulated rainfall depth (mm) since the start of the storm.

### Timestep Increment Runoff
Since the simulation is a time-series model, it computes the incremental runoff for each timestep $t$ by evaluating:
$$\Delta Q_t = Q(P_t) - Q(P_{t-1})$$

## Spatial Weighting and Topography

In a uniform rainfall model, every cell receives the same amount of rainfall. However, in reality, low-lying coastal areas and river valleys accumulate significantly more runoff due to local topography and gravity, while steep hillsides shed water rapidly.

The `HydrologyEngine` models this using two elevation-derived spatial grids computed during initialization:

### 1. Flood Susceptibility Weight (`flood_weight`)
We map the raw elevation grid to a normalized range $E_{norm} \in [0, 1]$, where $0$ is the lowest point in Mumbai (sea level / Mithi river mouth) and $1$ is the highest point (Sanjay Gandhi National Park hills).

A susceptibility weight is computed using an exponential decay function:
$$W_{raw} = \exp(-3.0 \times E_{norm})$$
This results in:
* Low-lying coastal lowlands (elevation near sea level) receiving a weight of $1.0$.
* High-elevation peaks (hills) receiving a weight of $e^{-3} \approx 0.05$ (only 5% of the base runoff remains).

To ensure conservation of water volume across the entire model, the weights are normalized by dividing by their mean:
$$W_{flood} = \frac{W_{raw}}{\text{mean}(W_{raw})}$$

### 2. Drainage Capacity Factor (`drainage_factor`)
Drainage efficiency is also heavily influenced by elevation. Lower valleys have overwhelmed stormwater networks and collect standing water, whereas elevated regions drain rapidly to surrounding areas.

This is modeled using a linear interpolation across the normalized elevation grid:
$$F_{drainage} = 0.05 + 0.45 \times E_{norm}$$

* **Low-lying areas ($E_{norm} \approx 0$):** Have a $5\%$ drainage deduction (95% of water remains on the surface).
* **Hilltops ($E_{norm} \approx 1$):** Have a $50\%$ drainage deduction (50% of water is routed out of the surface model immediately).

### Combined Spatial Runoff Calculation
The final incremental runoff depth in meters deposited on cell $(r, c)$ at timestep $t$ is calculated as:
$$R_{m}(r, c) = \frac{\Delta Q_t(r, c)}{1000} \times W_{flood}(r, c) \times (1 - F_{drainage}(r, c))$$

## Infiltration
In addition to the SCS CN method, the codebase scaffolds **Green-Ampt Infiltration** which computes the rate of infiltration as:
$$f = K_s \left(1 + \frac{(\psi + h) \Delta \theta}{F}\right)$$
Where:
* $K_s$ is saturated hydraulic conductivity.
* $\psi$ is wetting front suction head.
* $\Delta \theta$ is initial moisture deficit.
* $F$ is cumulative infiltration.
* $h$ is ponded surface water depth.
This is prepared for Phase 3 to support dynamic soil infiltration modeling.
