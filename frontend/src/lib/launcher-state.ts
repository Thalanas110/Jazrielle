import type { WindowMode } from './window-geometry';

export type LauncherState = {
  mode: WindowMode;
};

export type LauncherAction =
  | { type: 'open' }
  | { type: 'close' }
  | { type: 'toggle' };

export const initialLauncherState: LauncherState = {
  mode: 'collapsed',
};

export function launcherReducer(state: LauncherState, action: LauncherAction): LauncherState {
  if (action.type === 'open') return { mode: 'expanded' };
  if (action.type === 'close') return { mode: 'collapsed' };
  return { mode: state.mode === 'collapsed' ? 'expanded' : 'collapsed' };
}
