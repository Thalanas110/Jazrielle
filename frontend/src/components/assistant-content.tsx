import { type ReactNode } from 'react';

export type AssistantContentProps = {
  children: ReactNode;
};

export function AssistantContent({ children }: AssistantContentProps) {
  return (
    <div className="jazrielle-shell" data-testid="jazrielle-shell">
      {children}
    </div>
  );
}
