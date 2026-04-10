import { expect, test, type Page } from '@playwright/test';
import { mockChatBootstrap } from './chat-test-helpers';

type BrowserScenario = {
  steps: Array<
    | { delay: number; type: 'result'; results: Array<{ transcript: string; isFinal: boolean }> }
    | { delay: number; type: 'error'; error: string }
    | { delay: number; type: 'end' }
  >;
};

type AzureScenario = {
  steps: Array<
    | { delay: number; type: 'recognizing'; text: string }
    | { delay: number; type: 'recognized'; text: string }
    | { delay: number; type: 'canceled'; errorDetails: string }
    | { delay: number; type: 'sessionStopped' }
  >;
};

const installVoiceMocks = async (page: Page) => {
  await page.addInitScript(() => {
    const browserScenarios = [];
    const azureScenarios = [];

    function MockSpeechRecognition(this: any) {
      this.continuous = false;
      this.interimResults = false;
      this.lang = 'en-US';
      this.onstart = null;
      this.onresult = null;
      this.onerror = null;
      this.onend = null;
      this.timers = [];
      this.ended = false;
    }

    MockSpeechRecognition.prototype.emitResult = function emitResult(results: Array<{ transcript: string; isFinal: boolean }>) {
      const payload = results.map((item) => ({
        isFinal: item.isFinal,
        0: { transcript: item.transcript },
      }));
      if (this.onresult) {
        this.onresult({ results: payload });
      }
    };

    MockSpeechRecognition.prototype.finish = function finish() {
      if (this.ended) return;
      this.ended = true;
      if (this.onend) {
        this.onend(new Event('end'));
      }
    };

    MockSpeechRecognition.prototype.start = function start() {
      const scenario = browserScenarios.shift() || { steps: [] };
      if (this.onstart) {
        this.onstart(new Event('start'));
      }
      for (const step of scenario.steps) {
        const timer = window.setTimeout(() => {
          if (this.ended) return;
          if (step.type === 'result') {
            this.emitResult(step.results);
            return;
          }
          if (step.type === 'error') {
            if (this.onerror) {
              this.onerror({ error: step.error });
            }
            return;
          }
          this.finish();
        }, step.delay);
        this.timers.push(timer);
      }
    };

    MockSpeechRecognition.prototype.stop = function stop() {
      this.timers.forEach(window.clearTimeout);
      this.timers = [];
      window.setTimeout(() => this.finish(), 0);
    };

    MockSpeechRecognition.prototype.abort = function abort() {
      this.timers.forEach(window.clearTimeout);
      this.timers = [];
      this.ended = true;
      if (this.onerror) {
        this.onerror({ error: 'aborted' });
      }
      if (this.onend) {
        this.onend(new Event('end'));
      }
    };

    function MockAzureRecognizer(this: any) {
      this.recognizing = null;
      this.recognized = null;
      this.canceled = null;
      this.sessionStopped = null;
      this.timers = [];
      this.stopped = false;
    }

    MockAzureRecognizer.prototype.startContinuousRecognitionAsync = function startContinuousRecognitionAsync(cb?: () => void) {
      const scenario = azureScenarios.shift() || { steps: [] };
      if (cb) cb();
      for (const step of scenario.steps) {
        const timer = window.setTimeout(() => {
          if (this.stopped) return;
          if (step.type === 'recognizing') {
            if (this.recognizing) {
              this.recognizing(null, { result: { text: step.text } });
            }
            return;
          }
          if (step.type === 'recognized') {
            if (this.recognized) {
              this.recognized(null, { result: { text: step.text } });
            }
            return;
          }
          if (step.type === 'canceled') {
            if (this.canceled) {
              this.canceled(null, { errorDetails: step.errorDetails });
            }
            return;
          }
          if (this.sessionStopped) {
            this.sessionStopped(null, new Event('sessionStopped'));
          }
        }, step.delay);
        this.timers.push(timer);
      }
    };

    MockAzureRecognizer.prototype.stopContinuousRecognitionAsync = function stopContinuousRecognitionAsync(cb?: () => void) {
      this.stopped = true;
      this.timers.forEach(window.clearTimeout);
      this.timers = [];
      if (cb) cb();
      window.setTimeout(() => {
        if (this.sessionStopped) {
          this.sessionStopped(null, new Event('sessionStopped'));
        }
      }, 0);
    };

    MockAzureRecognizer.prototype.close = function close() {};

    if (!navigator.mediaDevices) {
      Object.defineProperty(navigator, 'mediaDevices', {
        configurable: true,
        value: {},
      });
    }
    if (!navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices.getUserMedia = async () => ({}) as MediaStream;
    }

    (window as any).__voiceInputTest = {
      queueBrowserScenario: (scenario: any) => {
        browserScenarios.push(scenario);
      },
      queueAzureScenario: (scenario: any) => {
        azureScenarios.push(scenario);
      },
      installAzureSpeechSdkMock: () => {
        (window as any).SpeechSDK = {
          SpeechConfig: {
            fromAuthorizationToken: (_token: string, _region: string) => ({}),
          },
          AudioConfig: {
            fromDefaultMicrophoneInput: () => ({}),
          },
          SpeechRecognizer: MockAzureRecognizer,
        };
      },
    };

    (window as any).SpeechRecognition = MockSpeechRecognition;
    (window as any).webkitSpeechRecognition = MockSpeechRecognition;
  });
};

const getComposer = (page: Page) => page.getByPlaceholder(/You are chatting with/i);
const getVoiceButton = (page: Page) => page.locator('button[aria-label*="voice input"], button[aria-label*="Voice input"]').first();
const getInsertButton = (page: Page) => page.getByRole('button', { name: 'Insert' });
const getDiscardButton = (page: Page) => page.getByRole('button', { name: 'Discard' });
const getSendVoiceButton = (page: Page) => page.getByRole('button', { name: 'Send (Cmd/Ctrl+Enter)' });
const getVoiceDraftReadyText = (page: Page, providerLabel: string) =>
  page.getByText(`Voice draft ready from ${providerLabel}`, { exact: true }).last();

const selectAgentByMention = async (page: Page, agentName: string) => {
  const composer = getComposer(page);
  await composer.fill('@');
  await page.getByRole('button', { name: new RegExp(agentName, 'i') }).click();
  await expect(composer).toHaveValue('');
};

test.describe('voice input', () => {
  test.beforeEach(async ({ page }) => {
    await installVoiceMocks(page);
  });

  test('browser speech creates a draft and inserts into the composer after confirmation', async ({ page }) => {
    await mockChatBootstrap(page, {
      prefs: {
        language: 'zh',
        voice_input_enabled: true,
        voice_input_provider: 'browser',
        voice_input_language: 'zh-CN',
      },
      agents: [
        { id: 'default', name: 'Default Agent', system_prompt: 'sys', provider: 'openai', model: 'gpt-4o-mini', enabled_tools: [] },
      ],
    });

    await page.goto('/');
    await expect(getComposer(page)).toBeVisible();

    await page.evaluate((scenario: BrowserScenario) => {
      (window as any).__voiceInputTest.queueBrowserScenario(scenario);
    }, {
      steps: [
        { delay: 50, type: 'result', results: [{ transcript: '你好', isFinal: false }] },
        { delay: 180, type: 'result', results: [{ transcript: '你好 世界', isFinal: true }] },
      ],
    });

    await getVoiceButton(page).click();
    await expect(page.getByText('Listening with Browser dictation... pause to finish', { exact: true })).toBeVisible();
    await expect(getVoiceDraftReadyText(page, 'Browser dictation')).toBeVisible({ timeout: 7000 });
    await expect(getComposer(page)).toHaveValue('');
    await getInsertButton(page).click();
    await expect(getComposer(page)).toHaveValue('你好 世界');
  });

  test('browser speech draft can be inserted with Enter even when focus remains on the voice button', async ({ page }) => {
    await mockChatBootstrap(page, {
      prefs: {
        language: 'zh',
        voice_input_enabled: true,
        voice_input_provider: 'browser',
        voice_input_language: 'zh-CN',
      },
      agents: [
        { id: 'default', name: 'Default Agent', system_prompt: 'sys', provider: 'openai', model: 'gpt-4o-mini', enabled_tools: [] },
      ],
    });

    await page.goto('/');
    await expect(getComposer(page)).toBeVisible();

    await page.evaluate((scenario: BrowserScenario) => {
      (window as any).__voiceInputTest.queueBrowserScenario(scenario);
    }, {
      steps: [
        { delay: 50, type: 'result', results: [{ transcript: '键盘 插入', isFinal: true }] },
      ],
    });

    await getVoiceButton(page).click();
    await expect(getVoiceDraftReadyText(page, 'Browser dictation')).toBeVisible({ timeout: 4000 });
    await page.keyboard.press('Enter');
    await expect(getComposer(page)).toHaveValue('键盘 插入');
  });

  test('browser speech draft can be sent directly from the voice draft card', async ({ page }) => {
    await mockChatBootstrap(page, {
      prefs: {
        language: 'zh',
        voice_input_enabled: true,
        voice_input_provider: 'browser',
        voice_input_language: 'zh-CN',
      },
      agents: [
        { id: 'default', name: 'Default Agent', system_prompt: 'sys', provider: 'openai', model: 'gpt-4o-mini', enabled_tools: [] },
      ],
    });

    await page.goto('/');
    await expect(getComposer(page)).toBeVisible();

    await page.evaluate((scenario: BrowserScenario) => {
      (window as any).__voiceInputTest.queueBrowserScenario(scenario);
    }, {
      steps: [
        { delay: 50, type: 'result', results: [{ transcript: '直接 发送', isFinal: true }] },
      ],
    });

    await getVoiceButton(page).click();
    await expect(getVoiceDraftReadyText(page, 'Browser dictation')).toBeVisible({ timeout: 4000 });
    await getSendVoiceButton(page).click();
    await expect(getComposer(page)).toHaveValue('');
    await expect(getVoiceDraftReadyText(page, 'Browser dictation')).toHaveCount(0);
  });

  test('browser speech draft can be sent with Cmd/Ctrl+Enter from the keyboard', async ({ page, browserName }) => {
    await mockChatBootstrap(page, {
      prefs: {
        language: 'zh',
        voice_input_enabled: true,
        voice_input_provider: 'browser',
        voice_input_language: 'zh-CN',
      },
      agents: [
        { id: 'default', name: 'Default Agent', system_prompt: 'sys', provider: 'openai', model: 'gpt-4o-mini', enabled_tools: [] },
      ],
    });

    await page.goto('/');
    await expect(getComposer(page)).toBeVisible();

    await page.evaluate((scenario: BrowserScenario) => {
      (window as any).__voiceInputTest.queueBrowserScenario(scenario);
    }, {
      steps: [
        { delay: 50, type: 'result', results: [{ transcript: '快捷键 发送', isFinal: true }] },
      ],
    });

    await getVoiceButton(page).click();
    await expect(getVoiceDraftReadyText(page, 'Browser dictation')).toBeVisible({ timeout: 4000 });
    await page.keyboard.press(browserName === 'webkit' ? 'Meta+Enter' : 'Control+Enter');
    await expect(getComposer(page)).toHaveValue('');
    await expect(getVoiceDraftReadyText(page, 'Browser dictation')).toHaveCount(0);
  });

  test('browser speech draft can be discarded with Escape from the keyboard', async ({ page }) => {
    await mockChatBootstrap(page, {
      prefs: {
        language: 'zh',
        voice_input_enabled: true,
        voice_input_provider: 'browser',
        voice_input_language: 'zh-CN',
      },
      agents: [
        { id: 'default', name: 'Default Agent', system_prompt: 'sys', provider: 'openai', model: 'gpt-4o-mini', enabled_tools: [] },
      ],
    });

    await page.goto('/');
    await expect(getComposer(page)).toBeVisible();

    await page.evaluate((scenario: BrowserScenario) => {
      (window as any).__voiceInputTest.queueBrowserScenario(scenario);
    }, {
      steps: [
        { delay: 50, type: 'result', results: [{ transcript: '丢弃 草稿', isFinal: true }] },
      ],
    });

    await getVoiceButton(page).click();
    await expect(getVoiceDraftReadyText(page, 'Browser dictation')).toBeVisible({ timeout: 4000 });
    await page.keyboard.press('Escape');
    await expect(getVoiceDraftReadyText(page, 'Browser dictation')).toHaveCount(0);
    await expect(getComposer(page)).toHaveValue('');
  });

  test('azure speech uses tokenized cloud STT and inserts recognized draft explicitly', async ({ page }) => {
    await mockChatBootstrap(page, {
      prefs: {
        language: 'en',
        voice_input_enabled: true,
        voice_input_provider: 'azure',
        voice_input_language: 'en-US',
      },
      agents: [
        {
          id: 'azure-agent',
          name: 'Azure Agent',
          system_prompt: 'sys',
          provider: 'openai',
          model: 'gpt-4o-mini',
          enabled_tools: [],
          voice_input_enabled: true,
          voice_input_provider: 'azure',
          voice_azure_config: { region: 'eastus', endpoint_id: '', api_key_configured: true },
        },
      ],
      tokenResponse: {
        status: 200,
        body: { token: 'mock-token', region: 'eastus', endpoint_id: '' },
      },
    });

    await page.goto('/');
    await expect(getComposer(page)).toBeVisible();
    await page.evaluate(() => {
      (window as any).__voiceInputTest.installAzureSpeechSdkMock();
    });
    await selectAgentByMention(page, 'Azure Agent');
    await page.evaluate((scenario: AzureScenario) => {
      (window as any).__voiceInputTest.queueAzureScenario(scenario);
    }, {
      steps: [
        { delay: 80, type: 'recognizing', text: 'hello' },
        { delay: 160, type: 'recognized', text: 'hello azure' },
      ],
    });

    await getVoiceButton(page).click();
    await expect(page.getByText('Listening with Azure Speech... pause to finish', { exact: true })).toBeVisible();
    await expect(getVoiceDraftReadyText(page, 'Azure Speech')).toBeVisible({ timeout: 7000 });
    await expect(getComposer(page)).toHaveValue('');
    await getInsertButton(page).click();
    await expect(getComposer(page)).toHaveValue('hello azure');
  });

  test('azure token failure falls back to browser dictation and still produces an insertable draft', async ({ page }) => {
    await mockChatBootstrap(page, {
      prefs: {
        language: 'en',
        voice_input_enabled: true,
        voice_input_provider: 'azure',
        voice_input_language: 'en-US',
      },
      agents: [
        {
          id: 'fallback-agent',
          name: 'Fallback Agent',
          system_prompt: 'sys',
          provider: 'openai',
          model: 'gpt-4o-mini',
          enabled_tools: [],
          voice_input_enabled: true,
          voice_input_provider: 'azure',
          voice_azure_config: { region: 'eastus', endpoint_id: '', api_key_configured: true },
        },
      ],
      tokenResponse: {
        status: 500,
        body: 'mock azure token failure',
      },
    });

    await page.goto('/');
    await expect(getComposer(page)).toBeVisible();
    await page.evaluate(() => {
      (window as any).__voiceInputTest.installAzureSpeechSdkMock();
    });
    await selectAgentByMention(page, 'Fallback Agent');
    await page.evaluate((scenario: BrowserScenario) => {
      (window as any).__voiceInputTest.queueBrowserScenario(scenario);
    }, {
      steps: [
        { delay: 60, type: 'result', results: [{ transcript: 'fallback works', isFinal: true }] },
      ],
    });

    await getVoiceButton(page).click();
    await expect(page.getByText('Using Browser dictation')).toBeVisible();
    await expect(page.getByText('Azure Speech unavailable. Switched to browser dictation.')).toBeVisible();
    await expect(getVoiceDraftReadyText(page, 'Browser dictation')).toBeVisible({ timeout: 4000 });
    await getInsertButton(page).click();
    await expect(getComposer(page)).toHaveValue('fallback works');
  });

  test('starting a new recording after discard does not leak the previous draft', async ({ page }) => {
    await mockChatBootstrap(page, {
      prefs: {
        language: 'zh',
        voice_input_enabled: true,
        voice_input_provider: 'browser',
        voice_input_language: 'zh-CN',
      },
      agents: [
        { id: 'default', name: 'Default Agent', system_prompt: 'sys', provider: 'openai', model: 'gpt-4o-mini', enabled_tools: [] },
      ],
    });

    await page.goto('/');
    await expect(getComposer(page)).toBeVisible();

    await page.evaluate((scenario: BrowserScenario) => {
      (window as any).__voiceInputTest.queueBrowserScenario(scenario);
    }, {
      steps: [
        { delay: 50, type: 'result', results: [{ transcript: '第一次', isFinal: true }] },
      ],
    });

    await getVoiceButton(page).click();
    await expect(getVoiceDraftReadyText(page, 'Browser dictation')).toBeVisible({ timeout: 4000 });
    await getDiscardButton(page).click();
    await expect(getVoiceDraftReadyText(page, 'Browser dictation')).toHaveCount(0);

    await page.evaluate((scenario: BrowserScenario) => {
      (window as any).__voiceInputTest.queueBrowserScenario(scenario);
    }, {
      steps: [
        { delay: 50, type: 'result', results: [{ transcript: '第二次', isFinal: true }] },
      ],
    });

    await getVoiceButton(page).click();
    await expect(getVoiceDraftReadyText(page, 'Browser dictation')).toBeVisible({ timeout: 4000 });
    await getInsertButton(page).click();
    await expect(getComposer(page)).toHaveValue('第二次');
  });
});
