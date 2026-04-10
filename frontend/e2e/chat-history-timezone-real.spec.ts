import { expect, test, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const BACKEND_PYTHON = path.join(REPO_ROOT, 'backend', '.venv', 'bin', 'python');
const SEED_SCRIPT = path.join(REPO_ROOT, 'backend', 'scripts', 'seed_chat_history_timezone_e2e.py');
const E2E_DATA_DIR = process.env.YUE_E2E_DATA_DIR || '/tmp/yue-e2e-real-data';

const seedScenario = (scenario: string) => {
  execFileSync(BACKEND_PYTHON, [SEED_SCRIPT, '--data-dir', E2E_DATA_DIR, '--scenario', scenario], {
    cwd: REPO_ROOT,
    env: {
      ...process.env,
      PYTHONPATH: 'backend',
      YUE_DATA_DIR: E2E_DATA_DIR,
    },
    stdio: 'inherit',
  });
};

const freezeNow = async (page: Page, fixedNowIso: string) => {
  await page.addInitScript(({ frozenIso }) => {
    const fixedNowMs = new Date(frozenIso).getTime();
    const RealDate = Date;
    class MockDate extends RealDate {
      constructor(...args: ConstructorParameters<typeof Date>) {
        if (args.length === 0) {
          super(fixedNowMs);
          return;
        }
        super(...args);
      }
      static now() {
        return fixedNowMs;
      }
      static parse = RealDate.parse;
      static UTC = RealDate.UTC;
    }
    Object.setPrototypeOf(MockDate, RealDate);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).Date = MockDate;
  }, { frozenIso: fixedNowIso });
};

test('real backend + real db: cross-midnight UTC history is grouped into local dates', async ({ page }) => {
  seedScenario('cross_midnight');
  await freezeNow(page, '2026-04-11T01:00:00+08:00');

  await page.goto('/', { waitUntil: 'networkidle' });

  const todayGroup = page.getByRole('button', { name: 'Toggle date group 4/11/2026' });
  const yesterdayGroup = page.getByRole('button', { name: 'Toggle date group 4/10/2026' });

  await expect(todayGroup).toHaveAttribute('aria-expanded', 'true');
  await expect(yesterdayGroup).toHaveAttribute('aria-expanded', 'false');

  await expect(page.getByText('Timezone Today Session')).toBeVisible();
  await expect(page.getByText('Timezone Yesterday Session')).not.toBeVisible();

  await yesterdayGroup.click();
  await expect(yesterdayGroup).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByText('Timezone Yesterday Session')).toBeVisible();
});

test('real backend + real db: new session is grouped into Today after refresh', async ({ page }) => {
  seedScenario('new_chat_base');
  await freezeNow(page, '2026-04-11T01:00:00+08:00');

  await page.goto('/', { waitUntil: 'networkidle' });
  await expect(page.getByRole('button', { name: 'Toggle date group 4/10/2026' })).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByRole('button', { name: 'Toggle date group 4/11/2026' })).toHaveCount(0);

  seedScenario('append_today_new_chat');
  await page.reload({ waitUntil: 'networkidle' });

  const todayGroup = page.getByRole('button', { name: 'Toggle date group 4/11/2026' });
  const yesterdayGroup = page.getByRole('button', { name: 'Toggle date group 4/10/2026' });
  await expect(todayGroup).toHaveAttribute('aria-expanded', 'true');
  await expect(yesterdayGroup).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByText('Fresh Today Session')).toBeVisible();
});

test('real backend + real db: date groups expand and collapse correctly', async ({ page }) => {
  seedScenario('expand_collapse');
  await freezeNow(page, '2026-04-11T12:00:00+08:00');

  await page.goto('/', { waitUntil: 'networkidle' });

  const todayGroup = page.getByRole('button', { name: 'Toggle date group 4/11/2026' });
  const yesterdayGroup = page.getByRole('button', { name: 'Toggle date group 4/10/2026' });
  const twoDaysGroup = page.getByRole('button', { name: 'Toggle date group 4/9/2026' });

  await expect(todayGroup).toHaveAttribute('aria-expanded', 'true');
  await expect(yesterdayGroup).toHaveAttribute('aria-expanded', 'false');
  await expect(twoDaysGroup).toHaveAttribute('aria-expanded', 'false');

  await yesterdayGroup.click();
  await expect(yesterdayGroup).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByText('Yesterday A')).toBeVisible();
  await expect(page.getByText('Yesterday B')).toBeVisible();

  await yesterdayGroup.click();
  await expect(yesterdayGroup).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByText('Yesterday A')).not.toBeVisible();
  await expect(page.getByText('Yesterday B')).not.toBeVisible();

  await twoDaysGroup.click();
  await expect(twoDaysGroup).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByText('TwoDaysAgo')).toBeVisible();
});

test('real backend + real db: date presets respect local day boundaries', async ({ page }) => {
  seedScenario('date_presets');
  await freezeNow(page, '2026-04-11T12:00:00+08:00');

  await page.goto('/', { waitUntil: 'networkidle' });

  await page.getByRole('button', { name: 'Today' }).click();
  await expect(page.getByRole('button', { name: 'Toggle date group 4/11/2026' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle date group 4/5/2026' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Toggle date group 4/4/2026' })).toHaveCount(0);

  await page.getByRole('button', { name: '7d' }).click();
  await expect(page.getByRole('button', { name: 'Toggle date group 4/11/2026' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle date group 4/5/2026' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle date group 4/4/2026' })).toHaveCount(0);

  await page.getByRole('button', { name: '30d' }).click();
  await expect(page.getByRole('button', { name: 'Toggle date group 4/11/2026' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle date group 4/5/2026' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle date group 4/4/2026' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle date group 3/13/2026' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle date group 3/12/2026' })).toHaveCount(0);
});

test('real backend + real db: tag filter works under date grouping', async ({ page }) => {
  seedScenario('tag_filter_search');
  await freezeNow(page, '2026-04-11T12:00:00+08:00');

  await page.goto('/', { waitUntil: 'networkidle' });

  await page.getByRole('button', { name: '#api' }).first().click();

  await expect(page.getByRole('button', { name: 'Toggle date group 4/11/2026' })).toBeVisible();
  const yesterdayGroup = page.getByRole('button', { name: 'Toggle date group 4/10/2026' });
  await expect(yesterdayGroup).toBeVisible();
  await expect(page.getByText('Tag Today API')).toBeVisible();
  await expect(page.getByText('Tag Yesterday Design')).toHaveCount(0);

  await yesterdayGroup.click();
  await expect(page.getByText('Tag Yesterday API')).toBeVisible();
  await expect(page.getByText('Tag Yesterday Design')).toHaveCount(0);
});

test('real backend + real db: search and date grouping stay consistent', async ({ page }) => {
  seedScenario('tag_filter_search');
  await freezeNow(page, '2026-04-11T12:00:00+08:00');

  await page.goto('/', { waitUntil: 'networkidle' });
  await page.getByPlaceholder('Search title, summary, tags...').fill('design');

  await expect(page.getByRole('button', { name: 'Toggle date group 4/10/2026' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle date group 4/11/2026' })).toHaveCount(0);

  const yesterdayGroup = page.getByRole('button', { name: 'Toggle date group 4/10/2026' });
  await expect(yesterdayGroup).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByText('Tag Yesterday Design')).not.toBeVisible();
  await yesterdayGroup.click();
  await expect(page.getByText('Tag Yesterday Design')).toBeVisible();
  await expect(page.getByText('Tag Yesterday API')).toHaveCount(0);
});

test.describe('timezone matrix for cross-midnight grouping', () => {
  test.use({ timezoneId: 'Asia/Shanghai' });
  test('asia/shanghai: split into 4/11 and 4/10 groups', async ({ page }) => {
    seedScenario('cross_midnight');
    await freezeNow(page, '2026-04-11T01:00:00+08:00');
    await page.goto('/', { waitUntil: 'networkidle' });
    await expect(page.getByRole('button', { name: 'Toggle date group 4/11/2026' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Toggle date group 4/10/2026' })).toBeVisible();
  });
});

test.describe('timezone matrix for cross-midnight grouping in UTC', () => {
  test.use({ timezoneId: 'UTC' });
  test('utc: merged into 4/10 group as local today', async ({ page }) => {
    seedScenario('cross_midnight');
    await freezeNow(page, '2026-04-11T01:00:00+08:00');
    await page.goto('/', { waitUntil: 'networkidle' });
    await expect(page.getByRole('button', { name: 'Toggle date group 4/10/2026' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Toggle date group 4/11/2026' })).toHaveCount(0);
    await expect(page.getByText('Timezone Today Session')).toBeVisible();
    await expect(page.getByText('Timezone Yesterday Session')).toBeVisible();
  });
});

test.describe('timezone matrix for cross-midnight grouping in America/Los_Angeles', () => {
  test.use({ timezoneId: 'America/Los_Angeles' });
  test('los_angeles: merged into 4/10 group as local today', async ({ page }) => {
    seedScenario('cross_midnight');
    await freezeNow(page, '2026-04-11T01:00:00+08:00');
    await page.goto('/', { waitUntil: 'networkidle' });
    await expect(page.getByRole('button', { name: 'Toggle date group 4/10/2026' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Toggle date group 4/11/2026' })).toHaveCount(0);
    await expect(page.getByText('Timezone Today Session')).toBeVisible();
    await expect(page.getByText('Timezone Yesterday Session')).toBeVisible();
  });
});
