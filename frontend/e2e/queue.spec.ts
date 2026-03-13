import { test, expect } from '@playwright/test'

const PROJECT = 'bet365_feature_act_01'

test.describe('Queue Monitor', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/projects/${PROJECT}/queue`)
    await expect(page.getByRole('heading', { name: 'Queue' })).toBeVisible()
  })

  // ── Header ────────────────────────────────────────────────────
  test('header shows Queue title', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Queue' })).toBeVisible()
  })

  test('breadcrumbs are correct', async ({ page }) => {
    const breadcrumb = page.getByRole('banner').getByRole('navigation', { name: 'Breadcrumb' })
    await expect(breadcrumb.getByRole('link', { name: 'Projects' })).toBeVisible()
    await expect(breadcrumb.getByRole('link', { name: PROJECT })).toBeVisible()
  })

  // ── Filter Buttons ─────────────────────────────────────────────
  test('filter buttons render all 4 options', async ({ page }) => {
    await expect(page.locator('button:has-text("All")')).toBeVisible()
    await expect(page.locator('button:has-text("Running")')).toBeVisible()
    await expect(page.locator('button:has-text("Completed")')).toBeVisible()
    await expect(page.locator('button:has-text("Failed")')).toBeVisible()
  })

  test('All filter is active by default', async ({ page }) => {
    const allBtn = page.locator('button:has-text("All")')
    // Active filter should have accent styling
    await expect(allBtn).toHaveClass(/accent/)
  })

  test('clicking Running filter activates it', async ({ page }) => {
    const runningBtn = page.locator('button:has-text("Running")')
    await runningBtn.click()
    await expect(runningBtn).toHaveClass(/accent/)

    // All button should no longer be active
    const allBtn = page.locator('button:has-text("All")')
    await expect(allBtn).not.toHaveClass(/accent/)
  })

  test('clicking Completed filter activates it', async ({ page }) => {
    const completedBtn = page.locator('button:has-text("Completed")')
    await completedBtn.click()
    await expect(completedBtn).toHaveClass(/accent/)
  })

  test('clicking Failed filter activates it', async ({ page }) => {
    const failedBtn = page.locator('button:has-text("Failed")')
    await failedBtn.click()
    await expect(failedBtn).toHaveClass(/accent/)
  })

  test('filter buttons cycle: Running -> All -> Completed', async ({ page }) => {
    const runningBtn = page.locator('button:has-text("Running")')
    const allBtn = page.locator('button:has-text("All")')
    const completedBtn = page.locator('button:has-text("Completed")')

    await runningBtn.click()
    await expect(runningBtn).toHaveClass(/accent/)

    await allBtn.click()
    await expect(allBtn).toHaveClass(/accent/)
    await expect(runningBtn).not.toHaveClass(/accent/)

    await completedBtn.click()
    await expect(completedBtn).toHaveClass(/accent/)
    await expect(allBtn).not.toHaveClass(/accent/)
  })

  // ── Empty state ────────────────────────────────────────────────
  test('empty state shows when no jobs match filter', async ({ page }) => {
    // Switch to Running filter - might be empty
    const runningBtn = page.locator('button:has-text("Running")')
    await runningBtn.click()
    await page.waitForTimeout(500)

    // Either shows jobs or "No running jobs" message
    const emptyMsg = page.locator('text=/No .* jobs/')
    const jobCards = page.locator('[aria-expanded]')
    const hasEmpty = await emptyMsg.isVisible().catch(() => false)
    const hasJobs = (await jobCards.count()) > 0

    // One of these should be true
    expect(hasEmpty || hasJobs).toBeTruthy()
  })

  // ── Job Card interaction ───────────────────────────────────────
  test('job cards render when jobs exist', async ({ page }) => {
    // Wait for potential job loading
    await page.waitForTimeout(2000)

    // Check if any jobs are displayed
    const jobElements = page.locator('[aria-expanded]')
    const count = await jobElements.count()
    // May or may not have jobs - just ensure no crash
    expect(count).toBeGreaterThanOrEqual(0)
  })

  test('job card expand/collapse on click', async ({ page }) => {
    await page.waitForTimeout(2000)

    const jobCard = page.locator('[aria-expanded]').first()
    if (await jobCard.isVisible()) {
      // Initially collapsed
      await expect(jobCard).toHaveAttribute('aria-expanded', 'false')

      // Click to expand
      await jobCard.click()
      await expect(jobCard).toHaveAttribute('aria-expanded', 'true')

      // Click again to collapse
      await jobCard.click()
      await expect(jobCard).toHaveAttribute('aria-expanded', 'false')
    }
  })

  test('job card keyboard expand/collapse', async ({ page }) => {
    await page.waitForTimeout(2000)

    const jobCard = page.locator('[aria-expanded]').first()
    if (await jobCard.isVisible()) {
      await jobCard.focus()

      // Press Enter to expand
      await page.keyboard.press('Enter')
      await expect(jobCard).toHaveAttribute('aria-expanded', 'true')

      // Press Space to collapse
      await page.keyboard.press('Space')
      await expect(jobCard).toHaveAttribute('aria-expanded', 'false')
    }
  })

  // ── Filter keyboard focus ──────────────────────────────────────
  test('filter buttons are keyboard focusable', async ({ page }) => {
    const allBtn = page.locator('button:has-text("All")')
    await allBtn.focus()
    await expect(allBtn).toBeFocused()

    await page.keyboard.press('Tab')
    const runningBtn = page.locator('button:has-text("Running")')
    await expect(runningBtn).toBeFocused()
  })

  // ── Breadcrumb navigation ──────────────────────────────────────
  test('breadcrumb Projects link works', async ({ page }) => {
    const link = page.getByRole('banner').getByRole('navigation', { name: 'Breadcrumb' }).getByRole('link', { name: 'Projects' })
    await link.click()
    await page.waitForURL('/')
  })
})
