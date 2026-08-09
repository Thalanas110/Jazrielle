import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from '../App';

const capabilities = {
  assistant: 'JAZRIELLE',
  localMode: true,
  llmConfigured: false,
  capabilities: [],
};

vi.mock('../lib/api', () => ({
  getGetJarvisCapabilitiesQueryKey: () => ['capabilities'],
  useGetJarvisCapabilities: () => ({ data: capabilities, isLoading: false, isError: false, refetch: vi.fn() }),
  useExecuteJarvisCommand: () => ({ isPending: false, isError: false, data: undefined, error: null, mutate: vi.fn() }),
  useRunJarvisInference: () => ({ isPending: false, isError: false, data: undefined, mutate: vi.fn() }),
}));

describe('assistant shell', () => {
  it('starts expanded in browser mode and collapses on Escape', () => {
    render(<App />);

    expect(screen.getByRole('dialog', { name: 'Jazrielle assistant' })).toBeInTheDocument();
    expect(screen.getByTestId('input-command')).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(screen.getByRole('button', { name: 'Open Jazrielle' })).toBeInTheDocument();
  });
});
