import type { InspectorReading, TerrainData, TerrainOverlay } from './types';

type ColorStop = [number, [number, number, number, number]];

const waterRamp: ColorStop[] = [
  [0, [0, 0, 0, 0]],
  [0.05, [125, 211, 252, 70]],
  [0.2, [30, 144, 255, 132]],
  [0.5, [34, 211, 238, 168]],
  [1, [250, 204, 21, 184]],
  [1.5, [249, 115, 22, 210]],
  [2.5, [220, 38, 38, 226]],
  [3, [127, 29, 29, 238]],
];

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function rampColor(value: number, stops: ColorStop[]): [number, number, number, number] {
  for (let index = 0; index < stops.length - 1; index += 1) {
    const [leftValue, leftColor] = stops[index];
    const [rightValue, rightColor] = stops[index + 1];

    if (value <= rightValue) {
      const t = clamp((value - leftValue) / (rightValue - leftValue || 1), 0, 1);
      return [
        Math.round(lerp(leftColor[0], rightColor[0], t)),
        Math.round(lerp(leftColor[1], rightColor[1], t)),
        Math.round(lerp(leftColor[2], rightColor[2], t)),
        Math.round(lerp(leftColor[3], rightColor[3], t)),
      ];
    }
  }

  return stops[stops.length - 1][1];
}

function sampleBilinear(grid: number[][], x: number, y: number): number {
  const height = grid.length;
  const width = grid[0]?.length ?? 0;
  const x0 = clamp(Math.floor(x), 0, width - 1);
  const x1 = clamp(x0 + 1, 0, width - 1);
  const y0 = clamp(Math.floor(y), 0, height - 1);
  const y1 = clamp(y0 + 1, 0, height - 1);
  const tx = x - x0;
  const ty = y - y0;
  const top = lerp(grid[y0][x0], grid[y0][x1], tx);
  const bottom = lerp(grid[y1][x0], grid[y1][x1], tx);

  return lerp(top, bottom, ty);
}

function gridStats(grid: number[][]): { min: number; max: number } {
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;

  for (const row of grid) {
    for (const value of row) {
      min = Math.min(min, value);
      max = Math.max(max, value);
    }
  }

  return { min, max: max === min ? min + 1 : max };
}

export function rasterCoordinates(terrain: TerrainData): [[number, number], [number, number], [number, number], [number, number]] {
  const dx = terrain.transform[0];
  const dy = terrain.transform[4];
  const west = terrain.transform[2];
  const north = terrain.transform[5];
  const east = west + terrain.width * dx;
  const south = north + terrain.height * dy;

  return [
    [west, north],
    [east, north],
    [east, south],
    [west, south],
  ];
}

export function terrainCenter(terrain: TerrainData): [number, number] {
  const coordinates = rasterCoordinates(terrain);
  return [
    (coordinates[0][0] + coordinates[1][0]) / 2,
    (coordinates[0][1] + coordinates[3][1]) / 2,
  ];
}

export function renderTerrainRaster(terrain: TerrainData, overlay: TerrainOverlay): HTMLCanvasElement {
  const sourceGrid = overlay === 'slope'
    ? terrain.slope
    : overlay === 'aspect'
      ? terrain.aspect
      : overlay === 'flowAccumulation'
        ? terrain.flow_accumulation
        : terrain.elevation;
  const width = Math.min(1536, Math.max(terrain.width * 6, 512));
  const height = Math.min(1536, Math.max(terrain.height * 6, 512));
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');

  canvas.width = width;
  canvas.height = height;

  if (!context) {
    return canvas;
  }

  const image = context.createImageData(width, height);
  const { min, max } = gridStats(sourceGrid);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const gx = (x / Math.max(1, width - 1)) * (terrain.width - 1);
      const gy = (y / Math.max(1, height - 1)) * (terrain.height - 1);
      const value = sampleBilinear(sourceGrid, gx, gy);
      const normalized = clamp((value - min) / (max - min), 0, 1);
      const index = (y * width + x) * 4;

      if (overlay === 'flowAccumulation') {
        const intensity = Math.pow(normalized, 0.28);
        image.data[index] = 34;
        image.data[index + 1] = Math.round(158 + intensity * 80);
        image.data[index + 2] = 188;
        image.data[index + 3] = Math.round(intensity * 170);
      } else if (overlay === 'slope') {
        image.data[index] = Math.round(30 + normalized * 220);
        image.data[index + 1] = Math.round(220 - normalized * 90);
        image.data[index + 2] = Math.round(120 - normalized * 70);
        image.data[index + 3] = 132;
      } else if (overlay === 'aspect') {
        const hueBand = Math.abs(Math.sin((value / 180) * Math.PI));
        image.data[index] = Math.round(60 + hueBand * 120);
        image.data[index + 1] = Math.round(100 + (1 - hueBand) * 120);
        image.data[index + 2] = Math.round(180 + normalized * 50);
        image.data[index + 3] = 128;
      } else if (overlay === 'hillshade') {
        const slopeShade = clamp(sampleBilinear(terrain.slope, gx, gy) / 32, 0, 1);
        const aspectShade = 0.5 + Math.cos((sampleBilinear(terrain.aspect, gx, gy) - 315) * Math.PI / 180) * 0.5;
        const shade = clamp(0.28 + normalized * 0.28 + aspectShade * 0.26 - slopeShade * 0.18, 0, 1);
        image.data[index] = Math.round(190 * shade);
        image.data[index + 1] = Math.round(205 * shade);
        image.data[index + 2] = Math.round(215 * shade);
        image.data[index + 3] = 118;
      } else {
        const shade = sampleBilinear(terrain.slope, gx, gy) / 45;
        image.data[index] = Math.round(42 + normalized * 118 + shade * 18);
        image.data[index + 1] = Math.round(64 + normalized * 110);
        image.data[index + 2] = Math.round(76 + normalized * 84);
        image.data[index + 3] = overlay === 'none' ? 0 : 122;
      }
    }
  }

  context.putImageData(image, 0, 0);
  return canvas;
}

export function renderWaterRaster(depthFrame: number[][] | null, phase: number): HTMLCanvasElement {
  const source = depthFrame && depthFrame.length > 0 ? depthFrame : [[0, 0], [0, 0]];
  const sourceHeight = source.length;
  const sourceWidth = source[0]?.length ?? 2;
  const width = Math.min(1536, Math.max(sourceWidth * 6, 512));
  const height = Math.min(1536, Math.max(sourceHeight * 6, 512));
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');

  canvas.width = width;
  canvas.height = height;

  if (!context) {
    return canvas;
  }

  const image = context.createImageData(width, height);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const gx = (x / Math.max(1, width - 1)) * (sourceWidth - 1);
      const gy = (y / Math.max(1, height - 1)) * (sourceHeight - 1);
      const shimmer = Math.sin(x * 0.035 + y * 0.022 + phase) * 0.018;
      const depth = Math.max(0, sampleBilinear(source, gx, gy) + shimmer);
      const color = rampColor(depth, waterRamp);
      const index = (y * width + x) * 4;

      image.data[index] = color[0];
      image.data[index + 1] = color[1];
      image.data[index + 2] = color[2];
      image.data[index + 3] = depth < 0.03 ? 0 : color[3];
    }
  }

  context.putImageData(image, 0, 0);
  return canvas;
}

export function inspectCell(
  terrain: TerrainData,
  depthFrame: number[][] | null,
  lng: number,
  lat: number,
): InspectorReading {
  const dx = terrain.transform[0];
  const dy = terrain.transform[4];
  const col = clamp(Math.floor((lng - terrain.transform[2]) / dx), 0, terrain.width - 1);
  const row = clamp(Math.floor((lat - terrain.transform[5]) / dy), 0, terrain.height - 1);
  const waterDepth = depthFrame?.[row]?.[col] ?? 0;
  const slope = terrain.slope[row][col];

  return {
    lng,
    lat,
    row,
    col,
    elevation: terrain.elevation[row][col],
    slope,
    aspect: terrain.aspect[row][col],
    landCover: waterDepth > 0.2 ? 'Urban floodplain' : 'Dense urban fabric',
    waterDepth,
    velocity: Math.min(3.2, waterDepth * 0.85 + slope * 0.018),
    flowDirection: terrain.flow_direction[row][col],
    nearestDrain: `DR-${String((row * 17 + col) % 420).padStart(3, '0')}`,
    nearestNode: `MH-${String((row * 11 + col * 3) % 680).padStart(3, '0')}`,
    drainCapacity: 1.2 + ((row + col) % 7) * 0.18,
    travelTime: 6 + ((row * 2 + col) % 28),
  };
}
