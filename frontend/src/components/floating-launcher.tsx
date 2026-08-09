import { type ReactNode } from 'react';

export type FloatingLauncherProps = {
  active: boolean;
  thinking: boolean;
  onOpen: () => void;
  children?: ReactNode;
};

export function FloatingLauncher({ active, thinking, onOpen, children }: FloatingLauncherProps) {
  return (
    <button
      type="button"
      className={`launcher-button${active ? ' is-active' : ''}`}
      aria-label="Open Jazrielle"
      aria-controls="assistant-panel"
      aria-expanded="false"
      aria-haspopup="dialog"
      data-testid="button-open-launcher"
      data-state={thinking ? 'thinking' : 'ready'}
      onClick={onOpen}
    >
      <span className="launcher-orb" aria-hidden="true">
        {children ?? <span className="launcher-orb-core" />}
      </span>
    </button>
  );
}
