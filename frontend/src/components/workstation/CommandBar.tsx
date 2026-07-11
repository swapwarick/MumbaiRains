import {
  Activity,
  Box,
  ChevronLeft,
  ChevronRight,
  Download,
  Gauge,
  Pause,
  Play,
  Radar,
  RotateCcw,
  Search,
  Settings,
  SkipBack,
  SkipForward,
  Square,
  Video,
} from 'lucide-react';
import type { SimulationStatus, WorkspaceMode } from '../../features/digitalTwin/types';
import { modeCopy } from '../../features/digitalTwin/catalog';

interface CommandBarProps {
  mode: WorkspaceMode;
  status: SimulationStatus;
  threeD: boolean;
  onModeChange: (mode: WorkspaceMode) => void;
  onRun: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onReset: () => void;
  onStepPrevious: () => void;
  onStepNext: () => void;
  onCommandOpen: () => void;
  onThreeDToggle: () => void;
}

export function CommandBar({
  mode,
  status,
  threeD,
  onModeChange,
  onRun,
  onPause,
  onResume,
  onStop,
  onReset,
  onStepPrevious,
  onStepNext,
  onCommandOpen,
  onThreeDToggle,
}: CommandBarProps) {
  const primaryDisabled = status === 'running';

  return (
    <header className="command-bar">
      <div className="brand-lockup">
        <div className="brand-mark">
          <Radar size={20} />
        </div>
        <div>
          <strong>Mumbai Flood Digital Twin</strong>
          <span>Urban Hydrodynamic Workstation</span>
        </div>
      </div>

      <nav className="mode-switch" aria-label="Workspace mode">
        {(['operator', 'research', 'executive'] as WorkspaceMode[]).map((item) => (
          <button
            className={mode === item ? 'active' : ''}
            key={item}
            onClick={() => onModeChange(item)}
            type="button"
          >
            {modeCopy[item]}
          </button>
        ))}
      </nav>

      <div className="command-actions" aria-label="Simulation commands">
        <button type="button" className="primary-command" disabled={primaryDisabled} onClick={onRun} title="Run simulation">
          <Play size={16} />
          <span>Run</span>
        </button>
        <button type="button" onClick={onPause} title="Pause">
          <Pause size={16} />
        </button>
        <button type="button" onClick={onResume} title="Resume">
          <Activity size={16} />
        </button>
        <button type="button" onClick={onStop} title="Stop">
          <Square size={16} />
        </button>
        <button type="button" onClick={onReset} title="Reset">
          <RotateCcw size={16} />
        </button>
        <button type="button" onClick={onStepPrevious} title="Previous step">
          <SkipBack size={16} />
        </button>
        <button type="button" onClick={onStepNext} title="Next step">
          <SkipForward size={16} />
        </button>
      </div>

      <div className="secondary-actions">
        <button type="button" onClick={onThreeDToggle} className={threeD ? 'active' : ''} title="Toggle 3D mode">
          <Box size={16} />
          <span>3D</span>
        </button>
        <button type="button" title="Export workspace">
          <Download size={16} />
        </button>
        <button type="button" title="Record animation">
          <Video size={16} />
        </button>
        <button type="button" title="Open diagnostics">
          <Gauge size={16} />
        </button>
        <button type="button" title="Settings">
          <Settings size={16} />
        </button>
        <button type="button" className="search-command" onClick={onCommandOpen}>
          <Search size={15} />
          <span>Search</span>
          <kbd>Ctrl K</kbd>
        </button>
      </div>

      <div className="mobile-panel-toggles" aria-hidden="true">
        <ChevronLeft size={14} />
        <ChevronRight size={14} />
      </div>
    </header>
  );
}
