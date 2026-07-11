export interface GeoJsonFeature {
  id?: string | number;
  type: 'Feature';
  properties?: Record<string, unknown> | null;
  geometry: Record<string, unknown> | null;
}

export interface FeatureCollection {
  type: 'FeatureCollection';
  features: GeoJsonFeature[];
}

export type TerrainOverlay =
  | 'dem'
  | 'hillshade'
  | 'contours'
  | 'slope'
  | 'aspect'
  | 'flowAccumulation'
  | 'floodDepth'
  | 'velocity'
  | 'none';

export type WorkspaceMode = 'operator' | 'research' | 'executive';

export type SimulationStatus = 'idle' | 'running' | 'paused' | 'complete';

export interface TerrainData {
  width: number;
  height: number;
  elevation: number[][];
  slope: number[][];
  aspect: number[][];
  flow_direction: number[][];
  flow_accumulation: number[][];
  transform: number[];
  crs: string;
}

export interface SimulationData {
  metadata: {
    width: number;
    height: number;
    crs: string;
    transform: number[];
  };
  time_steps_min: number;
  rainfall_hyetograph_mm: number[];
  depth_history: number[][][];
}

export interface InspectorReading {
  lng: number;
  lat: number;
  row: number;
  col: number;
  elevation: number;
  slope: number;
  aspect: number;
  landCover: string;
  waterDepth: number;
  velocity: number;
  flowDirection: number;
  nearestDrain: string;
  nearestNode: string;
  drainCapacity: number;
  travelTime: number;
}

export interface TwinMetrics {
  currentTime: string;
  maxDepth: number;
  averageDepth: number;
  floodedArea: number;
  rainAdded: number;
  surfaceWaterVolume: number;
  drainIntake: number;
  hydraulicStorage: number;
  outfallDischarge: number;
  massBalanceError: number;
  simulationSpeed: number;
  memoryUsage: number;
  cpuUsage: number;
  gpuUsage: number;
}

export interface TwinDatasets {
  terrain: TerrainData;
  roads: FeatureCollection;
  buildings: FeatureCollection;
  waterways: FeatureCollection;
}

export interface LayerNode {
  id: TerrainOverlay | 'basemap' | 'buildings' | 'roads' | 'drainage' | 'hydraulicNetwork' | 'rainfall' | 'tide' | 'waterways';
  label: string;
  group: string;
  enabled: boolean;
  opacity: number;
}
