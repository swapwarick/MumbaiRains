import { Pause, Play, SkipBack, SkipForward, Square } from 'lucide-react';

interface TimelineProps {
  collapsed: boolean;
  currentStep: number;
  totalSteps: number;
  isPlaying: boolean;
  onPlayToggle: () => void;
  onStop: () => void;
  onStepChange: (step: number) => void;
  onPrevious: () => void;
  onNext: () => void;
}

export function Timeline({
  collapsed,
  currentStep,
  totalSteps,
  isPlaying,
  onPlayToggle,
  onStop,
  onStepChange,
  onPrevious,
  onNext,
}: TimelineProps) {
  const frameCount = Math.max(totalSteps, 1);
  const tickCount = Math.min(frameCount, 24);
  const progress = frameCount > 1 ? currentStep / (frameCount - 1) : 0;

  return (
    <footer className={`timeline ${collapsed ? 'is-collapsed' : ''}`}>
      <div className="transport-controls">
        <button type="button" onClick={onPrevious} title="Previous frame">
          <SkipBack size={16} />
        </button>
        <button type="button" onClick={onPlayToggle} className="play-toggle" title={isPlaying ? 'Pause' : 'Play'}>
          {isPlaying ? <Pause size={17} /> : <Play size={17} />}
        </button>
        <button type="button" onClick={onStop} title="Stop">
          <Square size={15} />
        </button>
        <button type="button" onClick={onNext} title="Next frame">
          <SkipForward size={16} />
        </button>
      </div>

      <div className="timeline-track">
        <div className="timecode">
          <strong>Frame {currentStep + 1}</strong>
          <span>{frameCount} total</span>
        </div>
        <div className="ruler">
          {Array.from({ length: tickCount }).map((_, index) => (
            <i key={`${index}-${tickCount}`} style={{ left: `${(index / Math.max(1, tickCount - 1)) * 100}%` }} />
          ))}
          <div className="timeline-progress" style={{ width: `${progress * 100}%` }} />
          <input
            type="range"
            min="0"
            max={frameCount - 1}
            step="1"
            value={Math.min(currentStep, frameCount - 1)}
            onChange={(event) => onStepChange(Number(event.target.value))}
            aria-label="Simulation timeline"
          />
        </div>
      </div>

      <div className="timeline-charts" aria-hidden="true">
        {Array.from({ length: 42 }).map((_, index) => (
          <span
            key={index}
            style={{
              height: `${18 + Math.sin(index * 0.42) * 10 + (index % 7) * 2}px`,
            }}
          />
        ))}
      </div>
    </footer>
  );
}
