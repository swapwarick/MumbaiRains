# Mathematical Specification — Hydraulic Routing Engine

This document details the governing equations, numerical schemes, spatial and temporal discretizations, and literature references for the Hydraulic Routing Engine (Sprint 6).

---

## 1. Pipe Flow Calculations (Manning's Equation)

The gravity-driven flow velocity in conduits is governed by Manning's equation (Manning, 1891; Chow, 1959):

$$ V = \frac{1}{n} R_h^{2/3} S_f^{1/2} $$

where:
* $V$ is the average cross-sectional flow velocity ($m/s$).
* $n$ is Manning's roughness coefficient ($s/m^{1/3}$).
* $R_h$ is the hydraulic radius ($m$), defined as the cross-sectional flow area $A$ divided by the wetted perimeter $P$.
* $S_f$ is the friction slope, assumed equal to the physical pipe slope under the kinematic wave approximation.

### Full-Pipe Circular Conduit Approximations
For a circular pipe of diameter $d$:
* Area: $A_{\text{full}} = \frac{\pi d^2}{4}$
* Wetted Perimeter: $P_{\text{full}} = \pi d$
* Hydraulic Radius: $R_{\text{full}} = \frac{A_{\text{full}}}{P_{\text{full}}} = \frac{d}{4}$

The full-conduit gravity velocity $V_{\text{full}}$ and discharge capacity $Q_{\text{full}}$ are:

$$ V_{\text{full}} = \frac{1}{n} \left(\frac{d}{4}\right)^{2/3} S_f^{1/2} $$

$$ Q_{\text{full}} = V_{\text{full}} \times A_{\text{full}} $$

---

## 2. Convective Wave Translation (Pipe Storage Model)

Conduits are modeled as finite-volume storage links. Water propagates downstream through the pipe with a travel time delay $\tau$:

$$ \tau = \frac{L}{V} $$

where $L$ is the pipe length ($m$), and $V = \max(V_{\text{full}}, V_{\text{min}})$ to prevent numerical division-by-zero errors.

At each timestep $\Delta t$, the volume leaving the pipe storage $S_{\text{pipe}}$ to the downstream node is:

$$ V_{\text{out}} = S_{\text{pipe}} \times \min\left(1.0, \frac{\Delta t}{\tau}\right) $$

The corresponding outflow rate is:

$$ Q_{\text{out}} = \frac{V_{\text{out}}}{\Delta t} $$

---

## 3. Node Storage & Proportional Outflow Allocation

For any junction node $j$, the volume balance equation is resolved at each step:

$$ S_{\text{junc}, j}(t + \Delta t) = S_{\text{junc}, j}(t) + \sum V_{\text{in}} + V_{\text{inflow}} \cdot \Delta t - \sum V_{\text{draw}} $$

where $V_{\text{inflow}}$ represents external stormwater inflows from surface drainage inlets.

### Proportional Flow Limitation
If a junction has multiple outgoing conduits, the potential draw volume is:

$$ V_{\text{draw}, p}^* = Q_{\text{full}, p} \times \Delta t $$

If the total potential draw exceeds the available node storage, the actual draw volume $V_{\text{in}, p}$ for each pipe $p$ is scaled proportionally to ensure non-negative junction storage:

$$ V_{\text{in}, p} = S_{\text{junc}, j}^* \times \frac{V_{\text{draw}, p}^*}{\sum_{k \in P_{\text{out}}(j)} V_{\text{draw}, k}^*} $$

---

## 4. Boundary Conditions

### Overflow (Spills)
When a junction storage exceeds its maximum storage capacity $V_{\text{max}} = A_{\text{junc}} (z_{\text{overflow}} - z_{\text{invert}})$, the excess volume spills:

$$ V_{\text{overflow}} = S_{\text{junc}, j} - V_{\text{max}} $$

This generates an `OverflowEvent` containing the spill volume and elevation.

### Outfalls
Outfall junctions generate a `DischargeRequest` representing the potential water to evacuate:

$$ Q_{\text{request}} = \frac{S_{\text{junc}, \text{outfall}}}{\Delta t} $$

The actual boundary loss volume is verified and subtracted from the system by the engine coordinator.

---

## 5. References

1. **Manning, R. (1891)**. *On the Flow of Water in Open Channels and Pipes*. Transactions of the Institution of Civil Engineers of Ireland.
2. **Chow, V. T. (1959)**. *Open-Channel Hydraulics*. McGraw-Hill, New York.
3. **Henderson, F. M. (1966)**. *Open Channel Flow*. Macmillan Publishing, New York.
4. **Rossman, L. A. (2015)**. *Storm Water Management Model (SWMM) User's Manual Version 5.1*. U.S. Environmental Protection Agency.
5. **USACE (2023)**. *HEC-RAS River Analysis System, Hydraulic Reference Manual*. Hydrologic Engineering Center.
