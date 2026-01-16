"use client";

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

/**
 * Shared state for synchronizing 2D (HyperbolicNavigator) and 3D (Manifold3D) views.
 */
interface GeometryContextType {
    // Selection state
    selectedNode: string | null;
    selectedConstellation: string | null;
    selectedPoint: string | null;

    // View mode
    viewMode: 'navigator' | 'manifold';

    // Manifold parameters (shared between views)
    manifoldParams: {
        curvature_k: number;
        epsilon: number;
    };

    // Actions
    setSelectedNode: (id: string | null) => void;
    setSelectedConstellation: (id: string | null) => void;
    setSelectedPoint: (id: string | null) => void;
    setViewMode: (mode: 'navigator' | 'manifold') => void;
    setManifoldParams: (params: { curvature_k?: number; epsilon?: number }) => void;
    clearSelection: () => void;
}

const GeometryContext = createContext<GeometryContextType | null>(null);

interface GeometryProviderProps {
    children: ReactNode;
    initialParams?: {
        curvature_k?: number;
        epsilon?: number;
    };
}

export function GeometryProvider({ children, initialParams }: GeometryProviderProps) {
    const [selectedNode, setSelectedNode] = useState<string | null>(null);
    const [selectedConstellation, setSelectedConstellation] = useState<string | null>(null);
    const [selectedPoint, setSelectedPoint] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<'navigator' | 'manifold'>('navigator');
    const [manifoldParams, setManifoldParamsState] = useState({
        curvature_k: initialParams?.curvature_k ?? 0,
        epsilon: initialParams?.epsilon ?? 0.1,
    });

    const setManifoldParams = useCallback((params: { curvature_k?: number; epsilon?: number }) => {
        setManifoldParamsState(prev => ({
            ...prev,
            ...params,
        }));
    }, []);

    const clearSelection = useCallback(() => {
        setSelectedNode(null);
        setSelectedConstellation(null);
        setSelectedPoint(null);
    }, []);

    const value: GeometryContextType = {
        selectedNode,
        selectedConstellation,
        selectedPoint,
        viewMode,
        manifoldParams,
        setSelectedNode,
        setSelectedConstellation,
        setSelectedPoint,
        setViewMode,
        setManifoldParams,
        clearSelection,
    };

    return (
        <GeometryContext.Provider value={value}>
            {children}
        </GeometryContext.Provider>
    );
}

export function useGeometry(): GeometryContextType {
    const context = useContext(GeometryContext);
    if (!context) {
        throw new Error('useGeometry must be used within a GeometryProvider');
    }
    return context;
}

/**
 * Hook for optional geometry context (returns null if not in provider).
 * Useful for components that can work with or without the context.
 */
export function useGeometryOptional(): GeometryContextType | null {
    return useContext(GeometryContext);
}
