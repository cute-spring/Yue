import { expect, test } from '@playwright/test';

const pngBase64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII=';
const imageFile: { name: string; mimeType: string; buffer: any } = {
  name: 'e2e.png',
  mimeType: 'image/png',
  buffer: (globalThis as any).Buffer.from(pngBase64, 'base64'),
};

const resolveModelCandidates = async (page: any) => {
  return page.evaluate(async () => {
    const res = await fetch('/api/models/providers');
    const providers = await res.json();
    let visionModel = '';
    let nonVisionModel = '';
    for (const provider of providers || []) {
      const models = (provider.available_models?.length ? provider.available_models : provider.models) || [];
      for (const model of models) {
        const caps = provider.model_capabilities?.[model] || [];
        if (!visionModel && caps.includes('vision')) {
          visionModel = model;
        }
        if (!nonVisionModel && !caps.includes('vision')) {
          nonVisionModel = model;
        }
        if (visionModel && nonVisionModel) break;
      }
      if (visionModel && nonVisionModel) break;
    }
    return { visionModel, nonVisionModel };
  });
};

const selectModel = async (page: any, modelName: string) => {
  const selectorButton = page.getByRole('button', { name: /Select Model|QWN|QWEN|GPT|DEEPSEEK|VISION/i }).first();
  await selectorButton.click();
  const toggleAll = page.getByRole('button', { name: 'All' }).first();
  if (await toggleAll.isVisible()) {
    await toggleAll.click();
  }
  const dropdown = page.locator('div').filter({ hasText: /All Models|Enabled Models/ }).first();
  await dropdown.getByRole('button', { name: new RegExp(modelName, 'i') }).first().click();
};

test('uploads image with text using a vision-capable model', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible();

  const { visionModel } = await resolveModelCandidates(page);
  expect(visionModel, 'No vision-capable model available for E2E').toBeTruthy();
  await selectModel(page, visionModel);

  const uploadButton = page.getByRole('button', { name: 'Upload images' });
  await expect(uploadButton).toBeVisible();
  const fileInput = page.locator('input[type="file"][accept="image/*"]');
  await fileInput.setInputFiles(imageFile);

  await input.fill('E2E image + text');
  await page.locator('button[type="submit"]').click();

  await expect(page.getByText('E2E image + text').first()).toBeVisible();
  await expect(page.locator('img[alt="User upload"]').first()).toBeVisible();
});

test('sends image-only message using a vision-capable model', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible();

  const { visionModel } = await resolveModelCandidates(page);
  expect(visionModel, 'No vision-capable model available for E2E').toBeTruthy();
  await selectModel(page, visionModel);

  const fileInput = page.locator('input[type="file"][accept="image/*"]');
  await fileInput.setInputFiles(imageFile);
  await page.locator('button[type="submit"]').click();

  await expect(page.locator('img[alt="User upload"]').first()).toBeVisible();
});

test('shows vision-off badge when model lacks vision capability', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible();

  const { nonVisionModel } = await resolveModelCandidates(page);
  expect(nonVisionModel, 'No non-vision model available for E2E').toBeTruthy();
  await selectModel(page, nonVisionModel);

  await input.fill('E2E non-vision text');
  await page.locator('button[type="submit"]').click();
  await expect(page.getByText('Vision Off').first()).toBeVisible({ timeout: 20000 });
});
