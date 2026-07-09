import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { 
  Layers, Compass, Activity, Database, Info, 
  Eye, EyeOff, RefreshCw, AlertCircle, Play, Pause, RotateCcw, Droplets 
} from 'lucide-react';

interface TerrainData {
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

export default function MapDashboard() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  
  // Data states
  const [terrain, setTerrain] = useState<TerrainData | null>(null);
  const [roadsGeoJSON, setRoadsGeoJSON] = useState<any>(null);
  const [buildingsGeoJSON, setBuildingsGeoJSON] = useState<any>(null);
  const [waterwaysGeoJSON, setWaterwaysGeoJSON] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // UI Selection states
  const [activeOverlay, setActiveOverlay] = useState<'none' | 'elevation' | 'slope' | 'aspect' | 'flow_accumulation' | 'water_depth'>('elevation');
  const [showRoads, setShowRoads] = useState(true);
  const [showBuildings, setShowBuildings] = useState(true);
  const [showWaterways, setShowWaterways] = useState(true);
  
  // Simulation states
  const [rainfallIntensity, setRainfallIntensity] = useState<number>(30); // mm/hr
  const [rainfallDuration, setRainfallDuration] = useState<number>(4); // hours
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simulationData, setSimulationData] = useState<{
    metadata: {
      width: number;
      height: number;
      crs: string;
      transform: number[];
    };
    time_steps_min: number;
    rainfall_hyetograph_mm: number[];
    depth_history: number[][][]; // [step][row][col]
  } | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [isStyleReady, setIsStyleReady] = useState<boolean>(false);

  // Mappings to track which features belong to which grid cells
  const [roadGridMappings, setRoadGridMappings] = useState<{ id: number, r: number, c: number }[]>([]);
  const [buildingGridMappings, setBuildingGridMappings] = useState<{ id: number, r: number, c: number }[]>([]);

  // Hover information
  const [hoveredCell, setHoveredCell] = useState<{
    lat: number;
    lng: number;
    elevation: number;
    slope: number;
    aspect: number;
    flowAcc: number;
    row: number;
    col: number;
    waterDepth?: number;
  } | null>(null);

  // Fetch terrain and load map layers
  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const [terrainRes, roadsRes, buildingsRes, waterwaysRes] = await Promise.all([
          fetch('/api/terrain'),
          fetch('/api/roads'),
          fetch('/api/buildings'),
          fetch('/api/waterways')
        ]);
        
        if (!terrainRes.ok) throw new Error('Failed to fetch terrain data');
        const terrainData = await terrainRes.json();
        
        const roadsData = roadsRes.ok ? await roadsRes.json() : { type: 'FeatureCollection', features: [] };
        const buildingsData = buildingsRes.ok ? await buildingsRes.json() : { type: 'FeatureCollection', features: [] };
        const waterwaysData = waterwaysRes.ok ? await waterwaysRes.json() : { type: 'FeatureCollection', features: [] };
        
        // Add ID to each feature for setFeatureState compatibility
        // Add ID at both feature level AND properties level for promoteId: 'id' compatibility
        roadsData.features = roadsData.features.map((f: any, idx: number) => ({ 
          ...f, id: idx, properties: { ...f.properties, id: idx } 
        }));
        buildingsData.features = buildingsData.features.map((f: any, idx: number) => ({ 
          ...f, id: idx, properties: { ...f.properties, id: idx } 
        }));
        
        setTerrain(terrainData);
        setRoadsGeoJSON(roadsData);
        setBuildingsGeoJSON(buildingsData);
        setWaterwaysGeoJSON(waterwaysData);
      } catch (err: any) {
        setError(err.message || 'Error loading digital twin layers');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  // Map initialization - wait for all datasets to load
  useEffect(() => {
    if (!mapContainer.current || !terrain || !roadsGeoJSON || !buildingsGeoJSON || !waterwaysGeoJSON) return;

    // Center coordinates from transform: lon_start = transform[2], lat_start = transform[5]
    // Let's compute center of grid:
    const dx = terrain.transform[0];
    const dy = terrain.transform[4];
    const lonStart = terrain.transform[2];
    const latStart = terrain.transform[5];
    const centerLng = lonStart + (terrain.width * dx) / 2;
    const centerLat = latStart + (terrain.height * dy) / 2;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [centerLng, centerLat],
      zoom: 11,      // wider zoom for full Mumbai extent (was 13.5 for tiny test grid)
      pitch: 20,
      maxZoom: 18,
      minZoom: 8
    });

    // Force map resize after DOM settles to prevent 0x0 canvas collapse in flex layout
    setTimeout(() => {
      if (map.current) {
        map.current.resize();
      }
    }, 100);

    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');

    const setupLayers = () => {
      if (!map.current || !terrain) return;

      // Ensure map recalculates size when style is loaded
      map.current.resize();

      // 1. Generate client-side grid for terrain raster overlays
      const gridGeoJSON = generateGridGeoJSON(terrain);
      
      map.current.addSource('terrain-grid', {
        type: 'geojson',
        data: gridGeoJSON,
        promoteId: 'id'
      });

      // Add Terrain raster overlay layer
      map.current.addLayer({
        id: 'terrain-layer',
        type: 'fill',
        source: 'terrain-grid',
        paint: {
          'fill-color': ['get', 'elevation_color'],
          'fill-opacity': 0.65,
          'fill-outline-color': 'rgba(255, 255, 255, 0.05)'
        }
      });

      // Add Dynamic Water Depth layer — transparent for shallow, vivid for deep flood
      map.current.addLayer({
        id: 'water-layer',
        type: 'fill',
        source: 'terrain-grid',
        paint: {
          // Color: invisible → light blue → deep navy
          'fill-color': [
            'interpolate', ['linear'],
            ['number', ['feature-state', 'water_depth'], 0],
            0,    'rgba(0, 0, 0, 0)',
            0.01, 'rgba(125, 211, 252, 0.15)',  // barely visible (< 1cm)
            0.05, 'rgba(56, 189, 248, 0.40)',   // light sky blue (~5cm)
            0.15, 'rgba(14, 165, 233, 0.65)',   // sky-500 (~15cm)
            0.40, 'rgba(2, 132, 199, 0.80)',    // sky-600 (~40cm)
            1.00, 'rgba(3, 105, 161, 0.90)',    // sky-700 (1m)
            2.50, 'rgba(30, 58, 138, 0.95)'     // blue-900 (>2.5m extreme)
          ],
          // Opacity: make shallow cells barely-there so street labels still show
          'fill-opacity': [
            'interpolate', ['linear'],
            ['number', ['feature-state', 'water_depth'], 0],
            0,    0,
            0.01, 0.15,
            0.05, 0.55,
            0.20, 0.80,
            1.00, 0.92
          ]
        }
      });

      // 2. Add vector layers
      // Roads
      map.current.addSource('roads-source', {
        type: 'geojson',
        data: roadsGeoJSON || { type: 'FeatureCollection', features: [] },
        promoteId: 'id'
      });
      map.current.addLayer({
        id: 'roads-layer',
        type: 'line',
        source: 'roads-source',
        layout: {
          'line-join': 'round',
          'line-cap': 'round'
        },
        paint: {
          'line-color': [
            'case',
            ['boolean', ['feature-state', 'flooded'], false],
            '#ff3838', // bright red when flooded
            '#64748b'  // normal slate-500 road gray
          ],
          'line-width': [
            'case',
            ['boolean', ['feature-state', 'flooded'], false],
            6,
            3
          ],
          'line-opacity': 0.8
        }
      });

      // Waterways
      map.current.addSource('waterways-source', {
        type: 'geojson',
        data: waterwaysGeoJSON || { type: 'FeatureCollection', features: [] }
      });
      map.current.addLayer({
        id: 'waterways-layer',
        type: 'line',
        source: 'waterways-source',
        layout: {
          'line-join': 'round',
          'line-cap': 'round'
        },
        paint: {
          'line-color': '#00d2d3',
          'line-width': 4,
          'line-opacity': 0.9
        }
      });

      // Buildings
      map.current.addSource('buildings-source', {
        type: 'geojson',
        data: buildingsGeoJSON || { type: 'FeatureCollection', features: [] },
        promoteId: 'id'
      });
      map.current.addLayer({
        id: 'buildings-layer',
        type: 'fill-extrusion',
        source: 'buildings-source',
        paint: {
          'fill-extrusion-color': [
            'case',
            ['boolean', ['feature-state', 'flooded'], false],
            '#f87171', // flooded red-400 highlight
            [
              'match',
              ['get', 'type'],
              'residential', '#1e90ff',
              'commercial', '#ffa502',
              'industrial', '#70a1ff',
              '#ffffff'
            ]
          ],
          'fill-extrusion-height': [
            'match',
            ['get', 'type'],
            'residential', 15,
            'commercial', 35,
            'industrial', 20,
            10
          ],
          'fill-extrusion-opacity': 0.85
        }
      });

      // 3. Hover interactivity on terrain grid
      let hoveredFeatureId: number | null = null;
      
      map.current.on('mousemove', 'terrain-layer', (e) => {
        if (!e.features || e.features.length === 0 || !map.current) return;
        
        const feature = e.features[0];
        const properties = feature.properties;
        const id = feature.id as number;

        if (hoveredFeatureId !== null) {
          map.current.setFeatureState(
            { source: 'terrain-grid', id: hoveredFeatureId },
            { hover: false }
          );
        }
        
        hoveredFeatureId = id;
        map.current.setFeatureState(
          { source: 'terrain-grid', id: hoveredFeatureId },
          { hover: true }
        );

        const lngLat = e.lngLat;
        const r = properties.row;
        const c = properties.col;
        const depthGrid = simulationDataRef.current?.depth_history?.[currentStepRef.current] || null;
        const waterDepth = depthGrid ? depthGrid[r]?.[c] : undefined;

        setHoveredCell({
          lat: lngLat.lat,
          lng: lngLat.lng,
          elevation: properties.elevation,
          slope: properties.slope,
          aspect: properties.aspect,
          flowAcc: properties.flow_accumulation,
          row: r,
          col: c,
          waterDepth
        });
      });

      map.current.on('mouseleave', 'terrain-layer', () => {
        if (hoveredFeatureId !== null && map.current) {
          map.current.setFeatureState(
            { source: 'terrain-grid', id: hoveredFeatureId },
            { hover: false }
          );
          hoveredFeatureId = null;
        }
        setHoveredCell(null);
      });

      // Mark style as ready and loaded
      setIsStyleReady(true);
    };

    if (map.current.isStyleLoaded()) {
      setupLayers();
    } else {
      map.current.on('load', setupLayers);
    }

    return () => {
      setIsStyleReady(false);
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [terrain, roadsGeoJSON, buildingsGeoJSON, waterwaysGeoJSON]);

  // Effect to handle toggling vector layers visibility
  useEffect(() => {
    if (!map.current) return;
    const layers = [
      { id: 'roads-layer', visible: showRoads },
      { id: 'buildings-layer', visible: showBuildings },
      { id: 'waterways-layer', visible: showWaterways }
    ];
    
    layers.forEach(({ id, visible }) => {
      try {
        if (map.current?.getLayer(id)) {
          map.current.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
        }
      } catch (e) {
        console.warn(`Layer ${id} not ready yet.`);
      }
    });
  }, [showRoads, showBuildings, showWaterways]);

  // Synchronize playback states to refs to avoid stale closures in MapLibre event listeners
  const currentStepRef = useRef(currentStep);
  const simulationDataRef = useRef(simulationData);

  useEffect(() => {
    currentStepRef.current = currentStep;
  }, [currentStep]);

  useEffect(() => {
    simulationDataRef.current = simulationData;
  }, [simulationData]);

  // Pre-calculate which grid cell each road and building feature falls into
  useEffect(() => {
    if (!terrain || !roadsGeoJSON || !buildingsGeoJSON) return;

    const dx = terrain.transform[0];
    const dy = terrain.transform[4];
    const lonStart = terrain.transform[2];
    const latStart = terrain.transform[5];

    const getCell = (coords: number[]) => {
      const lon = coords[0];
      const lat = coords[1];
      const c = Math.floor((lon - lonStart) / dx);
      const r = Math.floor((lat - latStart) / dy);
      return { 
        r: Math.max(0, Math.min(terrain.height - 1, r)), 
        c: Math.max(0, Math.min(terrain.width - 1, c)) 
      };
    };

    const roadsMap = roadsGeoJSON.features.map((f: any) => {
      let coords = [0, 0];
      if (f.geometry.type === 'LineString') {
        coords = f.geometry.coordinates[0];
      } else if (f.geometry.type === 'Point') {
        coords = f.geometry.coordinates;
      }
      return { id: f.id, ...getCell(coords) };
    });

    const buildingsMap = buildingsGeoJSON.features.map((f: any) => {
      let coords = [0, 0];
      if (f.geometry.type === 'Polygon') {
        coords = f.geometry.coordinates[0][0];
      } else if (f.geometry.type === 'Point') {
        coords = f.geometry.coordinates;
      }
      return { id: f.id, ...getCell(coords) };
    });

    setRoadGridMappings(roadsMap);
    setBuildingGridMappings(buildingsMap);
  }, [terrain, roadsGeoJSON, buildingsGeoJSON]);

  // Update dynamic feature states (water depth & flooded status) when simulation step changes
  useEffect(() => {
    const mapInstance = map.current;
    if (!mapInstance || !terrain || !isStyleReady) return;

    const depthGrid = simulationData?.depth_history?.[currentStep] || null;

    // 1. Update grid cells water_depth
    for (let r = 0; r < terrain.height; r++) {
      for (let c = 0; c < terrain.width; c++) {
        const depth = depthGrid ? depthGrid[r][c] : 0;
        mapInstance.setFeatureState(
          { source: 'terrain-grid', id: r * terrain.width + c },
          { water_depth: depth }
        );
      }
    }

    // 2. Update roads flooded state
    roadGridMappings.forEach(feat => {
      const depth = depthGrid ? depthGrid[feat.r]?.[feat.c] : 0;
      mapInstance.setFeatureState(
        { source: 'roads-source', id: feat.id },
        { flooded: depth > 0.1 }
      );
    });

    // 3. Update buildings flooded state
    buildingGridMappings.forEach(feat => {
      const depth = depthGrid ? depthGrid[feat.r]?.[feat.c] : 0;
      mapInstance.setFeatureState(
        { source: 'buildings-source', id: feat.id },
        { flooded: depth > 0.1 }
      );
    });
  }, [currentStep, simulationData, roadGridMappings, buildingGridMappings, terrain, isStyleReady]);

  // Simulation run / reset trigger methods
  const handleRunSimulation = async () => {
    try {
      setIsSimulating(true);
      setError(null);
      const res = await fetch('/api/simulation/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          duration_hours: rainfallDuration,
          intensity_mm_hr: rainfallIntensity,
          time_step_min: 15
        })
      });
      if (!res.ok) throw new Error('Simulation execution failed');
      const data = await res.json();
      setSimulationData(data);
      setCurrentStep(0);
      setActiveOverlay('water_depth');
    } catch (err: any) {
      setError(err.message || 'Error running simulation');
    } finally {
      setIsSimulating(false);
    }
  };

  const handleResetSimulation = async () => {
    try {
      await fetch('/api/simulation/reset', { method: 'POST' });
      setSimulationData(null);
      setCurrentStep(0);
      setIsPlaying(false);
      setActiveOverlay('elevation');
    } catch (err: any) {
      console.error('Reset error:', err);
    }
  };

  // Playback timer interval
  useEffect(() => {
    let intervalId: any = null;
    if (isPlaying && simulationData) {
      intervalId = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= simulationData.depth_history.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 500); // 500ms per step
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isPlaying, simulationData]);

  // Effect to handle water layer visibility
  useEffect(() => {
    if (!map.current) return;
    try {
      if (map.current.getLayer('water-layer')) {
        const isVisible = activeOverlay === 'water_depth' || simulationData !== null;
        map.current.setLayoutProperty('water-layer', 'visibility', isVisible ? 'visible' : 'none');
      }
    } catch (e) {
      console.warn("Water layer not ready yet.");
    }
  }, [activeOverlay, simulationData]);

  // Effect to update paint properties based on selected overlay
  useEffect(() => {
    if (!map.current || !terrain) return;
    try {
      if (map.current.getLayer('terrain-layer')) {
        if (activeOverlay === 'none' || activeOverlay === 'water_depth') {
          map.current.setLayoutProperty('terrain-layer', 'visibility', 'none');
        } else {
          map.current.setLayoutProperty('terrain-layer', 'visibility', 'visible');
          map.current.setPaintProperty(
            'terrain-layer',
            'fill-color',
            ['get', `${activeOverlay}_color`]
          );
        }
      }
    } catch (e) {
      console.warn("Terrain layer not ready yet.");
    }
  }, [activeOverlay, terrain]);

  // Client-side GeoJSON creation from DEM grid
  const generateGridGeoJSON = (data: TerrainData) => {
    const dx = data.transform[0];
    const dy = data.transform[4];
    const lonStart = data.transform[2];
    const latStart = data.transform[5];
    
    const features = [];
    let id = 0;
    
    // Find min/max for color scaling
    let maxElev = 1.0;
    let maxSlope = 1.0;
    let maxFlow = 1.0;
    
    for (let r = 0; r < data.height; r++) {
      for (let c = 0; c < data.width; c++) {
        maxElev = Math.max(maxElev, data.elevation[r][c]);
        maxSlope = Math.max(maxSlope, data.slope[r][c]);
        maxFlow = Math.max(maxFlow, data.flow_accumulation[r][c]);
      }
    }

    for (let r = 0; r < data.height; r++) {
      for (let c = 0; c < data.width; c++) {
        const x1 = lonStart + c * dx;
        const y1 = latStart + r * dy;
        const x2 = lonStart + (c + 1) * dx;
        const y2 = latStart + (r + 1) * dy;
        
        const poly = [
          [x1, y1],
          [x2, y1],
          [x2, y2],
          [x1, y2],
          [x1, y1]
        ];
        
        const elevationVal = data.elevation[r][c];
        const slopeVal = data.slope[r][c];
        const aspectVal = data.aspect[r][c];
        const flowAccVal = data.flow_accumulation[r][c];

        // Color calculations
        // 1. Elevation color (Green to Brown gradient)
        const elevPct = elevationVal / maxElev;
        const elevHue = 120 - elevPct * 100; // 120 (green) -> 20 (brownish/orange)
        const elevation_color = `hsl(${elevHue}, 70%, 40%)`;

        // 2. Slope color (Green to Red gradient)
        const slopePct = Math.min(slopeVal / 45, 1.0);
        const slopeHue = 120 - slopePct * 120; // 120 (flat green) -> 0 (steep red)
        const slope_color = `hsl(${slopeHue}, 80%, 45%)`;

        // 3. Aspect color (360 compass direction)
        let aspect_color = 'rgba(100, 100, 100, 0.2)'; // flat
        if (aspectVal >= 0) {
          aspect_color = `hsl(${aspectVal}, 75%, 50%)`;
        }

        // 4. Flow Accumulation (Electric cyan stream channels)
        const logAcc = Math.log10(Math.max(flowAccVal, 1));
        const flowPct = logAcc / Math.log10(maxFlow);
        // Channels with high flow accumulation are rendered bright cyan
        let flow_accumulation_color = 'rgba(0, 0, 0, 0)';
        if (flowPct > 0.4) {
          flow_accumulation_color = `hsla(180, 100%, 50%, ${Math.min(flowPct, 0.9)})`;
        }

        features.push({
          type: "Feature",
          id: id,
          properties: {
            id: id,  // MUST be in properties for promoteId: 'id' to work with setFeatureState
            row: r,
            col: c,
            elevation: elevationVal,
            slope: slopeVal,
            aspect: aspectVal,
            flow_accumulation: flowAccVal,
            elevation_color,
            slope_color,
            aspect_color,
            flow_accumulation_color
          },
          geometry: {
            type: "Polygon",
            coordinates: [poly]
          }
        });
        id++; // increment after push
      }
    }
    
    return {
      type: "FeatureCollection",
      features
    };
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-slate-950 text-slate-100">
        <RefreshCw className="w-12 h-12 text-teal-400 animate-spin mb-4" />
        <p className="text-lg font-medium tracking-wide">Processing Terrain Data...</p>
        <p className="text-sm text-slate-500 mt-1">Calculating slope, aspect, D8 routing maps...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-slate-950 text-slate-100 p-6 text-center">
        <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
        <h2 className="text-2xl font-bold mb-2">Terrain Loading Error</h2>
        <p className="text-slate-400 max-w-md mb-6">{error}</p>
        <button 
          onClick={() => window.location.reload()} 
          className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg flex items-center gap-2 transition"
        >
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex w-full h-screen bg-slate-950 font-sans overflow-hidden text-slate-100">
      
      {/* Glassmorphic Control Panel Sidebar */}
      <aside className="w-96 shrink-0 flex flex-col bg-slate-950/80 backdrop-blur-xl border-r border-slate-800/80 p-6 z-10 overflow-y-auto">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-teal-500/20 rounded-lg text-teal-400 border border-teal-500/30">
            <Activity className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">Mumbai Digital Twin</h1>
            <p className="text-xs text-slate-400 font-medium tracking-wider uppercase">Phase 2: Flood Simulator</p>
          </div>
        </div>

        {/* Dynamic Overlays Selection */}
        <section className="mb-6">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
            <Layers className="w-4 h-4 text-teal-400" /> Overlays Manager
          </h2>
          <div className="grid grid-cols-1 gap-2">
            {[
              { id: 'none', label: 'No Overlay', desc: 'Base Map Only' },
              { id: 'elevation', label: 'Elevation Grid', desc: 'Elevation heights (Green-Brown)' },
              { id: 'slope', label: 'Slope Analysis', desc: 'Slope gradient (Flat-Steep)' },
              { id: 'aspect', label: 'Aspect compass', desc: 'Terrain slope orientation' },
              { id: 'flow_accumulation', label: 'Flow Accumulation', desc: 'Runoff streams channels (Cyan)' },
              { id: 'water_depth', label: 'Flood Depth', desc: 'Water depth (Light-Dark Blue)' }
            ].map(item => (
              <button
                key={item.id}
                onClick={() => setActiveOverlay(item.id as any)}
                className={`flex flex-col text-left p-3 rounded-xl border transition ${
                  activeOverlay === item.id 
                    ? 'bg-teal-500/10 border-teal-500/40 text-teal-300 shadow-[0_0_15px_rgba(20,184,166,0.1)]' 
                    : 'bg-slate-900/50 border-slate-800 hover:bg-slate-900 text-slate-300'
                }`}
              >
                <div className="font-semibold text-sm">{item.label}</div>
                <div className="text-xs text-slate-400 mt-0.5">{item.desc}</div>
              </button>
            ))}
          </div>
        </section>

        {/* Vector Layers Visibility Toggles */}
        <section className="mb-6 border-t border-slate-800/80 pt-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
            <Database className="w-4 h-4 text-teal-400" /> GIS Layers (OSM)
          </h2>
          <div className="space-y-2">
            {[
              { id: 'roads', label: 'Road Network', state: showRoads, setState: setShowRoads, color: 'bg-red-500' },
              { id: 'waterways', label: 'Mithi River System', state: showWaterways, setState: setShowWaterways, color: 'bg-cyan-500' },
              { id: 'buildings', label: 'Building Footprints (3D)', state: showBuildings, setState: setShowBuildings, color: 'bg-amber-500' }
            ].map(layer => (
              <div 
                key={layer.id}
                onClick={() => layer.setState(!layer.state)}
                className="flex items-center justify-between p-3 bg-slate-900/50 hover:bg-slate-900 border border-slate-800/80 rounded-xl cursor-pointer transition"
              >
                <div className="flex items-center gap-2.5">
                  <span className={`w-2.5 h-2.5 rounded-full ${layer.color}`} />
                  <span className="text-sm font-medium text-slate-200">{layer.label}</span>
                </div>
                <button className="text-slate-400 hover:text-white transition">
                  {layer.state ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                </button>
              </div>
            ))}
          </div>
        </section>

        {/* Dynamic Flood Simulation Section */}
        <section className="mb-6 border-t border-slate-800/80 pt-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-teal-400" /> Flood Simulation
          </h2>
          
          {!simulationData ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">Rainfall Intensity:</span>
                  <span className="font-semibold text-teal-400">{rainfallIntensity} mm/hr</span>
                </div>
                <input 
                  type="range" 
                  min="10" 
                  max="150" 
                  step="10"
                  value={rainfallIntensity}
                  onChange={(e) => setRainfallIntensity(Number(e.target.value))}
                  className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-teal-500"
                />
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>10 (Light)</span>
                  <span>75 (Heavy)</span>
                  <span>150 (Extreme)</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">Storm Duration:</span>
                  <span className="font-semibold text-teal-400">{rainfallDuration} Hours</span>
                </div>
                <input 
                  type="range" 
                  min="1" 
                  max="12" 
                  step="1"
                  value={rainfallDuration}
                  onChange={(e) => setRainfallDuration(Number(e.target.value))}
                  className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-teal-500"
                />
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>1 Hr</span>
                  <span>6 Hrs</span>
                  <span>12 Hrs</span>
                </div>
              </div>

              <button
                onClick={handleRunSimulation}
                disabled={isSimulating}
                className="w-full py-2.5 bg-teal-600 hover:bg-teal-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition"
              >
                {isSimulating ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" /> Simulating...
                  </>
                ) : (
                  <>
                    <Droplets className="w-4 h-4" /> Run Flood Simulation
                  </>
                )}
              </button>
            </div>
          ) : (
            <div className="space-y-4 bg-slate-900/30 border border-slate-800/80 rounded-xl p-3">
              <div className="text-xs space-y-1.5 border-b border-slate-800/40 pb-2.5">
                <div className="flex justify-between">
                  <span className="text-slate-400">Storm Profile:</span>
                  <span className="font-semibold text-slate-200">{rainfallIntensity} mm/hr @ {rainfallDuration} hrs</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Active Step:</span>
                  <span className="font-bold text-teal-400">
                    Step {currentStep + 1} / {simulationData.depth_history.length} ({((currentStep * simulationData.time_steps_min) / 60).toFixed(2)} hrs)
                  </span>
                </div>
              </div>

              {/* Scrubber Slider */}
              <div className="space-y-1.5">
                <input 
                  type="range" 
                  min="0" 
                  max={simulationData.depth_history.length - 1} 
                  step="1"
                  value={currentStep}
                  onChange={(e) => {
                    setCurrentStep(Number(e.target.value));
                    setIsPlaying(false); // pause on manual scrub
                  }}
                  className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-teal-400"
                />
              </div>

              {/* Playback Button Group */}
              <div className="flex gap-2">
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="flex-1 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg flex items-center justify-center gap-1.5 transition text-xs font-semibold"
                >
                  {isPlaying ? (
                    <>
                      <Pause className="w-4 h-4 text-amber-400" /> Pause
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 text-emerald-400" /> Play
                    </>
                  )}
                </button>
                <button
                  onClick={() => {
                    setCurrentStep(0);
                    setIsPlaying(false);
                  }}
                  className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
                  title="Rewind"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
                <button
                  onClick={handleResetSimulation}
                  className="px-3 py-2 bg-red-950/30 hover:bg-red-900/40 text-red-400 border border-red-900/30 rounded-lg transition text-xs font-medium"
                >
                  Reset
                </button>
              </div>
            </div>
          )}
        </section>

        {/* Coordinate details panel */}
        <section className="mt-auto border-t border-slate-800/80 pt-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
            <Compass className="w-4 h-4 text-teal-400" /> Inspector / Query Tool
          </h2>
          <div className="bg-slate-900/40 border border-slate-800/60 rounded-xl p-3.5 space-y-2 text-xs">
            {hoveredCell ? (
              <>
                <div className="flex justify-between border-b border-slate-800/40 pb-1.5">
                  <span className="text-slate-400">Position:</span>
                  <span className="font-semibold text-slate-200">{hoveredCell.lng.toFixed(5)}°E, {hoveredCell.lat.toFixed(5)}°N</span>
                </div>
                <div className="flex justify-between border-b border-slate-800/40 pb-1.5">
                  <span className="text-slate-400">Elevation:</span>
                  <span className="font-bold text-teal-300">{hoveredCell.elevation.toFixed(1)} m</span>
                </div>
                {hoveredCell.waterDepth !== undefined && (
                  <div className="flex justify-between border-b border-slate-800/40 pb-1.5">
                    <span className="text-slate-400">Flood Depth:</span>
                    <span className="font-bold text-sky-400">
                      {hoveredCell.waterDepth > 0.05 ? `${hoveredCell.waterDepth.toFixed(2)} m` : 'Dry'}
                    </span>
                  </div>
                )}
                <div className="flex justify-between border-b border-slate-800/40 pb-1.5">
                  <span className="text-slate-400">Slope:</span>
                  <span className="font-semibold text-slate-200">{hoveredCell.slope.toFixed(2)}°</span>
                </div>
                <div className="flex justify-between border-b border-slate-800/40 pb-1.5">
                  <span className="text-slate-400">Aspect:</span>
                  <span className="font-semibold text-slate-200">{hoveredCell.aspect >= 0 ? `${hoveredCell.aspect.toFixed(0)}°` : 'Flat'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Flow Accumulation:</span>
                  <span className="font-semibold text-blue-300">{hoveredCell.flowAcc.toFixed(0)} cells</span>
                </div>
              </>
            ) : (
              <div className="text-slate-500 italic py-2 flex items-center gap-1.5">
                <Info className="w-4 h-4 text-slate-600" /> Hover cursor on terrain grid to inspect features
              </div>
            )}
          </div>
        </section>

        {/* Phase 2 Alert */}
        <div className="mt-4 p-3 bg-teal-950/20 border border-teal-800/30 rounded-xl text-xs text-teal-400 flex gap-2">
          <Info className="w-4 h-4 shrink-0 text-teal-500" />
          <span>Active flood model mapping. Play the simulation to watch runoff flow over roads, buildings, and terrain.</span>
        </div>
      </aside>

      <main className="flex-1" style={{ position: 'relative', height: '100%', minWidth: 0 }}>
        <div ref={mapContainer} className="w-full h-full" />
        
        {/* Dynamic Map Legend */}
        {activeOverlay !== 'none' && (
          <div className="bg-slate-950/90 backdrop-blur-md border border-slate-800 p-4 rounded-xl shadow-2xl w-56 text-xs" style={{ position: 'absolute', bottom: '24px', right: '24px', zIndex: 10 }}>
            <h3 className="font-semibold text-slate-200 mb-2 capitalize">{activeOverlay} Scale</h3>
            {activeOverlay === 'elevation' && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[hsl(20,70%,40%)] rounded-sm" />
                  <span className="text-slate-400 font-medium">Hills (~60m+)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[hsl(70,70%,40%)] rounded-sm" />
                  <span className="text-slate-400 font-medium">Mid-slope (~30m)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[hsl(120,70%,40%)] rounded-sm" />
                  <span className="text-slate-400 font-medium">Lowland / Coast (~2m)</span>
                </div>
              </div>
            )}
            {activeOverlay === 'slope' && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[hsl(0,80%,45%)] rounded-sm" />
                  <span className="text-slate-400 font-medium">Steep (&gt; 30°)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[hsl(60,80%,45%)] rounded-sm" />
                  <span className="text-slate-400 font-medium">Moderate (~15°)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[hsl(120,80%,45%)] rounded-sm" />
                  <span className="text-slate-400 font-medium">Flat (0°)</span>
                </div>
              </div>
            )}
            {activeOverlay === 'aspect' && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[hsl(0,75%,50%)] rounded-sm" />
                  <span className="text-slate-400 font-medium">North (0° / 360°)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[hsl(120,75%,50%)] rounded-sm" />
                  <span className="text-slate-400 font-medium">East (120°)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[hsl(240,75%,50%)] rounded-sm" />
                  <span className="text-slate-400 font-medium">West (240°)</span>
                </div>
              </div>
            )}
            {activeOverlay === 'flow_accumulation' && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[hsla(180,100%,50%,0.9)] rounded-sm animate-pulse" />
                  <span className="text-slate-400 font-medium">Stream/River Line</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[hsla(180,100%,50%,0.4)] rounded-sm" />
                  <span className="text-slate-400 font-medium">Runoff Channels</span>
                </div>
                <div className="text-[10px] text-slate-500 italic mt-2 border-t border-slate-800/40 pt-1">
                  Highlights cell paths with over 100 upslope cells draining.
                </div>
              </div>
            )}
            {activeOverlay === 'water_depth' && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[rgba(30,58,138,0.95)] rounded-sm" />
                  <span className="text-slate-400 font-medium">Extreme (&gt; 3.0m)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[rgba(2,132,199,0.8)] rounded-sm" />
                  <span className="text-slate-400 font-medium">High (1.5m - 3.0m)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[rgba(14,165,233,0.65)] rounded-sm" />
                  <span className="text-slate-400 font-medium">Moderate (0.5m - 1.5m)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="w-4 h-3 bg-[rgba(56,189,248,0.4)] rounded-sm" />
                  <span className="text-slate-400 font-medium">Low (0.05m - 0.5m)</span>
                </div>
                <div className="text-[10px] text-slate-500 italic mt-2 border-t border-slate-800/40 pt-1">
                  Red highlighted roads and buildings indicate flooded infrastructure.
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
