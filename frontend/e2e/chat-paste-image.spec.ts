import { expect, test } from '@playwright/test';
import { mockChatBootstrap } from './chat-test-helpers';

const pngBase64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII=';

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

const pastePlainTextIntoInput = async (page: any, selector: string, text: string) => {
  return page.evaluate(
    ({ targetSelector, content }) => {
      const target = document.querySelector(targetSelector) as HTMLTextAreaElement | null;
      if (!target) throw new Error(`Target not found: ${targetSelector}`);

      const dt = new DataTransfer();
      dt.setData('text/plain', content);

      target.focus();
      const event = new ClipboardEvent('paste', {
        clipboardData: dt,
        bubbles: true,
        cancelable: true,
      } as ClipboardEventInit);
      target.dispatchEvent(event);
      const prevented = event.defaultPrevented;

      // Synthetic paste does not insert text by default, emulate browser insertion
      // only when the app did not prevent default behavior.
      if (!prevented) {
        const start = target.selectionStart ?? target.value.length;
        const end = target.selectionEnd ?? target.value.length;
        target.setRangeText(content, start, end, 'end');
        target.dispatchEvent(new Event('input', { bubbles: true }));
      }

      return { prevented, value: target.value };
    },
    { targetSelector: selector, content: text },
  ) as Promise<{ prevented: boolean; value: string }>;
};

test('pastes screenshot into composer and sends with image attachment', async ({ page }) => {
  const provider = 'mock-openai';
  const visionModel = 'vision-model';

  await page.addInitScript(({ preferredProvider, preferredModel }) => {
    localStorage.setItem('yue_selected_provider', preferredProvider);
    localStorage.setItem('yue_selected_model', preferredModel);
  }, { preferredProvider: provider, preferredModel: visionModel });

  await mockChatBootstrap(page, {
    prefs: {
      advanced_mode: true,
      voice_input_enabled: false,
    },
    agents: [],
    providers: [
      {
        name: provider,
        configured: true,
        available_models: [visionModel, 'text-model'],
        models: [visionModel, 'text-model'],
        model_capabilities: {
          [visionModel]: ['vision'],
          'text-model': [],
        },
      },
    ],
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible();

  const inputSelector = 'textarea[placeholder*="You are chatting with"]';
  await pasteImageIntoInput(page, inputSelector);

  await expect(page.getByText('clipboard-shot.png').first()).toBeVisible();
  const submitButton = page.locator('button[type="submit"]');
  await expect(submitButton).toBeEnabled();
  await submitButton.click();

  await expect(page.locator('img[alt="User upload"]').first()).toBeVisible();
});

test('keeps plain text paste behavior without adding image attachment', async ({ page }) => {
  const provider = 'mock-openai';
  const textModel = 'text-model';

  await page.addInitScript(({ preferredProvider, preferredModel }) => {
    localStorage.setItem('yue_selected_provider', preferredProvider);
    localStorage.setItem('yue_selected_model', preferredModel);
  }, { preferredProvider: provider, preferredModel: textModel });

  await mockChatBootstrap(page, {
    prefs: {
      advanced_mode: true,
      voice_input_enabled: false,
    },
    agents: [],
    providers: [
      {
        name: provider,
        configured: true,
        available_models: [textModel],
        models: [textModel],
        model_capabilities: {
          [textModel]: [],
        },
      },
    ],
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible();

  const inputSelector = 'textarea[placeholder*="You are chatting with"]';
  const pastedText = 'plain paste should stay text';
  const pasteResult = await pastePlainTextIntoInput(page, inputSelector, pastedText);
  expect(pasteResult.prevented).toBe(false);
  await expect(input).toHaveValue(pastedText);
  await expect(page.getByText('clipboard-shot.png')).toHaveCount(0);

  const submitButton = page.locator('button[type="submit"]');
  await expect(submitButton).toBeEnabled();
  await submitButton.click();

  await expect(page.getByText(pastedText).first()).toBeVisible();
  await expect(page.locator('img[alt="User upload"]')).toHaveCount(0);
});
