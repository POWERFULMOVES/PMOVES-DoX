/**
 * Tests for Manifold3D component.
 *
 * Manifold3D renders Three.js 3D surface visualization with
 * OrbitControls and dynamic geometry based on manifold parameters.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import React from 'react';

// Mock Three.js and its modules
const mockRenderer = {
  setSize: vi.fn(),
  render: vi.fn(),
  dispose: vi.fn(),
  domElement: document.createElement('canvas'),
};

const mockScene = {
  add: vi.fn(),
  background: null,
};

const mockCamera = {
  position: { set: vi.fn() },
  up: { set: vi.fn() },
  aspect: 1,
  updateProjectionMatrix: vi.fn(),
};

const mockGeometry = {
  setAttribute: vi.fn(),
  setIndex: vi.fn(),
  computeVertexNormals: vi.fn(),
  dispose: vi.fn(),
};

const mockMesh = {
  rotation: { z: 0 },
  geometry: mockGeometry,
};

const mockControls = {
  enableDamping: false,
  autoRotate: false,
  autoRotateSpeed: 0,
  update: vi.fn(),
};

vi.mock('three', () => ({
  Scene: vi.fn(() => mockScene),
  PerspectiveCamera: vi.fn(() => mockCamera),
  WebGLRenderer: vi.fn(() => mockRenderer),
  AmbientLight: vi.fn(),
  DirectionalLight: vi.fn(() => ({ position: { set: vi.fn() } })),
  PlaneGeometry: vi.fn(),
  BufferGeometry: vi.fn(() => mockGeometry),
  Float32BufferAttribute: vi.fn(),
  MeshPhongMaterial: vi.fn(),
  Mesh: vi.fn(() => mockMesh),
  Color: vi.fn(),
  DoubleSide: 2,
}));

vi.mock('three/examples/jsm/controls/OrbitControls.js', () => ({
  OrbitControls: vi.fn(() => mockControls),
}));

// Mock nats-context
vi.mock('@/lib/nats-context', () => ({
  useNats: vi.fn(() => ({
    connection: null,
    isConnected: false,
    error: null,
    reconnectAttempt: 0,
    publish: vi.fn(),
    lastMessage: null,
  })),
}));

// Mock nats.ws StringCodec
vi.mock('nats.ws', () => ({
  StringCodec: vi.fn(() => ({
    decode: vi.fn((data) => new TextDecoder().decode(data)),
    encode: vi.fn((str) => new TextEncoder().encode(str)),
  })),
}));

// Mock requestAnimationFrame
const mockRequestAnimationFrame = vi.fn((cb: FrameRequestCallback) => 1);
const mockCancelAnimationFrame = vi.fn();

// Import after mocks
import Manifold3D from '../Manifold3D';

describe('Manifold3D', () => {
  beforeEach(() => {
    vi.stubGlobal('requestAnimationFrame', mockRequestAnimationFrame);
    vi.stubGlobal('cancelAnimationFrame', mockCancelAnimationFrame);
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders without crashing', () => {
    expect(() => {
      render(<Manifold3D width={800} height={600} params={null} />);
    }).not.toThrow();
  });

  it('creates a container div with correct dimensions', () => {
    const { container } = render(
      <Manifold3D width={800} height={600} params={null} />
    );

    const div = container.firstChild as HTMLElement;
    expect(div).toBeTruthy();
    expect(div.style.width).toBe('800px');
    expect(div.style.height).toBe('600px');
  });

  it('initializes Three.js Scene', async () => {
    render(<Manifold3D width={800} height={600} params={null} />);

    const THREE = await import('three');
    expect(THREE.Scene).toHaveBeenCalled();
  });

  it('initializes PerspectiveCamera with correct aspect ratio', async () => {
    render(<Manifold3D width={800} height={600} params={null} />);

    const THREE = await import('three');
    // Camera created with aspect = width / height
    expect(THREE.PerspectiveCamera).toHaveBeenCalledWith(
      45, // fov
      800 / 600, // aspect
      0.1, // near
      1000 // far
    );
  });

  it('initializes WebGLRenderer with antialias', async () => {
    render(<Manifold3D width={800} height={600} params={null} />);

    const THREE = await import('three');
    expect(THREE.WebGLRenderer).toHaveBeenCalledWith({
      antialias: true,
      alpha: true,
    });
  });

  it('creates OrbitControls', async () => {
    render(<Manifold3D width={800} height={600} params={null} />);

    const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js');
    expect(OrbitControls).toHaveBeenCalled();
  });

  it('adds ambient and directional lights to scene', async () => {
    render(<Manifold3D width={800} height={600} params={null} />);

    const THREE = await import('three');
    expect(THREE.AmbientLight).toHaveBeenCalled();
    expect(THREE.DirectionalLight).toHaveBeenCalled();
    expect(mockScene.add).toHaveBeenCalled();
  });

  it('creates initial BufferGeometry mesh', async () => {
    render(<Manifold3D width={800} height={600} params={null} />);

    const THREE = await import('three');
    expect(THREE.BufferGeometry).toHaveBeenCalled();
    expect(THREE.Mesh).toHaveBeenCalled();
  });

  it('starts animation loop via requestAnimationFrame', () => {
    render(<Manifold3D width={800} height={600} params={null} />);

    expect(mockRequestAnimationFrame).toHaveBeenCalled();
  });

  it('cleans up animation on unmount', () => {
    const { unmount } = render(
      <Manifold3D width={800} height={600} params={null} />
    );

    unmount();

    // Animation frame should be cancelled on unmount
    expect(mockCancelAnimationFrame).toHaveBeenCalled();
  });

  it('updates renderer size when dimensions change', () => {
    const { rerender } = render(
      <Manifold3D width={800} height={600} params={null} />
    );

    vi.clearAllMocks();

    rerender(<Manifold3D width={1200} height={900} params={null} />);

    expect(mockRenderer.setSize).toHaveBeenCalledWith(1200, 900);
    expect(mockCamera.updateProjectionMatrix).toHaveBeenCalled();
  });

  it('handles params prop for dynamic updates', () => {
    const params = { t: 1.5, curvature_k: -2 };

    expect(() => {
      render(<Manifold3D width={800} height={600} params={params} />);
    }).not.toThrow();
  });

  it('sets camera position', async () => {
    render(<Manifold3D width={800} height={600} params={null} />);

    expect(mockCamera.position.set).toHaveBeenCalledWith(20, 15, 20);
  });

  it('sets camera up vector', async () => {
    render(<Manifold3D width={800} height={600} params={null} />);

    expect(mockCamera.up.set).toHaveBeenCalledWith(0, 0, 1);
  });

  it('enables autoRotate on OrbitControls', () => {
    render(<Manifold3D width={800} height={600} params={null} />);

    expect(mockControls.autoRotate).toBe(true);
    expect(mockControls.autoRotateSpeed).toBe(1.0);
  });

  it('enables damping on OrbitControls', () => {
    render(<Manifold3D width={800} height={600} params={null} />);

    expect(mockControls.enableDamping).toBe(true);
  });
});
