/**
 * Tests for ZetaVisualizer component.
 *
 * ZetaVisualizer renders Riemann Zeta spectral analysis using
 * canvas-based animation with configurable frequencies and amplitudes.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import React from 'react';
import { ZetaVisualizer } from '../ZetaVisualizer';

// Mock requestAnimationFrame and cancelAnimationFrame
const mockRequestAnimationFrame = vi.fn((cb: FrameRequestCallback) => {
  return 1; // Return a mock animation frame ID
});
const mockCancelAnimationFrame = vi.fn();

// Mock canvas context
const mockCanvasContext = {
  fillStyle: '',
  strokeStyle: '',
  lineWidth: 1,
  fillRect: vi.fn(),
  strokeRect: vi.fn(),
  beginPath: vi.fn(),
  arc: vi.fn(),
  stroke: vi.fn(),
  fill: vi.fn(),
  clearRect: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  closePath: vi.fn(),
};

describe('ZetaVisualizer', () => {
  const defaultFrequencies = [14.13, 21.02, 25.01];
  const defaultAmplitudes = [0.8, 0.6, 0.4];

  beforeEach(() => {
    vi.stubGlobal('requestAnimationFrame', mockRequestAnimationFrame);
    vi.stubGlobal('cancelAnimationFrame', mockCancelAnimationFrame);

    // Mock HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = vi.fn(() => mockCanvasContext) as any;

    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders canvas element', () => {
    const { container } = render(
      <ZetaVisualizer frequencies={defaultFrequencies} amplitudes={defaultAmplitudes} />
    );

    const canvas = container.querySelector('canvas');
    expect(canvas).toBeTruthy();
  });

  it('renders with default width and height', () => {
    const { container } = render(
      <ZetaVisualizer frequencies={defaultFrequencies} amplitudes={defaultAmplitudes} />
    );

    const canvas = container.querySelector('canvas');
    expect(canvas?.getAttribute('width')).toBe('400');
    expect(canvas?.getAttribute('height')).toBe('200');
  });

  it('accepts custom width and height', () => {
    const { container } = render(
      <ZetaVisualizer
        frequencies={defaultFrequencies}
        amplitudes={defaultAmplitudes}
        width={800}
        height={400}
      />
    );

    const canvas = container.querySelector('canvas');
    expect(canvas?.getAttribute('width')).toBe('800');
    expect(canvas?.getAttribute('height')).toBe('400');
  });

  it('accepts frequencies and amplitudes props', () => {
    const frequencies = [14.13, 21.02, 25.01, 30.42];
    const amplitudes = [0.9, 0.7, 0.5, 0.3];

    // Should not throw
    expect(() => {
      render(
        <ZetaVisualizer frequencies={frequencies} amplitudes={amplitudes} />
      );
    }).not.toThrow();
  });

  it('starts animation on mount via requestAnimationFrame', () => {
    render(
      <ZetaVisualizer frequencies={defaultFrequencies} amplitudes={defaultAmplitudes} />
    );

    expect(mockRequestAnimationFrame).toHaveBeenCalled();
  });

  it('cleans up animation on unmount via cancelAnimationFrame', () => {
    const { unmount } = render(
      <ZetaVisualizer frequencies={defaultFrequencies} amplitudes={defaultAmplitudes} />
    );

    unmount();

    expect(mockCancelAnimationFrame).toHaveBeenCalled();
  });

  it('renders label for Zeta Spectral Resonance', () => {
    render(
      <ZetaVisualizer frequencies={defaultFrequencies} amplitudes={defaultAmplitudes} />
    );

    expect(screen.getByText('Zeta Spectral Resonance')).toBeTruthy();
  });

  it('applies custom className', () => {
    const { container } = render(
      <ZetaVisualizer
        frequencies={defaultFrequencies}
        amplitudes={defaultAmplitudes}
        className="custom-zeta-class"
      />
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.classList.contains('custom-zeta-class')).toBe(true);
  });

  it('handles empty frequencies gracefully (uses defaults)', () => {
    // Should not throw, should use default zeta zeros
    expect(() => {
      render(
        <ZetaVisualizer frequencies={[]} amplitudes={[]} />
      );
    }).not.toThrow();
  });

  it('handles mismatched frequencies/amplitudes lengths', () => {
    // Should not throw, should handle gracefully
    expect(() => {
      render(
        <ZetaVisualizer
          frequencies={[14.13, 21.02, 25.01]}
          amplitudes={[0.5]} // Shorter than frequencies
        />
      );
    }).not.toThrow();
  });

  it('renders border and rounded styling', () => {
    const { container } = render(
      <ZetaVisualizer frequencies={defaultFrequencies} amplitudes={defaultAmplitudes} />
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.classList.contains('border')).toBe(true);
    expect(wrapper.classList.contains('rounded-lg')).toBe(true);
  });

  it('renders with bg-slate-950 background', () => {
    const { container } = render(
      <ZetaVisualizer frequencies={defaultFrequencies} amplitudes={defaultAmplitudes} />
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.classList.contains('bg-slate-950')).toBe(true);
  });

  it('restarts animation when frequencies change', () => {
    const { rerender } = render(
      <ZetaVisualizer frequencies={[14.13]} amplitudes={[0.5]} />
    );

    vi.clearAllMocks();

    rerender(
      <ZetaVisualizer frequencies={[14.13, 21.02]} amplitudes={[0.5, 0.6]} />
    );

    // Should cancel old animation and start new one
    expect(mockCancelAnimationFrame).toHaveBeenCalled();
    expect(mockRequestAnimationFrame).toHaveBeenCalled();
  });

  it('canvas has block display class', () => {
    const { container } = render(
      <ZetaVisualizer frequencies={defaultFrequencies} amplitudes={defaultAmplitudes} />
    );

    const canvas = container.querySelector('canvas');
    expect(canvas?.classList.contains('block')).toBe(true);
  });
});
