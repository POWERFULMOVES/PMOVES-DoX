import { test, expect } from '@playwright/test';

test('loads header and basic tabs', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('text=LMS Analyst')).toBeVisible();
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

