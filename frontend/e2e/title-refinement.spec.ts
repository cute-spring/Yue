import { test, expect } from '@playwright/test'
import { mockBasicChatBootstrap } from './chat-test-helpers'

test('chat title is refined in sidebar after first assistant response', async ({ page }) => {
  test.setTimeout(120000)
  const question = 'Build a minimal JWT auth module for FastAPI with register login refresh and middleware'
  const placeholderTitle = question.length > 30 ? `${question.slice(0, 30)}...` : question
  const refinedTitle = `FastAPI JWT auth module ${Date.now()}`
  let historyCalls = 0
  let metaCalls = 0

  await mockBasicChatBootstrap(page)
  await page.route('**/api/chat/history', async route => {
    historyCalls += 1
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([])
    })
  })
  await page.route('**/api/chat/chat-1/meta', async route => {
    metaCalls += 1
    const title = metaCalls >= 3 ? refinedTitle : placeholderTitle
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'chat-1',
        title,
        summary: null,
        updated_at: '2026-03-18T00:00:00Z'
      })
    })
  })
  await page.route('**/api/chat/stream', async route => {
    const stream = [
      `data: ${JSON.stringify({ chat_id: 'chat-1' })}\n\n`,
      `data: ${JSON.stringify({ content: 'Sure, here is a minimal implementation plan.' })}\n\n`
    ].join('')
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body: stream
    })
  })

  await page.addInitScript(() => {
    localStorage.setItem('yue_selected_provider', 'openai')
    localStorage.setItem('yue_selected_model', 'gpt-4o-mini')
    localStorage.setItem('selected_provider', 'openai')
    localStorage.setItem('selected_model', 'gpt-4o-mini')
  })

  await page.goto('/', { waitUntil: 'networkidle' })

  const input = page.locator('textarea').first()
  await expect(input).toBeVisible({ timeout: 15000 })
  await input.fill(question)
  await input.press('Enter')

  await expect.poll(() => metaCalls, { timeout: 90000 }).toBeGreaterThanOrEqual(3)
  await expect(page.getByRole('heading', { level: 3, name: refinedTitle })).toBeVisible({ timeout: 90000 })
  expect(historyCalls).toBeLessThanOrEqual(1)
})
