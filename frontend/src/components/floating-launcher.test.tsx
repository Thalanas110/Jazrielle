import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { FloatingLauncher } from './floating-launcher';

describe('FloatingLauncher', () => {
  it('opens Jazrielle when clicked', () => {
    const onOpen = vi.fn();
    render(<FloatingLauncher active={false} thinking={false} onOpen={onOpen} />);

    fireEvent.click(screen.getByRole('button', { name: 'Open Jazrielle' }));

    expect(onOpen).toHaveBeenCalledOnce();
  });

  it('exposes the thinking state', () => {
    render(<FloatingLauncher active onOpen={vi.fn()} thinking />);

    expect(screen.getByRole('button', { name: 'Open Jazrielle' })).toHaveAttribute('data-state', 'thinking');
  });

  it('describes the panel it opens to assist keyboard and screen-reader users', () => {
    render(<FloatingLauncher active={false} thinking={false} onOpen={vi.fn()} />);

    expect(screen.getByRole('button', { name: 'Open Jazrielle' })).toHaveAttribute('aria-haspopup', 'dialog');
    expect(screen.getByRole('button', { name: 'Open Jazrielle' })).toHaveAttribute('aria-controls', 'assistant-panel');
  });
});
