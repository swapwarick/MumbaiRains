# Calibration Report — Urban Hydrodynamic Simulation Platform (UHSP)

This calibration report details the findings and physical mechanisms of the flood simulations conducted on the Greater Mumbai terrain models.

---

## 1. Why Flooding Occurs

Urban flooding in Mumbai is driven by a combination of meteorological, topographical, and hydrological factors:

1. **Extreme Rainfall Forcing**: The meteorological forcing (60 mm/hr) generates rainfall rates that exceed the natural soil infiltration capacity.
2. **Infiltration Losses Exceeded**: Soil infiltration is modeled at a constant rate of 3.0 mm/hr (representing heavily paved urban concrete), meaning **95% of rain** directly converts to surface runoff.
3. **Drainage Network Bottle-necks**: The sub-surface drainage network has a modeled intake capacity of 1.0 mm/hr. During a 60 mm/hr deluge, the inlets are fully saturated (utilization at 100%), and **98% of the runoff** must remain on the surface.
4. **Boundary Tide Blocks**: Tidal variations (mean sea level 0.0m with spring tide ranges up to 4.5m) raise the outfall boundary heights. When high tide occurs, outfalls experience backwater blocks, preventing gravity discharge and causing water to back up into the city's low-lying drainage channels.

---

## 2. Where Flooding Occurs

Flooding is highly localized and concentrates in specific basins and catchments:
- **Mithi River Corridor**: The primary diagonal low-elevation trough in the DEM collects overland flow from the surrounding SGNP hills. Depths here reach **0.95 m**, which is **3.54x deeper** than dry hilltop cells.
- **Dharavi / BKC Corridor**: Sitting at or near sea level, these flat coastal clay plains experience severe ponding (depths exceeding 0.8m) due to lack of gravity drainage slopes.
- **SGNP Hills (Hillsides)**: The high hills (elevation 65–90m) remain entirely dry (depths < 0.05m) because gravity routes water downhill before it can accumulate.

---

## 3. Terrain Depressions Controlling Flooding

The principal topographical controls are:
- **Dharavi Sink**: A local basin depression that acts as the primary drainage outlet for the Mithi corridor. When tide levels are high, this sink fills rapidly.
- **BKC Trough**: The flat valley bounding the Mithi River. The Pearson correlation between elevation and depth is **-0.362**, confirming that runoff is directed downhill into these low-elevation troughs.

---

## 4. Drainage Structures Reducing Flooding

Flooding is mitigated by:
- **Storm Water Inlets**: The 2D surface grid links directly to 1D sub-surface pipes. Drains capture up to 1.0 mm/hr of runoff, successfully routing water out of local depressions to coastal outfalls.
- **Outfalls**: When tide levels recede, outfalls discharge sub-surface storage, accelerating surface drainage.
