import { describe, expect, it } from 'vitest';
import { getBottomRightPosition, getWindowSize } from './window-geometry';

describe('window geometry', () => {
  it('returns the compact launcher size', () => {
    expect(getWindowSize('collapsed')).toEqual({ width: 80, height: 80 });
  });

  it('anchors the expanded panel above the bottom-right work-area inset', () => {
    expect(getBottomRightPosition({ x: 0, y: 0, width: 1920, height: 1040 }, 'expanded')).toEqual({ x: 1484, y: 384 });
  });
});
