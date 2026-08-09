import { type ReactNode } from 'react';
import { X } from 'lucide-react';

export type AssistantPanelProps = {
  onClose: () => void;
  children: ReactNode;
};

export function AssistantPanel({ onClose, children }: AssistantPanelProps) {
  return (
    <section
      className="assistant-panel"
      role="dialog"
      aria-modal="false"
      aria-labelledby="assistant-panel-title"
      data-testid="assistant-panel"
    >
      <header className="panel-header">
        <div>
          <span className="panel-header-kicker">JAZRIELLE</span>
          <h1 id="assistant-panel-title">Jazrielle assistant</h1>
        </div>
        <button type="button" className="panel-close" aria-label="Close Jazrielle" onClick={onClose}>
          <X size={16} aria-hidden="true" />
        </button>
      </header>
      <div className="assistant-panel-content">{children}</div>
    </section>
  );
}
