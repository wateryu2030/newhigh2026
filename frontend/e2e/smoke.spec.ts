import { test, expect } from '@playwright/test';

test.describe('Smoke', () => {
  test('home page loads and shows dashboard or app title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/AI|控制台|Fund|newhigh/i);
    const body = page.locator('body');
    await expect(body).toBeVisible();
    const main = page.locator('main');
    await expect(main).toBeVisible();
  });

  test('can navigate to strategies page', async ({ page }) => {
    await page.goto('/');
    await page.locator('a[href*="strategies"]').first().click();
    await expect(page).toHaveURL(/\/strategies/);
  });

  test('can navigate to portfolio page (execution equity curve)', async ({ page }) => {
    await page.goto('/portfolio');
    await expect(page).toHaveURL(/\/portfolio/);
    await expect(page.locator('h1')).toContainText(/组合|Portfolio|资金/i);
  });

  test('can navigate to AI trading page', async ({ page }) => {
    await page.goto('/ai-trading');
    await expect(page).toHaveURL(/\/ai-trading/);
    await expect(page.locator('body')).toBeVisible();
  });
});
