import { describe, expect, it } from 'vitest';
import { getBottomRightPosition, getWindowSize } from './window-geometry';

describe('window geometry', () => {
  it('leaves room for the compact launcher and its transparent-stage inset', () => {
    expect(getWindowSize('collapsed')).toEqual({ width: 112, height: 112 });
  });

  it('anchors the expanded panel above the bottom-right work-area inset', () => {
    expect(getBottomRightPosition({ x: 0, y: 0, width: 1920, height: 1040 }, 'expanded')).toEqual({ x: 1484, y: 384 });
  });
});
