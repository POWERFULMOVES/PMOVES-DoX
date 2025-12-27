"use client";

import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export default function Manifold3D({ width, height, params }: { width: number, height: number, params: any }) {
    const mountRef = useRef<HTMLDivElement>(null);
    const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
    const sceneRef = useRef<THREE.Scene | null>(null);
    const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
    const meshRef = useRef<THREE.Mesh | null>(null);
    const reqRef = useRef<number>(0);

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

        // Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        scene.add(ambientLight);
        const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
        dirLight.position.set(10, 20, 10);
        scene.add(dirLight);

        // Geometry (Initial)
        const geometry = new THREE.PlaneGeometry(10, 10, 50, 50); // Placeholder
        const material = new THREE.MeshPhongMaterial({ 
            color: 0x60a5fa, // blue-400
            wireframe: true,
            side: THREE.DoubleSide
        });
        const mesh = new THREE.Mesh(geometry, material);
        meshRef.current = mesh;
        scene.add(mesh);

        // Animation Loop
        const animate = () => {
            reqRef.current = requestAnimationFrame(animate);
            controls.update();

            // Dynamic Update if SurfaceFn is present (Simplistic version)
            if (meshRef.current && params?.t) {
                 meshRef.current.rotation.z += 0.002; 
            }

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
