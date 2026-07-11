import { Archive, Beaker, ChevronDown, CloudRain, Database, FolderTree, Layers, UploadCloud } from 'lucide-react';
import { scenarioCatalog } from '../../features/digitalTwin/catalog';
import type { LayerNode, TerrainOverlay } from '../../features/digitalTwin/types';

interface LeftDockProps {
  collapsed: boolean;
  selectedScenario: string;
  rainfallIntensity: number;
  layers: LayerNode[];
  onScenarioSelect: (scenario: string) => void;
  onRainfallIntensityChange: (intensity: number) => void;
  onOverlaySelect: (overlay: TerrainOverlay) => void;
  onLayerToggle: (id: LayerNode['id']) => void;
  onLayerOpacity: (id: LayerNode['id'], opacity: number) => void;
}

export function LeftDock({
  collapsed,
  selectedScenario,
  rainfallIntensity,
  layers,
  onScenarioSelect,
  onRainfallIntensityChange,
  onOverlaySelect,
  onLayerToggle,
  onLayerOpacity,
}: LeftDockProps) {
  const groupedLayers = layers.reduce<Record<string, LayerNode[]>>((groups, layer) => {
    groups[layer.group] = [...(groups[layer.group] ?? []), layer];
    return groups;
  }, {});

  const updateRainfallIntensity = (value: number) => {
    const nextValue = Number.isFinite(value) ? Math.min(500, Math.max(0, Math.round(value))) : 0;
    onRainfallIntensityChange(nextValue);
  };

  return (
    <aside className={`dock dock-left ${collapsed ? 'is-collapsed' : ''}`}>
      <section className="dock-section">
        <div className="section-heading">
          <FolderTree size={15} />
          <span>Scenario Explorer</span>
        </div>
        <div className="scenario-list">
          {scenarioCatalog.map((scenario) => (
            <button
              type="button"
              key={scenario.id}
              className={selectedScenario === scenario.id ? 'scenario-card active' : 'scenario-card'}
              onClick={() => onScenarioSelect(scenario.id)}
            >
              <strong>{scenario.label}</strong>
              <span>{scenario.detail}</span>
              <small>{scenario.status}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="dock-section rainfall-control">
        <div className="section-heading">
          <CloudRain size={15} />
          <span>Rainfall Forcing</span>
          <em>{rainfallIntensity} mm/hr</em>
        </div>
        <div className="rainfall-readout">
          <strong>{rainfallIntensity}</strong>
          <span>millimeters per hour</span>
        </div>
        <input
          type="range"
          min="0"
          max="250"
          step="5"
          value={rainfallIntensity}
          onChange={(event) => updateRainfallIntensity(Number(event.target.value))}
          aria-label="Rainfall intensity in millimeters per hour"
        />
        <div className="rainfall-input-row">
          <span>0</span>
          <label>
            <input
              type="number"
              min="0"
              max="500"
              step="5"
              value={rainfallIntensity}
              onChange={(event) => updateRainfallIntensity(Number(event.target.value))}
            />
            mm/hr
          </label>
          <span>250</span>
        </div>
      </section>

      <section className="dock-section layer-manager">
        <div className="section-heading">
          <Layers size={15} />
          <span>Layer Manager</span>
        </div>
        {Object.entries(groupedLayers).map(([group, groupLayers]) => (
          <div className="layer-group" key={group}>
            <div className="layer-group-title">
              <ChevronDown size={14} />
              <span>{group}</span>
            </div>
            {groupLayers.map((layer) => (
              <div className="layer-row" key={layer.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={layer.enabled}
                    onChange={() => {
                      onLayerToggle(layer.id);
                      if (['dem', 'hillshade', 'contours', 'slope', 'aspect', 'flowAccumulation', 'floodDepth', 'velocity'].includes(layer.id)) {
                        onOverlaySelect(layer.id as TerrainOverlay);
                      }
                    }}
                  />
                  <span>{layer.label}</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={layer.opacity}
                  onChange={(event) => onLayerOpacity(layer.id, Number(event.target.value))}
                  aria-label={`${layer.label} opacity`}
                />
              </div>
            ))}
          </div>
        ))}
      </section>

      <section className="dock-section compact-assets">
        <div className="section-heading">
          <Database size={15} />
          <span>Project Assets</span>
        </div>
        <div className="asset-grid">
          <span><Archive size={14} /> DEM 10m</span>
          <span><UploadCloud size={14} /> Custom CSV</span>
          <span><Beaker size={14} /> Experiments</span>
        </div>
      </section>
    </aside>
  );
}