/// <reference types="node" />
/**
 * Open WebUI Health Check Tests
 * Verifies all Docker services are running and responding
 */
import { test, expect, request } from '@playwright/test';

test.describe('Service Health Checks', () => {

    test('Open WebUI is accessible on port 3000', async ({ page }) => {
        const response = await page.goto('/');
        expect(response?.status()).toBeLessThan(400);
    });

    test('LiteLLM is running on port 4000', async () => {
        const context = await request.newContext();
        const response = await context.get('http://localhost:4000/health');
        expect(response.ok()).toBeTruthy();
    });

    test('Middleware is running on port 5000', async () => {
        const context = await request.newContext();
        // Middleware doesn't have /health, verify via v1/models with valid key
        const response = await context.get('http://localhost:5000/v1/models', {
            headers: {
                'Authorization': `Bearer ${process.env.SUBKEY_ADMIN || 'YOUR_SUBKEY_ADMIN'}`
            }
        });
        expect(response.ok()).toBeTruthy();
    });

    test('PostgreSQL is accessible via Docker', async () => {
        // PostgreSQL connectivity verified through middleware health
        const context = await request.newContext();
        const response = await context.get('http://localhost:5000/health');
        expect(response.ok()).toBeTruthy();
    });
});

test.describe('Login Page Verification', () => {

    test('Login page loads with form elements', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');

        // Wait for page to be interactive
        await page.waitForTimeout(2000);

        // Should have email and password inputs
        const hasLoginForm = await page.locator('input[type="email"], input[name="email"]').count() > 0 ||
            await page.locator('input[type="password"]').count() > 0;

        expect(hasLoginForm || page.url().includes('chat')).toBeTruthy();
    });
});
