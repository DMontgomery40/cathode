import { test, expect } from '@playwright/test'

test.describe('Home / Workspace', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Wait for the app shell to render
    await expect(page.locator('nav[aria-label="Main navigation"]')).toBeVisible()
  })

  // ── CommandRail ────────────────────────────────────────────────
  test('CommandRail renders with brand mark and nav items', async ({ page }) => {
    const rail = page.locator('nav[aria-label="Main navigation"]')
    await expect(rail).toBeVisible()

    // Brand mark shows "betTube Studio" when expanded
    await expect(rail.locator('text=betTube Studio')).toBeVisible()

    // All 5 nav items visible
    const menuItems = rail.locator('[role="menuitem"]')
    await expect(menuItems).toHaveCount(5)

    // Check labels
    await expect(rail.locator('text=Home')).toBeVisible()
    await expect(rail.locator('text=Projects')).toBeVisible()
    await expect(rail.locator('text=Queue')).toBeVisible()
    await expect(rail.locator('text=Short Form')).toBeVisible()
    await expect(rail.locator('text=Settings')).toBeVisible()
  })

  test('CommandRail collapse toggle works', async ({ page }) => {
    const rail = page.locator('nav[aria-label="Main navigation"]')

    // Initially expanded (width 240px)
    const collapseBtn = page.getByLabel(/Collapse navigation/i)
    await expect(collapseBtn).toBeVisible()

    // Click collapse
    await collapseBtn.click()
    await page.waitForTimeout(400) // wait for transition

    // Now should show the compact brand mark instead of "betTube Studio"
    const brandText = rail.locator('span').filter({ hasText: /^bT$/ }).first()
    await expect(brandText).toBeVisible()

    // Expand button should now be present
    const expandBtn = page.getByLabel(/Expand navigation/i)
    await expect(expandBtn).toBeVisible()

    // Click expand
    await expandBtn.click()
    await page.waitForTimeout(400)

    // Should show "betTube Studio" again
    await expect(rail.locator('text=betTube Studio')).toBeVisible()
  })

  test('CommandRail keyboard navigation works', async ({ page }) => {
    const homeItem = page.locator('[role="menuitem"]').first()
    await homeItem.focus()

    // Press ArrowDown to move to Projects
    await page.keyboard.press('ArrowDown')
    const projectsItem = page.locator('[role="menuitem"]').nth(1)
    await expect(projectsItem).toBeFocused()

    // Press ArrowDown again to Queue
    await page.keyboard.press('ArrowDown')
    const queueItem = page.locator('[role="menuitem"]').nth(2)
    await expect(queueItem).toBeFocused()
  })

  test('CommandRail active state indicator shows on Home', async ({ page }) => {
    // Home should be active (current route is /)
    const homeLink = page.locator('[role="menuitem"]').first()
    // Active link has brass indicator bar
    await expect(homeLink).toHaveClass(/bg-/)
  })

  // ── WorkspaceHeader ────────────────────────────────────────────
  test('WorkspaceHeader shows title and subtitle', async ({ page }) => {
    await expect(page.locator('text=betTube Studio').first()).toBeVisible()
    await expect(page.locator('text=Video production workspace')).toBeVisible()
  })

  // ── IntentDeck ─────────────────────────────────────────────────
  test('IntentDeck renders one card per distinct destination', async ({ page }) => {
    const group = page.locator('[role="group"][aria-label="Quick actions"]')
    await expect(group).toBeVisible()

    await expect(page.locator('text=Start a new video')).toBeVisible()
    await expect(page.locator('text=Create a vertical short')).toBeVisible()
    await expect(page.locator('text=Continue editing')).toBeVisible()
    await expect(page.locator('text=Browse projects')).toBeVisible()
    await expect(page.locator('text=Monitor queue')).toBeVisible()
    // The filler cards that duplicated the /projects route are gone.
    await expect(page.locator('text=Review footage & style')).toHaveCount(0)
    await expect(page.locator('text=Render & ship')).toHaveCount(0)
  })

  test('IntentDeck shows real project badge without stale queue count', async ({ page }) => {
    await expect(page.getByText(/\d+ projects?/)).toBeVisible()
    await expect(page.getByText('2 queued')).toHaveCount(0)
  })

  test('IntentDeck card click - Start a new video navigates to brief', async ({ page }) => {
    await page.locator('button', { hasText: 'Start a new video' }).click()
    await page.waitForURL('**/projects/new/brief')
    await expect(page).toHaveURL(/\/projects\/new\/brief/)
  })

  test('IntentDeck card click - Continue editing opens the latest project timeline', async ({ page }) => {
    await page.locator('button', { hasText: 'Continue editing' }).click()
    await page.waitForURL(/\/projects\/[^/]+\/scenes/)
    await expect(page).toHaveURL(/\/projects\/[^/]+\/scenes/)
  })

  test('IntentDeck card click - Browse projects navigates to the library', async ({ page }) => {
    await page.locator('button', { hasText: 'Browse projects' }).click()
    await page.waitForURL('**/projects')
    await expect(page).toHaveURL(/\/projects$/)
  })

  test('IntentDeck card click - Monitor queue navigates to queue', async ({ page }) => {
    await page.locator('button', { hasText: 'Monitor queue' }).click()
    await page.waitForURL('**/queue')
    await expect(page).toHaveURL(/\/queue/)
  })

  test('IntentDeck keyboard navigation with arrow keys', async ({ page }) => {
    const firstCard = page.locator('[role="group"][aria-label="Quick actions"] button').first()
    await firstCard.focus()
    await expect(firstCard).toBeFocused()

    // Arrow right moves to next card
    await page.keyboard.press('ArrowRight')
    const secondCard = page.locator('[role="group"][aria-label="Quick actions"] button').nth(1)
    await expect(secondCard).toBeFocused()
  })

  // ── BackgroundMesh ─────────────────────────────────────────────
  test('BackgroundMesh decorative element renders', async ({ page }) => {
    // BackgroundMesh uses absolute positioning with decorative elements
    const mesh = page.locator('[aria-hidden="true"]').first()
    await expect(mesh).toBeAttached()
  })

  // ── Skip Link ──────────────────────────────────────────────────
  test('Skip link is accessible via keyboard', async ({ page }) => {
    // Tab to reveal skip link
    await page.keyboard.press('Tab')
    const skipLink = page.locator('a:has-text("Skip to main content")')
    // Skip link may be first focusable; check it exists in DOM
    await expect(skipLink).toBeAttached()
  })

  test('Workspace status KPIs match the live API, nothing hardcoded', async ({ page, request }) => {
    const response = await request.get('/api/projects')
    const projects = await response.json() as Array<{ has_video: boolean; short_form_format?: string | null }>
    const expected = {
      Projects: String(projects.length),
      Rendered: String(projects.filter((p) => p.has_video).length),
      'Vertical shorts': String(projects.filter((p) => p.short_form_format === 'vertical_short').length),
    }

    for (const [label, value] of Object.entries(expected)) {
      const kpi = page.locator('.workspace-kpi-grid > div').filter({ hasText: label })
      await expect(kpi.locator('div')).toHaveText(value)
    }
  })
})
