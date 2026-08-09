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

export const WINDOW_SIZES: Record<WindowMode, WindowSize> = {
  collapsed: { width: 80, height: 80 },
  expanded: { width: 420, height: 640 },
};

export const WINDOW_INSET = 16;

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
