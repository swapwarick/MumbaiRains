/* oxlint-disable react-hooks/exhaustive-deps */
import { useEffect, useMemo, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Building2, Crosshair, Home, Layers3, LocateFixed, Map, Navigation, Ruler, Waves } from 'lucide-react';
import type {
  FeatureCollection,
  InspectorReading,
  LayerNode,
  SimulationData,
  TerrainData,
  TerrainOverlay,
} from '../../features/digitalTwin/types';
import {
  inspectCell,
  rasterCoordinates,
  renderTerrainRaster,
  renderWaterRaster,
  terrainCenter,
} from '../../features/digitalTwin/raster';

interface MapViewportProps {
  terrain: TerrainData;
  roads: FeatureCollection;
  buildings: FeatureCollection;
  waterways: FeatureCollection;
  activeOverlay: TerrainOverlay;
  simulation: SimulationData | null;
  currentStep: number;
  layers: LayerNode[];
  threeD: boolean;
  onInspect: (reading: InspectorReading) => void;
}

const sourceIds = {
  hillshade: 'hillshade-raster-source',
  terrain: 'terrain-raster-source',
  water: 'water-raster-source',
  roads: 'roads-source',
  buildings: 'buildings-source',
  waterways: 'waterways-source',
};

const layerIds = {
  basemap: 'carto-basemap-layer',
  labels: 'carto-labels-layer',
  hillshade: 'hillshade-raster-layer',
  terrain: 'terrain-raster-layer',
  water: 'water-raster-layer',
  roads: 'roads-layer',
  buildings: 'buildings-layer',
  waterways: 'waterways-layer',
};

const mumbaiBookmarks = {
  mumbai: { center: [72.8777, 19.076] as [number, number], zoom: 10.8, pitch: 0, bearing: 0 },
  bkc: { center: [72.8678, 19.0676] as [number, number], zoom: 14.3, pitch: 35, bearing: -12 },
  kurla: { center: [72.8794, 19.0726] as [number, number], zoom: 14.1, pitch: 35, bearing: -10 },
  mithi: { center: [72.8649, 19.1107] as [number, number], zoom: 13.2, pitch: 42, bearing: -20 },
};

function layerEnabled(layers: LayerNode[], id: LayerNode['id']): boolean {
  return layers.find((layer) => layer.id === id)?.enabled ?? false;
}

function layerOpacity(layers: LayerNode[], id: LayerNode['id']): number {
  return layers.find((layer) => layer.id === id)?.opacity ?? 1;
}

function activeTerrainLayer(activeOverlay: TerrainOverlay): TerrainOverlay {
  return activeOverlay === 'none' || activeOverlay === 'floodDepth' || activeOverlay === 'velocity'
    ? 'dem'
    : activeOverlay;
}

function buildBasemapStyle(): maplibregl.StyleSpecification {
  return {
    version: 8,
    sources: {
      'carto-dark': {
        type: 'raster',
        tiles: [
          'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
          'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
          'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        ],
        tileSize: 256,
        attribution: 'Â© OpenStreetMap contributors Â© CARTO',
      },
      'carto-labels': {
        type: 'raster',
        tiles: [
          'https://a.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}.png',
          'https://b.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}.png',
          'https://c.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}.png',
        ],
        tileSize: 256,
      },
    },
    layers: [
      { id: 'background', type: 'background', paint: { 'background-color': '#05070c' } },
      { id: layerIds.basemap, type: 'raster', source: 'carto-dark', paint: { 'raster-opacity': 1 } },
      { id: layerIds.labels, type: 'raster', source: 'carto-labels', paint: { 'raster-opacity': 0.72 } },
    ],
  };
}

export function MapViewport({
  terrain,
  roads,
  buildings,
  waterways,
  activeOverlay,
  simulation,
  currentStep,
  layers,
  threeD,
  onInspect,
}: MapViewportProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const readyRef = useRef(false);
  const phaseRef = useRef(0);
  const coordinates = useMemo(() => rasterCoordinates(terrain), [terrain]);

  const flyToBookmark = (bookmark: keyof typeof mumbaiBookmarks) => {
    const mapInstance = mapRef.current;
    if (!mapInstance) {
      return;
    }

    mapInstance.flyTo({
      ...mumbaiBookmarks[bookmark],
      duration: 900,
      essential: true,
    });
  };

  const fitProjectBounds = () => {
    const mapInstance = mapRef.current;
    if (!mapInstance) {
      return;
    }

    mapInstance.fitBounds([coordinates[3], coordinates[1]], {
      padding: { top: 110, right: 420, bottom: 170, left: 380 },
      duration: 900,
      pitch: threeD ? 58 : 0,
      bearing: threeD ? -28 : 0,
    });
  };

  useEffect(() => {
    if (!containerRef.current) {
      return undefined;
    }

    const mapInstance = new maplibregl.Map({
      container: containerRef.current,
      style: buildBasemapStyle(),
      center: terrainCenter(terrain),
      zoom: 11,
      pitch: 0,
      bearing: 0,
      minZoom: 8,
      maxZoom: 19,
      attributionControl: { compact: true },
    });

    mapRef.current = mapInstance;
    mapInstance.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');
    mapInstance.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');

    const setup = () => {
      const hillshadeCanvas = renderTerrainRaster(terrain, 'hillshade');
      const terrainCanvas = renderTerrainRaster(terrain, activeTerrainLayer(activeOverlay));
      const waterCanvas = renderWaterRaster(simulation?.depth_history[currentStep] ?? null, phaseRef.current);

      mapInstance.addSource(sourceIds.hillshade, {
        type: 'image',
        url: hillshadeCanvas.toDataURL('image/png'),
        coordinates,
      });
      mapInstance.addLayer({
        id: layerIds.hillshade,
        type: 'raster',
        source: sourceIds.hillshade,
        paint: {
          'raster-opacity': layerEnabled(layers, 'hillshade') ? layerOpacity(layers, 'hillshade') : 0,
          'raster-fade-duration': 180,
          'raster-resampling': 'linear',
        },
      });

      mapInstance.addSource(sourceIds.terrain, {
        type: 'image',
        url: terrainCanvas.toDataURL('image/png'),
        coordinates,
      });
      mapInstance.addLayer({
        id: layerIds.terrain,
        type: 'raster',
        source: sourceIds.terrain,
        paint: {
          'raster-opacity': layerEnabled(layers, activeTerrainLayer(activeOverlay)) ? layerOpacity(layers, activeTerrainLayer(activeOverlay)) : 0,
          'raster-fade-duration': 180,
          'raster-resampling': 'linear',
        },
      });

      mapInstance.addSource(sourceIds.water, {
        type: 'image',
        url: waterCanvas.toDataURL('image/png'),
        coordinates,
      });
      mapInstance.addLayer({
        id: layerIds.water,
        type: 'raster',
        source: sourceIds.water,
        paint: {
          'raster-opacity': layerEnabled(layers, 'floodDepth') ? layerOpacity(layers, 'floodDepth') : 0,
          'raster-fade-duration': 80,
          'raster-resampling': 'linear',
        },
      });

      mapInstance.addSource(sourceIds.roads, { type: 'geojson', data: roads, promoteId: 'id' });
      mapInstance.addLayer({
        id: layerIds.roads,
        type: 'line',
        source: sourceIds.roads,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': '#e5e7eb',
          'line-width': ['interpolate', ['linear'], ['zoom'], 9, 0.45, 13, 1.8, 16, 4.2],
          'line-opacity': layerOpacity(layers, 'roads'),
          'line-blur': 0.15,
        },
      });

      mapInstance.addSource(sourceIds.buildings, { type: 'geojson', data: buildings, promoteId: 'id' });
      mapInstance.addLayer({
        id: layerIds.buildings,
        type: 'fill-extrusion',
        source: sourceIds.buildings,
        paint: {
          'fill-extrusion-color': [
            'match',
            ['get', 'type'],
            'commercial', '#fbbf24',
            'industrial', '#60a5fa',
            'residential', '#cbd5e1',
            '#94a3b8',
          ],
          'fill-extrusion-height': [
            'case',
            ['boolean', ['get', 'extrude'], false],
            ['coalesce', ['to-number', ['get', 'height']], 18],
            threeD ? ['coalesce', ['to-number', ['get', 'height']], 16] : 0,
          ],
          'fill-extrusion-base': 0,
          'fill-extrusion-opacity': layerOpacity(layers, 'buildings'),
        },
      });

      mapInstance.addSource(sourceIds.waterways, { type: 'geojson', data: waterways });
      mapInstance.addLayer({
        id: layerIds.waterways,
        type: 'line',
        source: sourceIds.waterways,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': '#38bdf8',
          'line-width': ['interpolate', ['linear'], ['zoom'], 9, 1.2, 13, 3.2, 16, 7],
          'line-opacity': layerOpacity(layers, 'waterways'),
          'line-blur': 0.35,
        },
      });

      mapInstance.on('click', (event) => {
        onInspect(inspectCell(
          terrain,
          simulation?.depth_history[currentStep] ?? null,
          event.lngLat.lng,
          event.lngLat.lat,
        ));
      });

      readyRef.current = true;
      setTimeout(() => {
        mapInstance.resize();
        fitProjectBounds();
      }, 120);
    };

    mapInstance.on('load', setup);
    return () => {
      readyRef.current = false;
      mapInstance.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const mapInstance = mapRef.current;
    if (!mapInstance || !readyRef.current) {
      return;
    }

    const overlayLayer = activeTerrainLayer(activeOverlay);
    const terrainCanvas = renderTerrainRaster(terrain, overlayLayer);
    const terrainSource = mapInstance.getSource(sourceIds.terrain) as maplibregl.ImageSource | undefined;
    terrainSource?.updateImage({ url: terrainCanvas.toDataURL('image/png'), coordinates });

    if (mapInstance.getLayer(layerIds.terrain)) {
      mapInstance.setPaintProperty(
        layerIds.terrain,
        'raster-opacity',
        layerEnabled(layers, overlayLayer) ? layerOpacity(layers, overlayLayer) : 0,
      );
    }
  }, [activeOverlay, coordinates, layers, terrain]);

  useEffect(() => {
    const mapInstance = mapRef.current;
    if (!mapInstance || !readyRef.current) {
      return undefined;
    }

    let animationFrame = 0;
    const updateWater = () => {
      phaseRef.current += 0.16;
      const waterCanvas = renderWaterRaster(simulation?.depth_history[currentStep] ?? null, phaseRef.current);
      const waterSource = mapInstance.getSource(sourceIds.water) as maplibregl.ImageSource | undefined;
      waterSource?.updateImage({ url: waterCanvas.toDataURL('image/png'), coordinates });
    };

    updateWater();
    if (simulation) {
      const animate = () => {
        updateWater();
        animationFrame = window.requestAnimationFrame(animate);
      };
      animationFrame = window.requestAnimationFrame(animate);
    }

    return () => window.cancelAnimationFrame(animationFrame);
  }, [currentStep, simulation, coordinates]);

  useEffect(() => {
    const mapInstance = mapRef.current;
    if (!mapInstance || !readyRef.current) {
      return;
    }

    if (mapInstance.getLayer(layerIds.basemap)) {
      mapInstance.setPaintProperty(layerIds.basemap, 'raster-opacity', layerEnabled(layers, 'basemap') ? layerOpacity(layers, 'basemap') : 0);
      mapInstance.setPaintProperty(layerIds.labels, 'raster-opacity', layerEnabled(layers, 'basemap') ? Math.min(0.82, layerOpacity(layers, 'basemap')) : 0);
    }
    if (mapInstance.getLayer(layerIds.hillshade)) {
      mapInstance.setPaintProperty(layerIds.hillshade, 'raster-opacity', layerEnabled(layers, 'hillshade') ? layerOpacity(layers, 'hillshade') : 0);
    }
    if (mapInstance.getLayer(layerIds.water)) {
      mapInstance.setPaintProperty(layerIds.water, 'raster-opacity', layerEnabled(layers, 'floodDepth') ? layerOpacity(layers, 'floodDepth') : 0);
    }
    if (mapInstance.getLayer(layerIds.roads)) {
      mapInstance.setLayoutProperty(layerIds.roads, 'visibility', layerEnabled(layers, 'roads') ? 'visible' : 'none');
      mapInstance.setPaintProperty(layerIds.roads, 'line-opacity', layerOpacity(layers, 'roads'));
    }
    if (mapInstance.getLayer(layerIds.buildings)) {
      mapInstance.setLayoutProperty(layerIds.buildings, 'visibility', layerEnabled(layers, 'buildings') ? 'visible' : 'none');
      mapInstance.setPaintProperty(layerIds.buildings, 'fill-extrusion-opacity', layerOpacity(layers, 'buildings'));
    }
    if (mapInstance.getLayer(layerIds.waterways)) {
      mapInstance.setLayoutProperty(layerIds.waterways, 'visibility', layerEnabled(layers, 'waterways') ? 'visible' : 'none');
      mapInstance.setPaintProperty(layerIds.waterways, 'line-opacity', layerOpacity(layers, 'waterways'));
    }
  }, [layers]);

  useEffect(() => {
    const mapInstance = mapRef.current;
    if (!mapInstance) {
      return;
    }

    mapInstance.easeTo({
      pitch: threeD ? 62 : 0,
      bearing: threeD ? -34 : 0,
      duration: 900,
    });

    if (mapInstance.getLayer(layerIds.buildings)) {
      mapInstance.setPaintProperty(layerIds.buildings, 'fill-extrusion-height', threeD
        ? ['coalesce', ['to-number', ['get', 'height']], 16]
        : 0);
    }
  }, [threeD]);

  return (
    <section className="map-stage">
      <div ref={containerRef} className="map-container" />
      <div className="map-hud top-left">
        <span><Map size={14} /> Mumbai basemap</span>
        <span><Crosshair size={14} /> Copernicus DEM</span>
      </div>
      <div className="map-hud top-right-local">
        <span><Layers3 size={14} /> {threeD ? '3D tilted GIS view' : '2D GIS operations view'}</span>
        <span><Ruler size={14} /> Real project layers</span>
      </div>
      <div className="map-control-panel" aria-label="Map navigation shortcuts">
        <button type="button" onClick={fitProjectBounds} title="Fit to Mumbai"><Home size={15} /> Mumbai</button>
        <button type="button" onClick={() => flyToBookmark('mumbai')} title="Reset camera"><Navigation size={15} /> Reset</button>
        <button type="button" onClick={() => flyToBookmark('bkc')} title="Locate BKC"><Building2 size={15} /> BKC</button>
        <button type="button" onClick={() => flyToBookmark('kurla')} title="Locate Kurla"><LocateFixed size={15} /> Kurla</button>
        <button type="button" onClick={() => flyToBookmark('mithi')} title="Locate Mithi River"><Waves size={15} /> Mithi</button>
      </div>
      <div className="depth-legend">
        <div className="legend-ramp" />
        <div className="legend-labels">
          <span>0 m</span>
          <span>0.5</span>
          <span>1.5</span>
          <span>3 m+</span>
        </div>
        <strong><Waves size={14} /> Flood depth</strong>
      </div>
    </section>
  );
}