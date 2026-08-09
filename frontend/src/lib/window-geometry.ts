export type WindowMode = 'collapsed' | 'expanded';

export type WindowSize = {
  width: number;
  height: number;
};

export type WorkArea = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export const WINDOW_INSET = 16;
export const LAUNCHER_SIZE = 80;

export const WINDOW_SIZES: Record<WindowMode, WindowSize> = {
  collapsed: {
    width: LAUNCHER_SIZE + WINDOW_INSET * 2,
    height: LAUNCHER_SIZE + WINDOW_INSET * 2,
  },
  expanded: { width: 420, height: 640 },
};

export function getWindowSize(mode: WindowMode): WindowSize {
  return WINDOW_SIZES[mode];
}

export function getBottomRightPosition(workArea: WorkArea, mode: WindowMode) {
  const size = getWindowSize(mode);
  return {
    x: workArea.x + workArea.width - size.width - WINDOW_INSET,
    y: workArea.y + workArea.height - size.height - WINDOW_INSET,
  };
}
