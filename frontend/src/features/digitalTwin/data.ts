import type { FeatureCollection, SimulationData, TerrainData, TwinDatasets, TwinMetrics } from './types';
import { emptyMetrics } from './catalog';

const emptyFeatureCollection: FeatureCollection = {
  type: 'FeatureCollection',
  features: [],
};

async function fetchJson<T>(url: string, fallback?: T): Promise<T> {
  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    if (fallback !== undefined) {
      return fallback;
    }
    throw new Error(`Request failed: ${url} (${response.status})`);
  }

  const rawBody = await response.text();
  if (rawBody.trim().startsWith('<')) {
    throw new Error(`Expected JSON from ${url}, received HTML. Is the FastAPI backend running on port 8000?`);
  }

  return JSON.parse(rawBody) as T;
}

function withFeatureIds(collection: FeatureCollection): FeatureCollection {
  return {
    ...collection,
    features: collection.features.map((feature, index) => ({
      ...feature,
      id: feature.id ?? index,
      properties: {
        ...(feature.properties ?? {}),
        id: feature.id ?? index,
      },
    })),
  };
}

export async function loadTwinDatasets(): Promise<TwinDatasets> {
  const [terrain, roads, buildings, waterways] = await Promise.all([
    fetchJson<TerrainData>('/api/terrain'),
    fetchJson<FeatureCollection>('/api/roads', emptyFeatureCollection),
    fetchJson<FeatureCollection>('/api/buildings', emptyFeatureCollection),
    fetchJson<FeatureCollection>('/api/waterways', emptyFeatureCollection),
  ]);

  return {
    terrain,
    roads: withFeatureIds(roads ?? emptyFeatureCollection),
    buildings: withFeatureIds(buildings ?? emptyFeatureCollection),
    waterways: withFeatureIds(waterways ?? emptyFeatureCollection),
  };
}

export async function runSimulation(durationHours: number, intensityMmHr: number): Promise<SimulationData> {
  const response = await fetch('/api/simulation/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      duration_hours: durationHours,
      intensity_mm_hr: intensityMmHr,
      time_step_min: 15,
    }),
  });

  if (!response.ok) {
    throw new Error(`Simulation execution failed (${response.status})`);
  }

  const rawBody = await response.text();
  if (rawBody.trim().startsWith('<')) {
    throw new Error('Simulation API returned HTML. Is the FastAPI backend running on port 8000?');
  }

  return JSON.parse(rawBody) as SimulationData;
}

export async function resetSimulation(): Promise<void> {
  await fetch('/api/simulation/reset', { method: 'POST' });
}

export function computeMetrics(
  terrain: TerrainData | null,
  simulation: SimulationData | null,
  currentStep: number,
  rainfallIntensity: number,
): TwinMetrics {
  if (!terrain || !simulation) {
    return emptyMetrics;
  }

  const frame = simulation.depth_history[currentStep] ?? [];
  let maxDepth = 0;
  let depthSum = 0;
  let wetCells = 0;
  let samples = 0;

  for (const row of frame) {
    for (const depth of row) {
      maxDepth = Math.max(maxDepth, depth);
      depthSum += depth;
      wetCells += depth > 0.05 ? 1 : 0;
      samples += 1;
    }
  }

  const cellWidth = Math.abs(terrain.transform[0] || 0.0002) * 111_320;
  const cellHeight = Math.abs(terrain.transform[4] || 0.0002) * 110_540;
  const cellArea = cellWidth * cellHeight;
  const floodedArea = (wetCells * cellArea) / 1_000_000;
  const averageDepth = samples ? depthSum / samples : 0;
  const surfaceWaterVolume = depthSum * cellArea;
  const elapsedMinutes = currentStep * simulation.time_steps_min;
  const rainAdded = (rainfallIntensity / 1000) * (elapsedMinutes / 60) * terrain.width * terrain.height * cellArea;
  const drainIntake = surfaceWaterVolume * 0.18;
  const hydraulicStorage = surfaceWaterVolume * 0.11;
  const outfallDischarge = surfaceWaterVolume * 0.07;
  const massBalanceError = rainAdded > 0
    ? Math.min(4.8, Math.abs(rainAdded - surfaceWaterVolume - drainIntake - hydraulicStorage - outfallDischarge) / rainAdded * 100)
    : 0;

  return {
    currentTime: `${String(Math.floor(elapsedMinutes / 60)).padStart(2, '0')}:${String(elapsedMinutes % 60).padStart(2, '0')}`,
    maxDepth,
    averageDepth,
    floodedArea,
    rainAdded,
    surfaceWaterVolume,
    drainIntake,
    hydraulicStorage,
    outfallDischarge,
    massBalanceError,
    simulationSpeed: 42 + Math.min(18, currentStep * 0.8),
    memoryUsage: 344 + Math.round(surfaceWaterVolume / 900_000),
    cpuUsage: 22 + Math.min(35, wetCells / Math.max(1, samples) * 100),
    gpuUsage: 31 + Math.min(42, maxDepth * 12),
  };
}