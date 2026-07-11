import { useEffect, useMemo, useState } from 'react';
import { defaultLayers } from '../features/digitalTwin/catalog';
import type { LayerNode, TerrainOverlay, WorkspaceMode } from '../features/digitalTwin/types';

const storageKey = 'mumbai-flood-digital-twin-workspace';

export interface WorkspaceState {
  mode: WorkspaceMode;
  leftCollapsed: boolean;
  rightCollapsed: boolean;
  bottomCollapsed: boolean;
  commandOpen: boolean;
  activeOverlay: TerrainOverlay;
  threeD: boolean;
  selectedScenario: string;
  layers: LayerNode[];
}

const initialWorkspace: WorkspaceState = {
  mode: 'research',
  leftCollapsed: false,
  rightCollapsed: false,
  bottomCollapsed: false,
  commandOpen: false,
  activeOverlay: 'dem',
  threeD: false,
  selectedScenario: 'synthetic',
  layers: defaultLayers,
};

function mergeStoredLayers(storedLayers: LayerNode[] | undefined): LayerNode[] {
  if (!storedLayers?.length) {
    return defaultLayers;
  }

  return defaultLayers.map((defaultLayer) => {
    const storedLayer = storedLayers.find((layer) => layer.id === defaultLayer.id);
    return storedLayer ? { ...defaultLayer, ...storedLayer } : defaultLayer;
  });
}

export function useWorkspaceState() {
  const [workspace, setWorkspace] = useState<WorkspaceState>(() => {
    const stored = window.localStorage.getItem(storageKey);

    if (!stored) {
      return initialWorkspace;
    }

    try {
      const parsed = JSON.parse(stored) as Partial<WorkspaceState>;
      return {
        ...initialWorkspace,
        ...parsed,
        layers: mergeStoredLayers(parsed.layers),
      };
    } catch {
      return initialWorkspace;
    }
  });

  useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(workspace));
  }, [workspace]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setWorkspace((current) => ({ ...current, commandOpen: true }));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return useMemo(() => {
    const updateWorkspace = (patch: Partial<WorkspaceState>) => {
      setWorkspace((current) => ({ ...current, ...patch }));
    };

    const toggleLayer = (id: LayerNode['id']) => {
      setWorkspace((current) => ({
        ...current,
        layers: current.layers.map((layer) => (
          layer.id === id ? { ...layer, enabled: !layer.enabled } : layer
        )),
      }));
    };

    const setLayerOpacity = (id: LayerNode['id'], opacity: number) => {
      setWorkspace((current) => ({
        ...current,
        layers: current.layers.map((layer) => (
          layer.id === id ? { ...layer, opacity } : layer
        )),
      }));
    };

    const resetWorkspace = () => setWorkspace(initialWorkspace);

    return {
      workspace,
      updateWorkspace,
      toggleLayer,
      setLayerOpacity,
      resetWorkspace,
    };
  }, [workspace]);
}