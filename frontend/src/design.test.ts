import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const css = readFileSync(resolve('frontend/src/style.css'), 'utf8');
const palette = Object.fromEntries([...css.matchAll(/--([\w-]+):\s*(#[\da-f]{6});/gi)].map(match => [match[1], match[2]]));

function luminance(hex: string) {
  const values = hex.slice(1).match(/../g)!.map(value => parseInt(value, 16) / 255).map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
  return .2126 * values[0] + .7152 * values[1] + .0722 * values[2];
}
function contrast(foreground: string, background: string) {
  const values = [luminance(palette[foreground]), luminance(palette[background])].sort((a, b) => b - a);
  return (values[0] + .05) / (values[1] + .05);
}

describe('readable design tokens', () => {
  it.each([
    ['color-ink', 'color-cream'], ['color-ink', 'color-white'], ['color-muted', 'color-cream'],
    ['color-muted', 'color-mint'], ['color-muted', 'color-aqua'], ['color-muted', 'color-powder'],
    ['color-subtle', 'color-white'], ['color-green', 'color-mint'], ['color-green', 'color-aqua'],
    ['color-white', 'color-action'], ['color-white', 'color-action-hover'],
    ['color-action-hover', 'color-powder'], ['color-error', 'color-error-bg'],
    ['color-warning', 'color-warning-bg'], ['color-muted', 'color-disabled-bg'],
  ])('%s on %s meets normal text contrast', (foreground, background) => {
    expect(contrast(foreground, background)).toBeGreaterThanOrEqual(4.5);
  });
  it.each(['chart-1', 'chart-2', 'chart-3', 'chart-4'])('%s is visible against the chart surface', foreground => {
    expect(contrast(foreground, 'color-white')).toBeGreaterThanOrEqual(3);
  });
});
