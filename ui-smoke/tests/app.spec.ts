import { test, expect } from '@playwright/test';

test('loads header and basic tabs', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('text=PMOVES-DoX')).toBeVisible();
  // search is present
  const search = page.getByPlaceholder('Search docs, APIs, logs, tags…');
  await expect(search).toBeVisible();
  await search.fill('loan');

  // switch to LOGS tab
  await page.getByRole('button', { name: 'LOGS' }).click();
  await expect(page.getByText('Logs')).toBeVisible();
  await expect(page.getByRole('button', { name: /Export CSV/i })).toBeVisible();

  // switch to APIs tab
  await page.getByRole('button', { name: 'APIS' }).click();
  await expect(page.getByText('APIs')).toBeVisible();
  await expect(page.getByText('method')).toBeVisible();

  // switch to TAGS tab
  await page.getByRole('button', { name: 'TAGS' }).click();
  await expect(page.getByText('Application Tags')).toBeVisible();
  await expect(page.getByRole('button', { name: /Load LMS Preset/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /Preview \(dry run\)/i })).toBeVisible();
});

test('enable HRM in Settings and see HRM chip on answer', async ({ page }) => {
  await page.goto('/');
  // open Settings
  await page.getByRole('button', { name: 'Settings' }).click();
  // toggle HRM
  const hrm = page.locator('label:text("Use HRM Sidecar (experimental)")');
  await expect(hrm).toBeVisible();
  const checkbox = page.locator('#hrm');
  await checkbox.check();
  // Save
  await page.getByRole('button', { name: 'Save' }).click();
  // Ask a question
  await page.getByPlaceholder('e.g., what is the total ROAS?').fill('what is the total revenue?');
  await page.getByRole('button', { name: 'Ask' }).click();
  // Expect an HRM badge in the answer block
  await expect(page.locator('text=Answer:').locator('xpath=..').locator('text=HRM')).toBeVisible();
});

test('deeplink switches to APIs panel', async ({ page }) => {
  await page.goto('/');
  // Dispatch a global-deeplink event to switch to APIs tab
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent('global-deeplink', { detail: { panel: 'apis' } }));
  });
  await page.getByRole('heading', { name: 'APIs' }).waitFor();
});

test('deeplink switches to Tags and Logs panels', async ({ page }) => {
  await page.goto('/');
  // Tags
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent('global-deeplink', { detail: { panel: 'tags', q: 'Loan' } }));
  });
  await page.getByRole('heading', { name: 'Application Tags' }).waitFor();
  // Logs
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent('global-deeplink', { detail: { panel: 'logs', code: 'ERROR' } }));
  });
  await page.getByRole('heading', { name: 'Logs' }).waitFor();
});

test('search Open in button triggers deeplink', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder('Search docs, APIs, logs, tags.');
  await input.fill('__ui_test__');
  // wait for dropdown and click the button
  await page.getByRole('button', { name: 'Open in.' }).click();
  await page.getByRole('heading', { name: 'APIs' }).waitFor();
});

test('workspace deeplink shows PDF link with page', async ({ page }) => {
  await page.goto('/');
  // Dispatch a synthetic workspace deeplink (does not require artifact to exist for link to render)
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent('global-deeplink', { detail: { panel: 'workspace', artifact_id: 'A1B2C3', page: 2 } }));
  });
  // Expect the "Open PDF at page" link to be present with correct query params
  const link = await page.getByRole('link', { name: /Open PDF at page/i });
  await link.waitFor();
  const href = await link.getAttribute('href');
  if (!href || !href.includes('/open/pdf?artifact_id=A1B2C3#page=2')) {
    throw new Error('PDF link missing or incorrect');
  }
});
