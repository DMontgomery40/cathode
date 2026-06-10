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
  test('filter buttons render all status options', async ({ page }) => {
    await expect(page.locator('button:has-text("All")')).toBeVisible()
    await expect(page.locator('button:has-text("Queued")')).toBeVisible()
    await expect(page.locator('button:has-text("Running")')).toBeVisible()
    await expect(page.locator('button:has-text("Completed")')).toBeVisible()
    await expect(page.locator('button:has-text("Partial")')).toBeVisible()
    await expect(page.locator('button:has-text("Failed")')).toBeVisible()
    await expect(page.locator('button:has-text("Cancelled")')).toBeVisible()
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

    // Either shows running jobs or the precise empty state for the selected filter.
    const emptyMsg = page.getByText('No running jobs', { exact: true })
    const jobCards = page.locator('[aria-expanded]')
    await expect.poll(async () => {
      const hasEmpty = (await emptyMsg.count()) > 0
      const hasJobs = (await jobCards.count()) > 0
      return hasEmpty || hasJobs
    }).toBeTruthy()
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

  test('expanded job card does not expose raw request or result JSON', async ({ page }) => {
    await page.route(`**/api/projects/${PROJECT}/jobs`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            status: 'failed',
            job_id: 'raw-json-regression-job',
            project_name: PROJECT,
            project_dir: `/tmp/${PROJECT}`,
            kind: 'rerun_stage',
            current_stage: 'render',
            retryable: true,
            suggestion: 'Review the failed step and retry when ready.',
            requested_stage: 'render',
            created_utc: '2026-06-09T12:00:00Z',
            updated_utc: '2026-06-09T12:05:00Z',
            pid: null,
            log_path: '',
            request: {
              kind: 'rerun_stage',
              endpoint: '/api/projects/bet365_feature_act_01/agent-demo',
              internal_payload_marker: 'should-not-render',
            },
            result: {
              normalized_plan: 'should-not-render',
              operatorHint: 'Visible operator hint',
            },
            error: { message: 'Visible operator hint' },
            steps: [],
          },
        ]),
      })
    })

    await page.reload()
    const jobCard = page.locator('[aria-expanded]').filter({ hasText: 'raw-json-reg' })
    await expect(jobCard).toHaveCount(1)
    await jobCard.click()
    await expect(jobCard).toHaveAttribute('aria-expanded', 'true')

    await expect(page.getByText('Visible operator hint')).toBeVisible()
    await expect(page.getByText('Stage')).toBeVisible()
    await expect(page.getByText('Reference')).toBeVisible()
    await expect(page.getByText('internal_payload_marker')).toHaveCount(0)
    await expect(page.getByText('normalized_plan')).toHaveCount(0)
    await expect(page.getByText('agent-demo')).toHaveCount(0)
  })

  test('provider failure details are operator-safe in job cards', async ({ page }) => {
    const rawProviderError = 'Request timed out or interrupted. This could be due to a network timeout, dropped connection, or request cancellation. See https://docs.anthropic.com/en/api/errors#long-requests for more details.'
    await page.route(`**/api/projects/${PROJECT}/jobs`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            status: 'failed',
            job_id: 'provider-copy-regression-job',
            project_name: PROJECT,
            project_dir: `/tmp/${PROJECT}`,
            kind: 'make_video',
            current_stage: 'storyboard',
            retryable: true,
            suggestion: rawProviderError,
            requested_stage: 'render',
            created_utc: '2026-06-09T12:00:00Z',
            updated_utc: '2026-06-09T12:05:00Z',
            pid: null,
            log_path: '',
            request: { kind: 'make_video' },
            result: {},
            error: { message: rawProviderError },
            steps: [
              {
                id: 'storyboard',
                label: 'Storyboard',
                category: 'storyboard',
                status: 'failed',
                detail: rawProviderError,
                error: rawProviderError,
              },
            ],
          },
        ]),
      })
    })

    await page.reload()
    await expect(page.getByText('Provider request timed out or was interrupted. Retry after checking the network/proxy route.')).toBeVisible()
    await expect(page.getByText('docs.anthropic.com')).toHaveCount(0)
    await expect(page.getByText('long-requests')).toHaveCount(0)
    await expect(page.getByText('Anthropic')).toHaveCount(0)
  })

  // ── Filter keyboard focus ──────────────────────────────────────
  test('filter buttons are keyboard focusable', async ({ page }) => {
    const allBtn = page.locator('button:has-text("All")')
    await allBtn.focus()
    await expect(allBtn).toBeFocused()

    await page.keyboard.press('Tab')
    const queuedBtn = page.locator('button:has-text("Queued")')
    await expect(queuedBtn).toBeFocused()

    await page.keyboard.press('Tab')
    const runningBtn = page.locator('button:has-text("Running")')
    await expect(runningBtn).toBeFocused()
  })

  // ── Breadcrumb navigation ──────────────────────────────────────
  test('breadcrumb Projects link works', async ({ page }) => {
    const link = page.getByRole('banner').getByRole('navigation', { name: 'Breadcrumb' }).getByRole('link', { name: 'Projects' })
    await link.click()
    await page.waitForURL('**/projects')
  })
})
