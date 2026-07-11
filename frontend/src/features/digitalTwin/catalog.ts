import type { LayerNode, TerrainOverlay, TwinMetrics, WorkspaceMode } from './types';

export const scenarioCatalog = [
  { id: 'synthetic', label: 'Synthetic Design Storm', detail: '30 mm/hr baseline calibration', status: 'Ready' },
  { id: 'historical-2005', label: 'Historical 2005', detail: 'Extreme monsoon reconstruction', status: 'Calibrated' },
  { id: 'historical-2024', label: 'Historical 2024', detail: 'Observed drainage stress case', status: 'Review' },
  { id: 'blocked-drain', label: 'Blocked Drain', detail: 'Ward-level obstruction sensitivity', status: 'Ready' },
  { id: 'cyclone', label: 'Cyclone Surge', detail: 'Rainfall and tide compound hazard', status: 'Draft' },
  { id: '100mm', label: '100 mm/hr Cloudburst', detail: 'High intensity short duration pulse', status: 'Ready' },
  { id: 'custom-csv', label: 'Custom CSV', detail: 'Import hyetograph and boundary data', status: 'Local' },
  { id: 'imd-api', label: 'Future IMD API', detail: 'Forecast ingestion placeholder', status: 'Planned' },
];

export const defaultLayers: LayerNode[] = [
  { id: 'basemap', label: 'Basemap', group: 'Base Map', enabled: true, opacity: 1 },
  { id: 'dem', label: 'DEM', group: 'Terrain', enabled: true, opacity: 0.52 },
  { id: 'hillshade', label: 'Hillshade', group: 'Terrain', enabled: true, opacity: 0.4 },
  { id: 'contours', label: 'Contours', group: 'Terrain', enabled: false, opacity: 0.55 },
  { id: 'slope', label: 'Slope', group: 'Terrain Analysis', enabled: false, opacity: 0.5 },
  { id: 'aspect', label: 'Aspect', group: 'Terrain Analysis', enabled: false, opacity: 0.5 },
  { id: 'flowAccumulation', label: 'Flow Accumulation', group: 'Hydrology', enabled: false, opacity: 0.72 },
  { id: 'buildings', label: 'Buildings', group: 'Infrastructure', enabled: true, opacity: 0.8 },
  { id: 'roads', label: 'Roads', group: 'Infrastructure', enabled: true, opacity: 0.82 },
  { id: 'waterways', label: 'Waterways', group: 'Infrastructure', enabled: true, opacity: 0.9 },
  { id: 'drainage', label: 'Drainage', group: 'Hydraulic Network', enabled: true, opacity: 0.76 },
  { id: 'hydraulicNetwork', label: 'Hydraulic Network', group: 'Hydraulic Network', enabled: false, opacity: 0.72 },
  { id: 'floodDepth', label: 'Flood Depth', group: 'Simulation', enabled: true, opacity: 0.78 },
  { id: 'velocity', label: 'Velocity', group: 'Simulation', enabled: false, opacity: 0.62 },
  { id: 'rainfall', label: 'Rainfall', group: 'Boundary Conditions', enabled: false, opacity: 0.48 },
  { id: 'tide', label: 'Tide', group: 'Boundary Conditions', enabled: false, opacity: 0.44 },
];

export const modeCopy: Record<WorkspaceMode, string> = {
  operator: 'Operate',
  research: 'Research',
  executive: 'Executive',
};

export const overlayLabels: Record<TerrainOverlay, string> = {
  dem: 'DEM',
  hillshade: 'Hillshade',
  contours: 'Contours',
  slope: 'Slope',
  aspect: 'Aspect',
  flowAccumulation: 'Flow Accumulation',
  floodDepth: 'Flood Depth',
  velocity: 'Velocity',
  none: 'None',
};

export const emptyMetrics: TwinMetrics = {
  currentTime: '00:00',
  maxDepth: 0,
  averageDepth: 0,
  floodedArea: 0,
  rainAdded: 0,
  surfaceWaterVolume: 0,
  drainIntake: 0,
  hydraulicStorage: 0,
  outfallDischarge: 0,
  massBalanceError: 0,
  simulationSpeed: 0,
  memoryUsage: 318,
  cpuUsage: 18,
  gpuUsage: 27,
};
