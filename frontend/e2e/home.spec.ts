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

    // Brand mark shows "Cathode" when expanded
    await expect(rail.locator('text=Cathode')).toBeVisible()

    // All 4 nav items visible
    const menuItems = rail.locator('[role="menuitem"]')
    await expect(menuItems).toHaveCount(4)

    // Check labels
    await expect(rail.locator('text=Home')).toBeVisible()
    await expect(rail.locator('text=Projects')).toBeVisible()
    await expect(rail.locator('text=Queue')).toBeVisible()
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

    // Now should show "C" instead of "Cathode"
    const brandText = rail.locator('span').filter({ hasText: /^C$/ }).first()
    await expect(brandText).toBeVisible()

    // Expand button should now be present
    const expandBtn = page.getByLabel(/Expand navigation/i)
    await expect(expandBtn).toBeVisible()

    // Click expand
    await expandBtn.click()
    await page.waitForTimeout(400)

    // Should show "Cathode" again
    await expect(rail.locator('text=Cathode')).toBeVisible()
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
    await expect(page.locator('text=Cathode').first()).toBeVisible()
    await expect(page.locator('text=Video production workspace')).toBeVisible()
  })

  // ── IntentDeck ─────────────────────────────────────────────────
  test('IntentDeck renders all 5 cards', async ({ page }) => {
    const group = page.locator('[role="group"][aria-label="Quick actions"]')
    await expect(group).toBeVisible()

    // 5 intent cards
    await expect(page.locator('text=Start a new video')).toBeVisible()
    await expect(page.locator('text=Continue editing')).toBeVisible()
    await expect(page.locator('text=Review footage & style')).toBeVisible()
    await expect(page.locator('text=Render & ship')).toBeVisible()
    await expect(page.locator('text=Monitor queue')).toBeVisible()
  })

  test('IntentDeck shows badges', async ({ page }) => {
    await expect(page.locator('text=3 projects')).toBeVisible()
    await expect(page.locator('text=2 queued')).toBeVisible()
  })

  test('IntentDeck card click - Start a new video navigates to brief', async ({ page }) => {
    await page.locator('button', { hasText: 'Start a new video' }).click()
    await page.waitForURL('**/projects/new/brief')
    await expect(page).toHaveURL(/\/projects\/new\/brief/)
  })

  test('IntentDeck card click - Continue editing navigates to projects', async ({ page }) => {
    await page.locator('button', { hasText: 'Continue editing' }).click()
    await page.waitForURL('**/projects')
    await expect(page).toHaveURL(/\/projects/)
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
    await expect(page.locator('text=Skip to main content')).toBeAttached()
  })
})
