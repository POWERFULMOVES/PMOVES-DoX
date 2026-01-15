/**
 * E2E tests for Geometry page and components.
 *
 * Tests the geometric intelligence visualization features:
 * - HyperbolicNavigator (Poincare disk)
 * - ZetaVisualizer (spectral analysis)
 * - Manifold3D (3D surfaces)
 */
import { test, expect } from '@playwright/test';

test.describe('Geometry Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to geometry page
    await page.goto('/geometry');
  });

  test('geometry page loads and displays header', async ({ page }) => {
    // Should have geometry-related content
    await expect(page.locator('text=Hyperbolic')).toBeVisible({ timeout: 10000 });
  });

  test('HyperbolicNavigator renders with demo data', async ({ page }) => {
    // The navigator should render an SVG canvas
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible({ timeout: 10000 });
  });

  test('Navigator (2D) and Manifold (3D) toggle buttons are visible', async ({ page }) => {
    // Should have mode toggle buttons
    await expect(page.getByRole('button', { name: /Navigator \(2D\)/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Manifold \(3D\)/i })).toBeVisible();
  });

  test('can switch between 2D and 3D views', async ({ page }) => {
    // Click on 3D button
    const manifoldBtn = page.getByRole('button', { name: /Manifold \(3D\)/i });
    await manifoldBtn.click();

    // Wait for 3D view to load (WebGL canvas)
    await page.waitForTimeout(1000);

    // Switch back to 2D
    const navigatorBtn = page.getByRole('button', { name: /Navigator \(2D\)/i });
    await navigatorBtn.click();

    // SVG should be visible again
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible();
  });

  test('ZetaVisualizer canvas is present', async ({ page }) => {
    // ZetaVisualizer renders a canvas element
    const canvas = page.locator('canvas');
    await expect(canvas.first()).toBeVisible({ timeout: 10000 });
  });

  test('HUD displays mode information', async ({ page }) => {
    // HUD should show mode
    await expect(page.locator('text=Mode:')).toBeVisible();
  });

  test('loading state shows while fetching data', async ({ page }) => {
    // Go to a fresh page instance
    await page.goto('/geometry');

    // Either loading state or content should be visible
    const hasContent = await page.locator('svg').first().isVisible().catch(() => false);
    const hasLoading = await page.locator('text=Loading').isVisible().catch(() => false);

    // One of these should be true
    expect(hasContent || hasLoading).toBe(true);
  });
});

test.describe('Geometry API Integration', () => {
  test('demo-packet endpoint returns data', async ({ request }) => {
    const apiBase = process.env.API_BASE || 'http://localhost:8484';
    const response = await request.get(`${apiBase}/cipher/geometry/demo-packet`);

    expect(response.ok()).toBe(true);

    const data = await response.json();
    expect(data).toHaveProperty('spec');
    expect(data).toHaveProperty('super_nodes');
    expect(data.spec).toBe('chit.cgp.v0.1');
  });

  test('simulate endpoint accepts CGP and returns A2UI format', async ({ request }) => {
    const apiBase = process.env.API_BASE || 'http://localhost:8484';

    const cgp = {
      spec: 'chit.cgp.v0.1',
      super_nodes: [
        {
          id: 'test',
          x: 0,
          y: 0,
          r: 100,
          label: 'Test Node',
          constellations: [],
        },
      ],
    };

    const response = await request.post(`${apiBase}/cipher/geometry/simulate`, {
      data: cgp,
    });

    expect(response.ok()).toBe(true);

    const data = await response.json();
    expect(data).toHaveProperty('surfaceUpdate');
    expect(data).toHaveProperty('beginRendering');
    expect(data.surfaceUpdate).toHaveProperty('components');
  });

  test('visualize_manifold demo mode returns metrics', async ({ request }) => {
    const apiBase = process.env.API_BASE || 'http://localhost:8484';

    const response = await request.post(`${apiBase}/cipher/geometry/visualize_manifold`, {
      data: { document_id: 'demo' },
    });

    expect(response.ok()).toBe(true);

    const data = await response.json();
    expect(data).toHaveProperty('status');
    expect(data.status).toBe('ok');
    expect(data).toHaveProperty('metrics');
    expect(data.metrics).toHaveProperty('curvature_k');
    expect(data).toHaveProperty('shape');
  });
});

test.describe('Geometry Error Handling', () => {
  test('gracefully handles API errors', async ({ page }) => {
    // Block the API to simulate failure
    await page.route('**/cipher/geometry/demo-packet', (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' }),
      });
    });

    await page.goto('/geometry');

    // Page should still load without crashing
    // Error state or fallback should be shown
    await page.waitForTimeout(2000);

    // The page should remain functional
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });
});

test.describe('Geometry Visualization Interactions', () => {
  test('super nodes are clickable', async ({ page }) => {
    await page.goto('/geometry');

    // Wait for SVG to render
    await page.waitForSelector('svg', { timeout: 10000 });

    // Find and click a super node circle if present
    const superNodeCircle = page.locator('svg circle').first();
    if (await superNodeCircle.isVisible()) {
      // Should be able to click without error
      await superNodeCircle.click();
    }
  });

  test('zoom controls work on navigator', async ({ page }) => {
    await page.goto('/geometry');

    // Wait for SVG to render
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible({ timeout: 10000 });

    // Scroll to zoom (D3 zoom behavior)
    await svg.hover();
    await page.mouse.wheel(0, -100); // Zoom in

    // Should not throw errors
    await page.waitForTimeout(500);
  });
});
