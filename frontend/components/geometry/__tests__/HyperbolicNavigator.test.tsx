/**
 * Tests for HyperbolicNavigator component.
 *
 * HyperbolicNavigator renders a Poincare disk visualization of
 * hierarchical knowledge using D3.js with NATS integration.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

// Mock NATS context - return null connection to avoid async iterator issues
vi.mock('@/lib/nats-context', () => ({
  useNats: vi.fn(() => ({ connection: null, isConnected: false })),
}));

// Mock D3 to avoid jsdom SVG issues with zoom - all inline to avoid hoisting issues
vi.mock('d3', () => {
  const createChainable = () => {
    const obj: Record<string, any> = {};
    const methods = ['selectAll', 'data', 'join', 'attr', 'style', 'on', 'append', 'text', 'call', 'remove', 'datum'];
    methods.forEach(m => { obj[m] = vi.fn(() => obj); });
    return obj;
  };
  return {
    select: vi.fn(() => createChainable()),
    zoom: vi.fn(() => ({
      scaleExtent: vi.fn().mockReturnThis(),
      on: vi.fn().mockReturnThis(),
      transform: vi.fn(),
    })),
    zoomIdentity: {
      translate: vi.fn(() => ({ scale: vi.fn().mockReturnThis(), translate: vi.fn().mockReturnThis() })),
    },
    symbol: vi.fn(() => ({ type: vi.fn().mockReturnThis(), size: vi.fn().mockReturnThis() })),
    symbolStar: 'star',
  };
});

// Mock next/dynamic to return a simple placeholder for Manifold3D
vi.mock('next/dynamic', () => ({
  default: vi.fn(() => {
    const MockManifold3D = ({ width, height }: { width: number; height: number }) => (
      <div data-testid="manifold-3d" style={{ width, height }}>
        Mock Manifold3D
      </div>
    );
    MockManifold3D.displayName = 'MockManifold3D';
    return MockManifold3D;
  }),
}));

// Import after mocks are set up
import { HyperbolicNavigator } from '../HyperbolicNavigator';

describe('HyperbolicNavigator', () => {
  const mockData = {
    super_nodes: [
      {
        id: 'sn1',
        x: 0,
        y: 0,
        r: 100,
        label: 'Test Node',
        constellations: [
          {
            id: 'c1',
            anchor: [0, 0],
            summary: 'Test Cluster',
            spectrum: [1, 2, 3],
            radial_minmax: [0, 1] as [number, number],
            points: [
              { id: 'p1', x: 10, y: 10, proj: 0.5, conf: 0.9, text: 'Point 1' },
              { id: 'p2', x: -10, y: 10, proj: 0.3, conf: 0.7, text: 'Point 2' },
            ],
          },
        ],
      },
    ],
  };

  const emptyData = { super_nodes: [] };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders SVG canvas with correct dimensions', () => {
    const { container } = render(
      <HyperbolicNavigator data={mockData} width={800} height={600} />
    );

    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    expect(svg?.getAttribute('width')).toBe('800');
    expect(svg?.getAttribute('height')).toBe('600');
  });

  it('renders container with correct classes', () => {
    const { container } = render(
      <HyperbolicNavigator data={mockData} className="custom-class" />
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toBeTruthy();
    expect(wrapper.classList.contains('custom-class')).toBe(true);
  });

  it('initializes D3 visualization without errors', () => {
    // D3 is mocked, so this tests that component renders without throwing
    const { container } = render(
      <HyperbolicNavigator data={mockData} width={800} height={600} />
    );

    // Should render SVG
    expect(container.querySelector('svg')).toBeTruthy();
  });

  it('renders visualization container', () => {
    const { container } = render(
      <HyperbolicNavigator data={mockData} width={800} height={600} />
    );

    // Container should exist
    expect(container.firstChild).toBeTruthy();
  });

  it('handles empty data gracefully', () => {
    const { container } = render(
      <HyperbolicNavigator data={emptyData} width={800} height={600} />
    );

    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
  });

  it('handles missing NATS connection gracefully', () => {
    // With null connection, component should still render
    const { container } = render(<HyperbolicNavigator data={mockData} />);
    expect(container.querySelector('svg')).toBeTruthy();
  });

  it('shows Navigator (2D) button as active by default', () => {
    render(<HyperbolicNavigator data={mockData} />);

    const navigatorBtn = screen.getByRole('button', { name: /Navigator \(2D\)/i });
    expect(navigatorBtn).toBeTruthy();
  });

  it('shows Manifold (3D) button', () => {
    render(<HyperbolicNavigator data={mockData} />);

    const manifoldBtn = screen.getByRole('button', { name: /Manifold \(3D\)/i });
    expect(manifoldBtn).toBeTruthy();
  });

  it('switches to manifold view when clicking 3D button', async () => {
    const { container } = render(
      <HyperbolicNavigator data={mockData} width={800} height={600} />
    );

    // Initially in navigator mode - SVG visible
    expect(container.querySelector('svg')).toBeTruthy();

    // Click manifold button
    const manifoldBtn = screen.getByRole('button', { name: /Manifold \(3D\)/i });
    fireEvent.click(manifoldBtn);

    // Should now show Manifold3D
    await waitFor(() => {
      expect(screen.getByTestId('manifold-3d')).toBeTruthy();
    });
  });

  it('displays HUD with mode information', () => {
    render(<HyperbolicNavigator data={mockData} />);

    expect(screen.getByText('Hyperbolic Manifold')).toBeTruthy();
    expect(screen.getByText(/Mode: navigator/i)).toBeTruthy();
  });

  it('handles data prop changes without errors', () => {
    const { rerender, container } = render(
      <HyperbolicNavigator data={emptyData} width={800} height={600} />
    );

    // Update with data - should not throw
    rerender(
      <HyperbolicNavigator data={mockData} width={800} height={600} />
    );

    // Component should still render
    expect(container.querySelector('svg')).toBeTruthy();
  });

  it('renders with custom width and height', () => {
    const { container } = render(
      <HyperbolicNavigator data={mockData} width={1200} height={900} />
    );

    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('width')).toBe('1200');
    expect(svg?.getAttribute('height')).toBe('900');
  });
});
