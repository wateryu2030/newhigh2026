import { test, expect } from '@playwright/test';

/** 与 @/api/client AUTH_TOKEN_STORAGE_KEY 一致；E2E 仅用于通过 AuthGate，非真实 JWT。 */
const E2E_AUTH_STORAGE_KEY = 'newhigh_jwt_token';

test.beforeEach(async ({ page }) => {
  await page.addInitScript((key: string) => {
    try {
      localStorage.setItem(key, 'e2e-smoke-placeholder');
    } catch {
      /* ignore */
    }
  }, E2E_AUTH_STORAGE_KEY);
});

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
    await page.waitForLoadState('networkidle').catch(() => {});
    const strategies = page.locator('a[href*="/strategies"]').first();
    await strategies.waitFor({ state: 'visible', timeout: 15000 });
    await strategies.click();
    await expect(page).toHaveURL(/\/strategies/);
  });

  test('can navigate to portfolio page (execution equity curve)', async ({ page }) => {
    await page.goto('/portfolio');
    await expect(page).toHaveURL(/\/portfolio/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/组合|Portfolio/i);
  });

  test('can navigate to AI trading page', async ({ page }) => {
    await page.goto('/ai-trading');
    await expect(page).toHaveURL(/\/ai-trading/);
    await expect(page.locator('body')).toBeVisible();
  });
});
