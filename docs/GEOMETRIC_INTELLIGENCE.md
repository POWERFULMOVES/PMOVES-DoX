# GEMINI: Geometric Intelligence Guide

## Core Directive

## "The shape of the data determines the shape of the intelligence."

This document guides the AI Agent in understanding, visualizing, and manipulating the **Geometric Structure** of information within the PMOVES ecosystem.

## 1. The Geometry of Knowledge

### 1.1 The Problem with "Flat" Data

Traditional RAG (Retrieval-Augmented Generation) treats data as points in a flat High-Dimensional Euclidean space. This fails to capture:

*   **Hierarchy**: General concepts vs. details.
*   **Flow**: Directional relationships (A leads to B).
*   **Cycles**: Recurring patterns (Seasonality, Loops).

### 1.2 The Solution: Manifold Learning

We treat data as existing on a **Manifold** (a curved surface).

*   **Hyperbolic Space (Poincaré Disk/Pseudosphere)**: Best for **Tree-like** data (hierarchies, taxonomies, decision trees).
    *   *Visual Signature*: Exponential crowding at the edge (infinity).
    *   *Metric*: $\delta$-hyperbolicity (Lower $\delta$ = More Tree-like).
*   **Spherical Space**: Best for **Cyclic** data (daily routines, repeating processes).
*   **Euclidean Space**: Best for **Grid-like** data (images, spatial maps).

## 2. "Finding the Shape of Data"

### 2.1 The Agent's Role

Your job is to act as a **Geometer**. When analyzing a dataset (e.g., specific folder, set of logs), ask:

1.  **Is it Hierarchical?** $\rightarrow$ Use Hyperbolic Geometry.
2.  **Is it Cyclic?** $\rightarrow$ Use Spherical Geometry.
3.  **Is it Flat?** $\rightarrow$ Use Euclidean Geometry.

### 2.2 The "Trickout" Protocol (Mathematical Hacking)

We use the **Pmoves-hyperdimensions** tool (`/hyperdimensions`) to visualize these shapes.

**Control Knobs (Variables you can tweak):**

*   **`u, v`**: The coordinate space of the data.
*   **`Curvature (k)`**:
    *   $k < 0$: Hyperbolic (Saddle). Use for diverging data.
    *   $k > 0$: Spherical. Use for converging data.
    *   $k = 0$: Flat.
*   **`Epsilon (\epsilon)`**: The "Noise" or "Temperature".
    *   High $\epsilon$: Data is chaotic/unstructured.
    *   Low $\epsilon$: Data is crystallized/structured.

## 3. Tool Utilization

### 3.1 CHIT Geometry Packets (CGP)

*   **Format**: JSON.
*   **Usage**: The standard interchange format for geometry.
*   **Agent Action**: You can **generate** `chit_manifold.json` files to show the user the "Shape" of their query.

### 3.2 Key Files

*   **`external/Pmoves-hyperdimensions/index.html`**: The visualization engine.
*   **`chit_service.py`**: The backend decoder.
*   **`HyperbolicNavigator.tsx`**: The frontend viewer.

## 4. Workflows

### W1: Shape Discovery

1.  **Ingest**: Receive documents.
2.  **Embed**: Calculate embeddings.
3.  **Measure**: Compute curvature ($\delta$) and Topological Distribution.
4.  **Project**: Map to the appropriate Manifold (e.g., generating parameters for the Hyperdimensions tool).
5.  **Visualize**: Present the user with a 3D surface representing their knowledge base.

---

**Rule of Thumb:**

*   If the user asks "What does this look like?", do **not** show a list. Show a **Shape**.

---

## 5. Demo & Testing

For a complete demonstration walkthrough with metrics to watch and test validation:

**See: [GEOMETRY_DEMO_GUIDE.md](GEOMETRY_DEMO_GUIDE.md)**

- 95 tests validate geometric intelligence
- Live demo script (5-6 minutes)
- Troubleshooting guide
- API endpoint examples
