# Uncertainty Register — Mumbai Flood Digital Twin

This register documents the known assumptions, numerical limitations, missing physics, and expected error sources in the Version 1.0 Beta simulator.

---

## 1. Uncertainty Register Table

| Source of Uncertainty | Impact on Predictions | Confidence | Mitigation Strategy |
|---|---|---|---|
| **Pipelined Intake Capacity (Stubbed)** | The drainage network is modeled as a uniform 1.0 mm/hr intake capacity per cell. Real inlet rates depend on localized pipe diameters, slopes, and local clogging. This may overestimate or underestimate local flooding. | **Medium** | Integrate a detailed GIS spatial database of storm inlets and pipe diameters inside the `HydraulicNetworkEngine`. |
| **Grid Resolution (~105m × 210m)** | Fine street-level drainage flow pathways are averaged over 105m cells. This smooths out local barriers (curbs, walls) and micro-depressions. | **High** | Run sub-grid scaling or downscale the Copernicus DEM to a 5m or 10m grid. |
| **Constant Infiltration Rate (3 mm/hr)** | We assume a uniform concrete coefficient. Real soils (like park lands in SGNP) have much higher infiltration rates, while clay soils have lower. | **Medium** | Implement spatial mapping of soil Curve Numbers (SCS CN) using Land Cover classifications. |
| **Simple Outfall Backwater Model** | Outfalls are blocked during high tide, but full dynamics (tide-driven pressurized backflow) are not solved. | **Low** | Upgrade the 1D hydraulic routing from Kinematic wave to full Diffusive/Dynamic wave (Saint-Venant solver). |
| **Lack of Groundwater Interaction** | Groundwater infiltration and saturation/rise of water tables are ignored. | **Low** | Add a groundwater model tracking infiltration losses to saturated aquifer levels. |
| **Wind & Wave Runup** | Cyclone-driven coastal wave runup is not simulated. | **Low** | Wire a coastal storm-surge engine as a boundary condition block. |

---

## 2. Expected Error Sources

1. **Numerical Discretization Error**: The diffusion-wave solver uses finite differences. Cell size discretization can lead to numerical diffusion.
2. **Topographical Averaging**: Copernicus DEM interpolates canopy and building heights, which can create artificial blockages in flow paths.
3. **Precipitation Uniformity**: Rainfall is assumed uniform across the 200x200 grid, whereas convective monsoon storms exhibit high spatial variability.
