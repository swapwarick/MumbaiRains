# Hydraulic Routing Engine — Architectural Specifications

This document outlines the architecture, data models, public APIs, and routing engine of the Hydraulic Network simulation (Sprint 6).

---

## 1. Swappable Strategy Architecture

To allow future upgrades to more complex hydraulic models (such as diffusive wave or full Saint-Venant solvers) without code churn, the sub-surface flow system decouples the **simulation driver** from the **routing logic** using the **Strategy Pattern**.

```mermaid
graph TD
    HydraulicRoutingEngine -->|Delegates routing| RoutingStrategy
    RoutingStrategy <|-- KinematicRoutingStrategy
    RoutingStrategy <|-- DiffusiveRoutingStrategy_Future
    RoutingStrategy <|-- SaintVenantRoutingStrategy_Future
```

* **`HydraulicRoutingEngine`**: Manages simulation clock, registers pipes and junctions, invokes the selected strategy, tracks boundary discharge conditions (TideEngine requests), and logs cumulative water budget reports.
* **`RoutingStrategy`**: An abstract interface executing a single timestep advancement of the state.

---

## 2. Public API & Data Models

### `Pipe`
Physical structural properties of pipe edges:
* `pipe_id` (str): Unique pipe ID.
* `length` (float): Pipe length (m).
* `diameter` (float): Conduit diameter (m).
* `roughness` (float): Manning's roughness coefficient $n$.
* `invert_upstream` / `invert_downstream` (float): Connecting elevations (m).
* `upstream_node` / `downstream_node` (str): Connecting junction IDs.

### `Junction`
Physical structural properties of junction nodes:
* `junction_id` (str): Unique junction ID.
* `ground_elevation` (float): Ground surface elevation.
* `invert_elevation` (float): Invert bottom elevation.
* `overflow_elevation` (float): Ground level spill elevation.
* `max_storage_volume` (float): Storage volume capacity before overflow spills ($m^3$).

### `HydraulicState`
Instantaneous physical variables at step $t$:
* `pipe_flow` (Dict[str, float]): Current flow rate per pipe ($m^3/s$).
* `pipe_storage` (Dict[str, float]): Current water volume in pipe ($m^3$).
* `junction_storage` (Dict[str, float]): Current water volume in junction ($m^3$).
* `overflow_events` (List[OverflowEvent]): Spill events generated during the current step.
* `discharge_requests` (List[DischargeRequest]): Boundary discharge requests generated during the current step.

---

## 3. Boundary & Event Decoupling

* **Overflow Events (`OverflowEvent`)**: Instead of injecting spilled water back onto the surface model immediately, the routing strategy generates `OverflowEvent` objects. These are processed later by coupling components.
* **Discharge Requests (`DischargeRequest`)**: Outfall nodes do not simply delete water. The strategy generates a `DischargeRequest` detailing the potential outflow. The `HydraulicRoutingEngine` (and in future sprints, the `TideEngine`) determines the fraction of accepted discharge depending on external tailwater (tide) levels.

---

## 4. Known Limitations
* **Pressurized Flow**: The current kinematic routing strategy assumes open-channel gravity flow; surcharge and pipe pressurization (Preissmann slot) are not modeled.
* **Backwater Effects**: Flow propagates only in the downstream direction (based on pipe slope). Adverse slopes or backwater waves from tailwater conditions are not resolved.
