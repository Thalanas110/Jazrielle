import { describe, expect, it } from 'vitest';
import { initialLauncherState, launcherReducer } from './launcher-state';

describe('launcherReducer', () => {
  it('opens from collapsed state', () => {
    expect(launcherReducer(initialLauncherState, { type: 'open' })).toEqual({ mode: 'expanded' });
  });

  it('closes from expanded state', () => {
    expect(launcherReducer({ mode: 'expanded' }, { type: 'close' })).toEqual({ mode: 'collapsed' });
  });

  it('toggles the current mode', () => {
    expect(launcherReducer({ mode: 'collapsed' }, { type: 'toggle' }).mode).toBe('expanded');
    expect(launcherReducer({ mode: 'expanded' }, { type: 'toggle' }).mode).toBe('collapsed');
  });
});
