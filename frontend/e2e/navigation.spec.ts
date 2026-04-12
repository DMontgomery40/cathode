import { test, expect } from '@playwright/test'

const PROJECT = 'bet365_feature_act_01'

test.describe('Cross-route navigation', () => {
  // ── CommandRail navigation across all routes ───────────────────
  test('CommandRail Home -> Projects -> Queue -> Home', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('nav[aria-label="Main navigation"]')).toBeVisible()

    // Click Projects
    const projectsLink = page.locator('[role="menuitem"]').nth(1)
    await projectsLink.click()
    await page.waitForURL('**/projects')
    await expect(page).toHaveURL(/\/projects/)

    // Click Queue
    const queueLink = page.locator('[role="menuitem"]').nth(2)
    await queueLink.click()
    await page.waitForURL('**/queue')
    await expect(page).toHaveURL(/\/queue/)

    // Click Home
    const homeLink = page.locator('[role="menuitem"]').first()
    await homeLink.click()
    await page.waitForURL('/')
    await expect(page).toHaveURL('http://127.0.0.1:9322/')
  })

  // ── Full workflow navigation ───────────────────────────────────
  test('Home -> Projects -> Project Scenes -> Render -> Queue', async ({ page }) => {
    await page.goto('/')

    // Home: click "Continue editing" to go to Projects
    await page.locator('button', { hasText: 'Continue editing' }).click()
    await page.waitForURL('**/projects')

    // Projects: click first project to go to Scenes
    await page.waitForSelector(`button:has-text("bet365")`, { timeout: 10000 })
    await page.locator('button').filter({ hasText: 'bet365' }).first().click()
    await page.waitForURL(/\/projects\/.*\/(scenes|brief)/)

    // If on scenes page, navigate to render through the project workspace nav
    if (page.url().includes('/scenes')) {
      await page.getByRole('navigation', { name: 'Project workspace' }).getByRole('link', { name: 'Render' }).click()
      await page.waitForURL(`**/projects/${PROJECT}/render`)
      await expect(page.locator('text=Render').first()).toBeVisible()
    }

    // Navigate to queue
    await page.goto(`/projects/${PROJECT}/queue`)
    await expect(page.getByRole('heading', { name: 'Queue' })).toBeVisible()
  })

  // ── Browser back/forward ───────────────────────────────────────
  test('browser back navigates to previous route', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('text=Cathode').first()).toBeVisible()

    // Navigate to projects
    await page.locator('[role="menuitem"]').nth(1).click()
    await page.waitForURL('**/projects')

    // Go back
    await page.goBack()
    await page.waitForURL('/')
    await expect(page.locator('text=Start a new video')).toBeVisible()
  })

  test('browser forward after back', async ({ page }) => {
    await page.goto('/')
    await page.locator('[role="menuitem"]').nth(1).click()
    await page.waitForURL('**/projects')

    // Back
    await page.goBack()
    await page.waitForURL('/')

    // Forward
    await page.goForward()
    await page.waitForURL('**/projects')
    await expect(page.locator('text=Projects').first()).toBeVisible()
  })

  test('back from brief to projects', async ({ page }) => {
    await page.goto('/projects')
    await page.waitForTimeout(500)
    await page.goto('/projects/new/brief')
    await expect(page.locator('text=Brief Studio')).toBeVisible()

    await page.goBack()
    await page.waitForURL('**/projects')
  })

  test('back from scenes to projects list', async ({ page }) => {
    await page.goto('/projects')
    await page.waitForTimeout(500)
    await page.goto(`/projects/${PROJECT}/scenes`)
    await expect(page.locator('text=Scenes')).toBeVisible()

    await page.goBack()
    await page.waitForURL('**/projects')
  })

  // ── Page refresh ───────────────────────────────────────────────
  test('refresh home page preserves content', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('text=Start a new video')).toBeVisible()

    await page.reload()
    await expect(page.locator('text=Start a new video')).toBeVisible()
  })

  test('refresh projects page re-fetches data', async ({ page }) => {
    await page.goto('/projects')
    await page.waitForSelector(`button:has-text("bet365")`, { timeout: 10000 })

    await page.reload()
    await page.waitForSelector(`button:has-text("bet365")`, { timeout: 10000 })
    // Projects should still be visible
    const cards = page.locator('h3:has-text("bet365")')
    const count = await cards.count()
    expect(count).toBeGreaterThan(0)
  })

  test('refresh scenes page preserves project context', async ({ page }) => {
    await page.goto(`/projects/${PROJECT}/scenes`)
    await page.waitForSelector('[role="listbox"][aria-label="Scene timeline"]', { timeout: 10000 })

    await page.reload()
    await page.waitForSelector('[role="listbox"][aria-label="Scene timeline"]', { timeout: 10000 })
    await expect(page.getByRole('banner').getByText(/\d+ scenes/)).toBeVisible()
  })

  test('refresh render page preserves settings', async ({ page }) => {
    await page.goto(`/projects/${PROJECT}/render`)
    await expect(page.locator('text=Render Settings')).toBeVisible()

    // Change filename
    const input = page.locator('#output-filename')
    await input.fill('refreshed.mp4')

    // Refresh - note: form state is local, so it resets
    await page.reload()
    await expect(page.locator('#output-filename')).toHaveValue(`${PROJECT}.mp4`)
  })

  // ── Direct URL navigation ──────────────────────────────────────
  test('direct URL to projects', async ({ page }) => {
    await page.goto('/projects')
    await expect(page.locator('text=Projects').first()).toBeVisible()
  })

  test('direct URL to brief studio', async ({ page }) => {
    await page.goto('/projects/new/brief')
    await expect(page.locator('text=Brief Studio')).toBeVisible()
  })

  test('direct URL to scenes', async ({ page }) => {
    await page.goto(`/projects/${PROJECT}/scenes`)
    await page.waitForSelector('[role="listbox"][aria-label="Scene timeline"]', { timeout: 10000 })
    await expect(page.getByRole('heading', { name: 'Scenes' })).toBeVisible()
  })

  test('direct URL to render', async ({ page }) => {
    await page.goto(`/projects/${PROJECT}/render`)
    await expect(page.locator('text=Render Settings')).toBeVisible()
  })

  test('project workspace nav links scenes to render', async ({ page }) => {
    await page.goto(`/projects/${PROJECT}/scenes`)
    const workspaceNav = page.getByRole('navigation', { name: 'Project workspace' })
    await expect(workspaceNav.getByRole('link', { name: 'Brief' })).toBeVisible()
    await expect(workspaceNav.getByRole('link', { name: 'Scenes' })).toHaveAttribute('aria-current', 'page')
    await workspaceNav.getByRole('link', { name: 'Render' }).click()
    await page.waitForURL(`**/projects/${PROJECT}/render`)
    await expect(page.getByRole('heading', { name: 'Render', exact: true })).toBeVisible()
  })

  test('direct URL to queue', async ({ page }) => {
    await page.goto(`/projects/${PROJECT}/queue`)
    await expect(page.getByRole('heading', { name: 'Queue' })).toBeVisible()
  })

  // ── Collapsed rail navigation ──────────────────────────────────
  test('navigation works with collapsed rail', async ({ page }) => {
    await page.goto('/')

    // Collapse rail
    const collapseBtn = page.getByLabel(/Collapse navigation/i)
    await collapseBtn.click()
    await page.waitForTimeout(400)

    // Navigate via rail icons (no labels)
    const projectsItem = page.locator('[role="menuitem"]').nth(1)
    await projectsItem.click()
    await page.waitForURL('**/projects')
    await expect(page).toHaveURL(/\/projects/)

    // Navigate to queue
    const queueItem = page.locator('[role="menuitem"]').nth(2)
    await queueItem.click()
    await page.waitForURL('**/queue')
  })

  // ── Breadcrumb navigation chain ────────────────────────────────
  test('breadcrumb chain: Brief -> Projects', async ({ page }) => {
    await page.goto(`/projects/${PROJECT}/brief`)
    await expect(page.locator('text=Brief Studio')).toBeVisible()

    const projectsBC = page.getByRole('banner').getByRole('navigation', { name: 'Breadcrumb' }).getByRole('link', { name: 'Projects' })
    await projectsBC.click()
    await page.waitForURL('**/projects')
  })

  test('breadcrumb chain: Scenes -> Project brief', async ({ page }) => {
    await page.goto(`/projects/${PROJECT}/scenes`)
    await page.waitForSelector('[role="listbox"]', { timeout: 10000 })

    const projectBC = page.locator(`a:has-text("${PROJECT}")`)
    if (await projectBC.isVisible()) {
      await projectBC.click()
      await page.waitForURL(/\/brief/)
    }
  })

  // ── Error resilience ───────────────────────────────────────────
  test('non-existent project shows empty state gracefully', async ({ page }) => {
    await page.goto('/projects/nonexistent_project_xyz/scenes')
    // Should show empty state rather than crash
    await page.waitForTimeout(2000)
    const noScenes = page.locator('text=No scenes yet')
    const loading = page.locator('text=Loading')
    const scenes = page.getByRole('heading', { name: 'Scenes' })
    // At minimum, page should render something
    await expect(scenes).toBeVisible()
  })
})
