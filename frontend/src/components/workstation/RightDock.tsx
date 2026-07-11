import { Activity, BarChart3, Cpu, Gauge, GitBranch, Microscope, Waves } from 'lucide-react';
import type { InspectorReading, SimulationStatus, TwinMetrics, WorkspaceMode } from '../../features/digitalTwin/types';

interface RightDockProps {
  collapsed: boolean;
  mode: WorkspaceMode;
  status: SimulationStatus;
  metrics: TwinMetrics;
  inspector: InspectorReading | null;
}

function StatLine({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="stat-line">
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
    </div>
  );
}

function MiniChart({ values, tone = 'cyan' }: { values: number[]; tone?: 'cyan' | 'amber' | 'red' }) {
  const max = Math.max(...values, 1);
  const points = values
    .map((value, index) => `${(index / (values.length - 1)) * 100},${42 - (value / max) * 36}`)
    .join(' ');

  return (
    <svg className={`mini-chart ${tone}`} viewBox="0 0 100 48" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={points} />
      <line x1="0" y1="42" x2="100" y2="42" />
    </svg>
  );
}

export function RightDock({ collapsed, mode, status, metrics, inspector }: RightDockProps) {
  const researchVisible = mode === 'research';
  const hydrograph = [0.04, 0.08, metrics.averageDepth, metrics.maxDepth * 0.62, metrics.maxDepth, metrics.averageDepth * 1.4, metrics.maxDepth * 0.55];
  const balance = [0.2, metrics.massBalanceError, 0.8, 1.2, metrics.massBalanceError * 0.7, 0.5, 0.3];

  return (
    <aside className={`dock dock-right ${collapsed ? 'is-collapsed' : ''}`}>
      <section className="dock-section">
        <div className="section-heading">
          <Activity size={15} />
          <span>Live Simulation Metrics</span>
          <em>{status}</em>
        </div>
        <div className="metric-grid">
          <div>
            <span>Current Time</span>
            <strong>{metrics.currentTime}</strong>
          </div>
          <div>
            <span>Max Depth</span>
            <strong>{metrics.maxDepth.toFixed(2)} m</strong>
          </div>
          <div>
            <span>Flooded Area</span>
            <strong>{metrics.floodedArea.toFixed(2)} km2</strong>
          </div>
          <div>
            <span>Sim Speed</span>
            <strong>{metrics.simulationSpeed.toFixed(0)} fps</strong>
          </div>
        </div>
        <StatLine label="Average Flood Depth" value={`${metrics.averageDepth.toFixed(2)} m`} />
        <StatLine label="Rain Added" value={`${(metrics.rainAdded / 1_000_000).toFixed(2)} Mm3`} />
        <StatLine label="Surface Water Volume" value={`${(metrics.surfaceWaterVolume / 1_000_000).toFixed(2)} Mm3`} />
        <StatLine label="Drain Intake" value={`${(metrics.drainIntake / 1_000_000).toFixed(2)} Mm3`} />
        <StatLine label="Hydraulic Storage" value={`${(metrics.hydraulicStorage / 1_000_000).toFixed(2)} Mm3`} />
        <StatLine label="Outfall Discharge" value={`${(metrics.outfallDischarge / 1_000_000).toFixed(2)} Mm3`} />
        <StatLine
          label="Mass Balance Error"
          value={`${metrics.massBalanceError.toFixed(2)}%`}
          tone={metrics.massBalanceError > 3 ? 'warn' : 'good'}
        />
      </section>

      <section className="dock-section">
        <div className="section-heading">
          <BarChart3 size={15} />
          <span>Hydrographs</span>
        </div>
        <MiniChart values={hydrograph} />
        <div className="chart-labels">
          <span>Flood volume</span>
          <strong>{(metrics.surfaceWaterVolume / 1_000_000).toFixed(2)} Mm3</strong>
        </div>
      </section>

      {researchVisible && (
        <>
          <section className="dock-section">
            <div className="section-heading">
              <GitBranch size={15} />
              <span>Mass Balance</span>
            </div>
            <MiniChart values={balance} tone={metrics.massBalanceError > 3 ? 'red' : 'amber'} />
            <StatLine label="Continuity Residual" value={`${metrics.massBalanceError.toFixed(2)}%`} />
            <StatLine label="Drain Utilization" value={`${Math.min(98, metrics.drainIntake / Math.max(1, metrics.surfaceWaterVolume) * 100).toFixed(1)}%`} />
            <StatLine label="Outfall Utilization" value={`${Math.min(96, metrics.outfallDischarge / Math.max(1, metrics.surfaceWaterVolume) * 100).toFixed(1)}%`} />
          </section>

          <section className="dock-section profiler">
            <div className="section-heading">
              <Cpu size={15} />
              <span>Diagnostics Profiler</span>
            </div>
            <StatLine label="Memory Usage" value={`${metrics.memoryUsage.toFixed(0)} MB`} />
            <StatLine label="CPU Usage" value={`${metrics.cpuUsage.toFixed(0)}%`} />
            <StatLine label="GPU Usage" value={`${metrics.gpuUsage.toFixed(0)}%`} />
            <StatLine label="Raster Upload" value="WebGL image source" />
          </section>
        </>
      )}

      <section className="dock-section inspector">
        <div className="section-heading">
          <Microscope size={15} />
          <span>Inspector Tool</span>
        </div>
        {inspector ? (
          <>
            <StatLine label="Coordinates" value={`${inspector.lng.toFixed(5)}, ${inspector.lat.toFixed(5)}`} />
            <StatLine label="Elevation" value={`${inspector.elevation.toFixed(1)} m`} />
            <StatLine label="Slope / Aspect" value={`${inspector.slope.toFixed(1)} deg / ${inspector.aspect.toFixed(0)} deg`} />
            <StatLine label="Land Cover" value={inspector.landCover} />
            <StatLine label="Water Depth" value={`${inspector.waterDepth.toFixed(2)} m`} tone={inspector.waterDepth > 0.5 ? 'warn' : 'good'} />
            <StatLine label="Velocity" value={`${inspector.velocity.toFixed(2)} m/s`} />
            <StatLine label="Flow Direction" value={`${inspector.flowDirection.toFixed(0)} deg`} />
            <StatLine label="Nearest Drain" value={inspector.nearestDrain} />
            <StatLine label="Nearest Node" value={inspector.nearestNode} />
            <StatLine label="Drain Capacity" value={`${inspector.drainCapacity.toFixed(2)} m3/s`} />
            <StatLine label="Travel Time" value={`${inspector.travelTime.toFixed(0)} min`} />
          </>
        ) : (
          <div className="empty-inspector">
            <Waves size={18} />
            <span>Click the map to query terrain, flood, and hydraulic attributes.</span>
          </div>
        )}
      </section>

      <section className="dock-section">
        <div className="section-heading">
          <Gauge size={15} />
          <span>Warnings</span>
        </div>
        <div className={metrics.massBalanceError > 3 ? 'warning-card active' : 'warning-card'}>
          {metrics.massBalanceError > 3 ? 'Mass balance warning threshold exceeded' : 'No critical diagnostics'}
        </div>
      </section>
    </aside>
  );
}
