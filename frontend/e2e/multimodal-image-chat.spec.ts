import { expect, test } from '@playwright/test';

const pngBase64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII=';
const imageFile: { name: string; mimeType: string; buffer: any } = {
  name: 'e2e.png',
  mimeType: 'image/png',
  buffer: (globalThis as any).Buffer.from(pngBase64, 'base64'),
};

const pasteImageIntoInput = async (page: any, selector: string) => {
  await page.evaluate(
    async ({ targetSelector, base64 }) => {
      const target = document.querySelector(targetSelector) as HTMLTextAreaElement | null;
      if (!target) throw new Error(`Target not found: ${targetSelector}`);

      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i += 1) {
        bytes[i] = binary.charCodeAt(i);
      }
      const file = new File([bytes], 'clipboard-shot.png', { type: 'image/png' });
      const dt = new DataTransfer();
      dt.items.add(file);

      target.focus();
      const event = new ClipboardEvent('paste', {
        clipboardData: dt,
        bubbles: true,
        cancelable: true,
      } as ClipboardEventInit);
      target.dispatchEvent(event);
    },
    { targetSelector: selector, base64: pngBase64 },
  );
};

const resolveModelCandidates = async (page: any) => {
  return page.evaluate(async () => {
    const res = await fetch('/api/models/providers');
    const providers = await res.json();
    let visionModel = '';
    let visionProvider = '';
    let nonVisionModel = '';
    let nonVisionProvider = '';
    for (const provider of providers || []) {
      const models = (provider.available_models?.length ? provider.available_models : provider.models) || [];
      for (const model of models) {
        const caps = provider.model_capabilities?.[model] || [];
        if (!visionModel && caps.includes('vision')) {
          visionModel = model;
          visionProvider = provider.name;
        }
        if (!nonVisionModel && !caps.includes('vision')) {
          nonVisionModel = model;
          nonVisionProvider = provider.name;
        }
        if (visionModel && nonVisionModel) break;
      }
      if (visionModel && nonVisionModel) break;
    }
    return { visionModel, visionProvider, nonVisionModel, nonVisionProvider };
  });
};

const selectModel = async (page: any, providerName: string, modelName: string) => {
  // Force a stable model selection path without relying on transient dropdown UI.
  await page.evaluate(({ provider, model }) => {
    localStorage.setItem('yue_selected_provider', provider);
    localStorage.setItem('yue_selected_model', model);
  }, { provider: providerName, model: modelName });
  await page.reload();
};

test('uploads image with text using a vision-capable model', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible();

  const { visionModel, visionProvider } = await resolveModelCandidates(page);
  expect(visionModel, 'No vision-capable model available for E2E').toBeTruthy();
  expect(visionProvider, 'No vision-capable provider available for E2E').toBeTruthy();
  await selectModel(page, visionProvider, visionModel);

  const uploadButton = page.getByRole('button', { name: /Upload files|Upload images/i });
  await expect(uploadButton).toBeVisible();
  const fileInput = page.locator('input[type="file"]').first();
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

  const { visionModel, visionProvider } = await resolveModelCandidates(page);
  expect(visionModel, 'No vision-capable model available for E2E').toBeTruthy();
  expect(visionProvider, 'No vision-capable provider available for E2E').toBeTruthy();
  await selectModel(page, visionProvider, visionModel);

  const fileInput = page.locator('input[type="file"]').first();
  await fileInput.setInputFiles(imageFile);
  await page.locator('button[type="submit"]').click();

  await expect(page.locator('img[alt="User upload"]').first()).toBeVisible();
});

test('pastes screenshot with Ctrl+V flow and sends successfully', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible();

  const { visionModel, visionProvider } = await resolveModelCandidates(page);
  expect(visionModel, 'No vision-capable model available for E2E').toBeTruthy();
  expect(visionProvider, 'No vision-capable provider available for E2E').toBeTruthy();
  await selectModel(page, visionProvider, visionModel);

  const inputSelector = 'textarea[placeholder*="You are chatting with"]';
  await pasteImageIntoInput(page, inputSelector);

  await expect(page.getByText('clipboard-shot.png').first()).toBeVisible();
  await page.locator('button[type="submit"]').click();

  await expect(page.locator('img[alt="User upload"]').first()).toBeVisible();
});

test('shows vision-off badge when model lacks vision capability', async ({ page }) => {
  await page.route('**/api/chat/stream', async route => {
    const stream = [
      `data: ${JSON.stringify({ chat_id: 'chat-vision-off-e2e' })}\n\n`,
      `data: ${JSON.stringify({ meta: { supports_vision: false, vision_enabled: false, image_count: 1 } })}\n\n`,
      `data: ${JSON.stringify({ content: 'vision fallback response' })}\n\n`,
    ].join('');
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body: stream,
    });
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible();

  const { nonVisionModel, nonVisionProvider } = await resolveModelCandidates(page);
  expect(nonVisionModel, 'No non-vision model available for E2E').toBeTruthy();
  expect(nonVisionProvider, 'No non-vision provider available for E2E').toBeTruthy();
  await selectModel(page, nonVisionProvider, nonVisionModel);

  const fileInput = page.locator('input[type="file"]').first();
  await fileInput.setInputFiles(imageFile);
  await input.fill('E2E non-vision text');
  await page.locator('button[type="submit"]').click();
  await expect(page.getByText('Vision Off').first()).toBeVisible({ timeout: 20000 });
});
