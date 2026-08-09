import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AssistantPanel } from './assistant-panel';

describe('AssistantPanel', () => {
  it('renders an accessible dialog and closes when requested', () => {
    const onClose = vi.fn();
    render(
      <AssistantPanel onClose={onClose}>
        <p>Panel content</p>
      </AssistantPanel>,
    );

    expect(screen.getByRole('dialog', { name: 'Jazrielle assistant' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close Jazrielle' }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
