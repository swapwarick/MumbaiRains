import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ChevronsDown, ChevronsLeft, ChevronsRight, ChevronsUp, Loader2 } from 'lucide-react';
import { computeMetrics, loadTwinDatasets, resetSimulation, runSimulation } from '../../features/digitalTwin/data';
import type {
  InspectorReading,
  SimulationData,
  SimulationStatus,
  TwinDatasets,
} from '../../features/digitalTwin/types';
import { useWorkspaceState } from '../../state/workspace';
import { CommandBar } from './CommandBar';
import { CommandPalette } from './CommandPalette';
import { LeftDock } from './LeftDock';
import { MapViewport } from './MapViewport';
import { RightDock } from './RightDock';
import { Timeline } from './Timeline';
import { ToastStack, type ToastMessage } from './ToastStack';

let toastId = 0;
let datasetsPromise: Promise<TwinDatasets> | null = null;

function getTwinDatasets() {
  datasetsPromise ??= loadTwinDatasets();
  return datasetsPromise;
}

export function DigitalTwinWorkstation() {
  const { workspace, updateWorkspace, toggleLayer, setLayerOpacity, resetWorkspace } = useWorkspaceState();
  const [datasets, setDatasets] = useState<TwinDatasets | null>(null);
  const [simulation, setSimulation] = useState<SimulationData | null>(null);
  const [status, setStatus] = useState<SimulationStatus>('idle');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rainfallIntensity, setRainfallIntensity] = useState(60);
  const [rainfallDuration] = useState(4);
  const [currentStep, setCurrentStep] = useState(0);
  const [inspector, setInspector] = useState<InspectorReading | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const totalSteps = simulation?.depth_history.length ?? 1;
  const isPlaying = status === 'running';
  const metrics = useMemo(
    () => computeMetrics(datasets?.terrain ?? null, simulation, currentStep, rainfallIntensity),
    [currentStep, datasets, rainfallIntensity, simulation],
  );

  const pushToast = (title: string, detail: string, tone: ToastMessage['tone'] = 'info') => {
    toastId += 1;
    const nextToast = { id: toastId, title, detail, tone };
    setToasts((current) => [nextToast, ...current].slice(0, 4));
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== nextToast.id));
    }, 5200);
  };

  useEffect(() => {
    let cancelled = false;

    getTwinDatasets()
      .then((loadedDatasets) => {
        if (cancelled) {
          return;
        }
        setDatasets(loadedDatasets);
        pushToast('DEM Loaded', 'Terrain, roads, buildings, and waterways are online.', 'success');
      })
      .catch((loadError: unknown) => {
        if (cancelled) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : 'Unable to load digital twin datasets');
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!isPlaying || !simulation) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setCurrentStep((step) => {
        if (step >= simulation.depth_history.length - 1) {
          setStatus('complete');
          pushToast('Simulation Finished', 'Playback reached the final hydraulic frame.', 'success');
          return step;
        }

        return step + 1;
      });
    }, 520);

    return () => window.clearInterval(intervalId);
  }, [isPlaying, simulation]);

  useEffect(() => {
    if (metrics.massBalanceError > 3) {
      pushToast('Mass Balance Warning', `Continuity residual is ${metrics.massBalanceError.toFixed(2)}%.`, 'warning');
    }
  }, [metrics.massBalanceError]);

  const handleRun = async () => {
    setStatus('running');
    setError(null);
    pushToast('Simulation Started', `${rainfallIntensity} mm/hr storm scenario is executing.`, 'info');

    try {
      const result = await runSimulation(rainfallDuration, rainfallIntensity);
      setSimulation(result);
      setCurrentStep(0);
      updateWorkspace({ activeOverlay: 'floodDepth' });
      pushToast('Rain Started', 'Flood-depth raster layer is now animating.', 'success');
    } catch (runError) {
      setStatus('idle');
      setError(runError instanceof Error ? runError.message : 'Simulation failed');
      pushToast('Simulation Failed', 'The backend returned an execution error.', 'warning');
    }
  };

  const handleReset = async () => {
    await resetSimulation();
    setSimulation(null);
    setCurrentStep(0);
    setStatus('idle');
    setInspector(null);
    pushToast('Workspace Reset', 'Simulation state and playback frame were cleared.', 'info');
  };

  const stepPrevious = () => {
    setStatus((current) => (current === 'running' ? 'paused' : current));
    setCurrentStep((step) => Math.max(0, step - 1));
  };

  const stepNext = () => {
    setStatus((current) => (current === 'running' ? 'paused' : current));
    setCurrentStep((step) => Math.min(totalSteps - 1, step + 1));
  };

  if (loading) {
    return (
      <main className="loading-screen">
        <Loader2 size={44} />
        <strong>Booting hydrodynamic workstation</strong>
        <span>Loading terrain rasters, infrastructure vectors, and analysis workspace.</span>
      </main>
    );
  }

  if (error || !datasets) {
    return (
      <main className="loading-screen error-screen">
        <AlertTriangle size={44} />
        <strong>Digital twin could not start</strong>
        <span>{error ?? 'Datasets are unavailable.'}</span>
        <button type="button" onClick={() => window.location.reload()}>Retry</button>
      </main>
    );
  }

  return (
    <main className={`workstation mode-${workspace.mode}`}>
      <CommandBar
        mode={workspace.mode}
        status={status}
        threeD={workspace.threeD}
        onModeChange={(mode) => updateWorkspace({ mode })}
        onRun={handleRun}
        onPause={() => setStatus('paused')}
        onResume={() => simulation && setStatus('running')}
        onStop={() => setStatus('idle')}
        onReset={handleReset}
        onStepPrevious={stepPrevious}
        onStepNext={stepNext}
        onCommandOpen={() => updateWorkspace({ commandOpen: true })}
        onThreeDToggle={() => updateWorkspace({ threeD: !workspace.threeD })}
      />

      <div className="workspace-grid">
        <LeftDock
          collapsed={workspace.leftCollapsed || workspace.mode === 'executive'}
          selectedScenario={workspace.selectedScenario}
          rainfallIntensity={rainfallIntensity}
          layers={workspace.layers}
          onOverlaySelect={(activeOverlay) => updateWorkspace({ activeOverlay })}
          onRainfallIntensityChange={setRainfallIntensity}
          onScenarioSelect={(selectedScenario) => {
            updateWorkspace({ selectedScenario });
            pushToast('Load Scenario', 'Scenario metadata is selected for the next run.', 'info');
          }}
          onLayerToggle={toggleLayer}
          onLayerOpacity={setLayerOpacity}
        />

        <MapViewport
          terrain={datasets.terrain}
          roads={datasets.roads}
          buildings={datasets.buildings}
          waterways={datasets.waterways}
          activeOverlay={workspace.activeOverlay}
          simulation={simulation}
          currentStep={currentStep}
          layers={workspace.layers}
          threeD={workspace.threeD}
          onInspect={setInspector}
        />

        <RightDock
          collapsed={workspace.rightCollapsed || workspace.mode === 'executive'}
          mode={workspace.mode}
          status={status}
          metrics={metrics}
          inspector={inspector}
        />
      </div>

      <Timeline
        collapsed={workspace.bottomCollapsed}
        currentStep={currentStep}
        totalSteps={totalSteps}
        isPlaying={isPlaying}
        onPlayToggle={() => setStatus(isPlaying ? 'paused' : simulation ? 'running' : 'idle')}
        onStop={() => setStatus('idle')}
        onStepChange={(step) => {
          setCurrentStep(step);
          setStatus((current) => (current === 'running' ? 'paused' : current));
        }}
        onPrevious={stepPrevious}
        onNext={stepNext}
      />

      <div className="dock-toggles">
        <button type="button" onClick={() => updateWorkspace({ leftCollapsed: !workspace.leftCollapsed })} title="Toggle left dock">
          {workspace.leftCollapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
        </button>
        <button type="button" onClick={() => updateWorkspace({ rightCollapsed: !workspace.rightCollapsed })} title="Toggle right dock">
          {workspace.rightCollapsed ? <ChevronsLeft size={16} /> : <ChevronsRight size={16} />}
        </button>
        <button type="button" onClick={() => updateWorkspace({ bottomCollapsed: !workspace.bottomCollapsed })} title="Toggle timeline">
          {workspace.bottomCollapsed ? <ChevronsUp size={16} /> : <ChevronsDown size={16} />}
        </button>
      </div>

      <CommandPalette
        open={workspace.commandOpen}
        onClose={() => updateWorkspace({ commandOpen: false })}
        onRun={handleRun}
        onResetWorkspace={resetWorkspace}
      />
      <ToastStack
        messages={toasts}
        onDismiss={(id) => setToasts((current) => current.filter((toast) => toast.id !== id))}
      />
    </main>
  );
}
