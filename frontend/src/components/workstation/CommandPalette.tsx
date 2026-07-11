import { Layers, Play, Search, Settings, Sparkles, X } from 'lucide-react';

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onRun: () => void;
  onResetWorkspace: () => void;
}

export function CommandPalette({ open, onClose, onRun, onResetWorkspace }: CommandPaletteProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="palette-backdrop" role="presentation" onMouseDown={onClose}>
      <dialog className="command-palette" open onMouseDown={(event) => event.stopPropagation()}>
        <div className="palette-search">
          <Search size={18} />
          <input autoFocus placeholder="Search commands, layers, scenarios, diagnostics" />
          <button type="button" onClick={onClose} title="Close command palette">
            <X size={16} />
          </button>
        </div>
        <div className="palette-results">
          <button type="button" onClick={onRun}>
            <Play size={16} />
            <span>Run current simulation scenario</span>
            <kbd>Enter</kbd>
          </button>
          <button type="button">
            <Layers size={16} />
            <span>Toggle flood depth raster</span>
            <kbd>L</kbd>
          </button>
          <button type="button">
            <Sparkles size={16} />
            <span>Open executive presentation mode</span>
            <kbd>E</kbd>
          </button>
          <button type="button" onClick={onResetWorkspace}>
            <Settings size={16} />
            <span>Restore default workspace layout</span>
            <kbd>R</kbd>
          </button>
        </div>
      </dialog>
    </div>
  );
}
