import { test, expect } from '@playwright/test';

const BASE = process.env.STUDIO_BASE_URL ?? 'http://localhost:3000';

test('Extensions tile on home page navigates to /extensions', async ({ page }) => {
  await page.goto(BASE);
  const tile = page.getByRole('link', { name: /the extension story/i });
  await expect(tile).toBeVisible();
  await tile.click();
  await expect(page).toHaveURL(/\/extensions$/);
});

test('/extensions page has all six sections', async ({ page }) => {
  await page.goto(`${BASE}/extensions`);
  await expect(page.getByRole('heading', { name: 'Extensions' })).toBeVisible();
  await expect(page.getByRole('heading', { name: /the assignment/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /what i built/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /what i extended/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /critique/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /tech notes/i })).toBeVisible();
});

test('canonical sample video is rendered on /extensions', async ({ page }) => {
  await page.goto(`${BASE}/extensions`);
  const video = page.locator('video').first();
  await expect(video).toBeVisible();
  const src = await video.locator('source').getAttribute('src');
  expect(src).toMatch(/find-evil-canonical\.mp4$/);
});
