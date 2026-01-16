"use client";

import React, { useEffect, useRef, useMemo, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

interface ManifoldParams {
    curvature_k?: number;
    epsilon?: number;
    surfaceFn?: string;
    t?: number;
}

interface Props {
    width: number;
    height: number;
    params: ManifoldParams | null;
}

/**
 * Generate parametric surface geometry based on curvature type.
 * Supports Hyperbolic (K < 0), Spherical (K > 0), and Flat (K ≈ 0) manifolds.
 */
function generateManifoldGeometry(
    curvature_k: number,
    epsilon: number,
    segments: number = 50
): THREE.BufferGeometry {
    const positions: number[] = [];
    const colors: number[] = [];
    const indices: number[] = [];

    const scale = Math.max(1, Math.abs(curvature_k)) * 2;

    for (let i = 0; i <= segments; i++) {
        const u = i / segments;
        for (let j = 0; j <= segments; j++) {
            const v = j / segments;

            let x: number, y: number, z: number;
            let r: number, g: number, b: number;

            if (curvature_k < -0.1) {
                // Hyperbolic (Pseudosphere/Tractrix-like)
                const theta = u * 4 * Math.PI;
                const phi = v * 2.9 + 0.1;
                const k = Math.abs(curvature_k);

                x = k * Math.cos(theta) * Math.sin(phi);
                y = k * Math.sin(theta) * Math.sin(phi);
                // Tractrix z-coordinate with logarithmic singularity clamped
                const tanHalf = Math.tan(phi / 2);
                const logVal = tanHalf > 0.001 ? Math.log(tanHalf) : -6;
                z = -k * (Math.cos(phi) + Math.max(-6, Math.min(6, logVal)));

                // Add epsilon noise
                const noise = Math.sin(theta * 10) * epsilon * 0.1;
                z += noise;

                // Color: purple-cyan gradient
                r = 0.5 + 0.5 * Math.sin(phi);
                g = 0.2;
                b = 1.0 - epsilon * 0.5;
            } else if (curvature_k > 0.1) {
                // Spherical
                const theta = u * 2 * Math.PI;
                const phi = v * Math.PI;
                const k = Math.abs(curvature_k);

                x = k * Math.sin(phi) * Math.cos(theta);
                y = k * Math.sin(phi) * Math.sin(theta);
                z = k * Math.cos(phi);

                // Add epsilon wobble
                const noise = Math.cos(phi * 20) * epsilon * 0.1;
                x += noise;
                y += noise;

                // Color: orange-gold gradient
                r = 1.0 - epsilon * 0.3;
                g = 0.5 + 0.5 * Math.cos(theta);
                b = 0.2;
            } else {
                // Flat (Euclidean plane with optional waves)
                x = (u - 0.5) * scale * 5;
                y = (v - 0.5) * scale * 5;
                z = Math.sin(u * Math.PI * 2) * Math.cos(v * Math.PI * 2) * epsilon * 2;

                // Color: gray-blue
                r = 0.4;
                g = 0.5 + z * 0.1;
                b = 0.6;
            }

            positions.push(x, y, z);
            colors.push(r, g, b);
        }
    }

    // Generate triangle indices
    for (let i = 0; i < segments; i++) {
        for (let j = 0; j < segments; j++) {
            const a = i * (segments + 1) + j;
            const b = a + 1;
            const c = a + (segments + 1);
            const d = c + 1;

            indices.push(a, b, c);
            indices.push(b, d, c);
        }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();

    return geometry;
}

export default function Manifold3D({ width, height, params }: Props) {
    const mountRef = useRef<HTMLDivElement>(null);
    const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
    const sceneRef = useRef<THREE.Scene | null>(null);
    const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
    const meshRef = useRef<THREE.Mesh | null>(null);
    const controlsRef = useRef<OrbitControls | null>(null);
    const reqRef = useRef<number>(0);

    // Extract params with defaults
    const curvature_k = params?.curvature_k ?? 0;
    const epsilon = params?.epsilon ?? 0.1;

    // Initialize Three.js
    useEffect(() => {
        if (!mountRef.current) return;

        // Scene
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0f172a); // slate-950
        sceneRef.current = scene;

        // Camera
        const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
        camera.position.set(20, 15, 20);
        camera.up.set(0, 0, 1);
        cameraRef.current = camera;

        // Renderer
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(width, height);
        mountRef.current.appendChild(renderer.domElement);
        rendererRef.current = renderer;

        // Controls
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.autoRotate = true;
        controls.autoRotateSpeed = 1.0;
        controlsRef.current = controls;

        // Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        scene.add(ambientLight);
        const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
        dirLight.position.set(10, 20, 10);
        scene.add(dirLight);

        // Geometry - Generate based on curvature
        const geometry = generateManifoldGeometry(curvature_k, epsilon);
        const material = new THREE.MeshPhongMaterial({
            vertexColors: true,
            wireframe: false,
            side: THREE.DoubleSide,
            shininess: 80,
        });
        const mesh = new THREE.Mesh(geometry, material);
        meshRef.current = mesh;
        scene.add(mesh);

        // Animation Loop
        const animate = () => {
            reqRef.current = requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        };
        animate();

        return () => {
            cancelAnimationFrame(reqRef.current);
            if (rendererRef.current && mountRef.current) {
                if (mountRef.current.contains(rendererRef.current.domElement)) {
                    mountRef.current.removeChild(rendererRef.current.domElement);
                }
                rendererRef.current.dispose();
            }
        };
    }, []);

    // Update geometry when params change
    useEffect(() => {
        if (!meshRef.current || !sceneRef.current) return;

        // Generate new geometry
        const newGeometry = generateManifoldGeometry(curvature_k, epsilon);

        // Dispose old geometry
        meshRef.current.geometry.dispose();

        // Apply new geometry
        meshRef.current.geometry = newGeometry;
    }, [curvature_k, epsilon]);

    // Handle Resize
    useEffect(() => {
        if (cameraRef.current && rendererRef.current) {
            cameraRef.current.aspect = width / height;
            cameraRef.current.updateProjectionMatrix();
            rendererRef.current.setSize(width, height);
        }
    }, [width, height]);

    return <div ref={mountRef} style={{ width, height }} />;
}
