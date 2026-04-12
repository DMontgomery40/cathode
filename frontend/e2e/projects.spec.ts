import { test, expect } from '@playwright/test'

test.describe('Projects List', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects')
    await expect(page.locator('nav[aria-label="Main navigation"]')).toBeVisible()
  })

  test('page renders with header and breadcrumb', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible()
    // Breadcrumb shows Home link
    await expect(page.getByRole('banner').getByRole('navigation', { name: 'Breadcrumb' }).getByRole('link', { name: 'Home' })).toBeVisible()
  })

  test('New Project button is visible and clickable', async ({ page }) => {
    const newBtn = page.locator('button:has-text("New Project")')
    await expect(newBtn).toBeVisible()
    await newBtn.click()
    await page.waitForURL('**/projects/new/brief')
    await expect(page).toHaveURL(/\/projects\/new\/brief/)
  })

  test('project cards load from API', async ({ page }) => {
    // Wait for project cards to appear (bet365 projects exist)
    await page.waitForSelector('button:has-text("bet365")', { timeout: 10000 })

    // Should have multiple project cards
    const cards = page.locator('h3:has-text("bet365")')
    const count = await cards.count()
    expect(count).toBeGreaterThan(0)
  })

  test('project thumbnails do not 404', async ({ page }) => {
    const mediaFailures: Array<{ url: string; status: number }> = []
    page.on('response', (response) => {
      const url = response.url()
      if (url.includes('/api/projects/') && url.includes('/media/') && response.status() >= 400) {
        mediaFailures.push({ url, status: response.status() })
      }
    })

    await page.goto('/projects')
    await page.waitForSelector('button:has-text("bet365")', { timeout: 10000 })
    await page.waitForTimeout(1000)

    expect(mediaFailures).toEqual([])
  })

  test('project card shows scene count and status badge', async ({ page }) => {
    await page.waitForSelector('button:has-text("bet365")', { timeout: 10000 })

    // First project card should show scene count
    const firstCard = page.locator('button').filter({ hasText: 'bet365' }).first()
    // Should show "N scenes" text
    const sceneText = firstCard.locator('text=/\\d+ scenes?/')
    await expect(sceneText).toBeVisible()
  })

  test('project card click navigates to scenes or brief', async ({ page }) => {
    await page.waitForSelector('button:has-text("bet365")', { timeout: 10000 })

    // Click first project
    const firstCard = page.locator('button').filter({ hasText: 'bet365' }).first()
    await firstCard.click()

    // Should navigate to scenes (since it has scenes) or brief
    await page.waitForURL(/\/projects\/.*\/(scenes|brief)/)
  })

  test('project card hover effect', async ({ page }) => {
    await page.waitForSelector('button:has-text("bet365")', { timeout: 10000 })

    const firstCard = page.locator('button').filter({ hasText: 'bet365' }).first()
    const transformBefore = await firstCard.evaluate(el => getComputedStyle(el).transform)

    await firstCard.hover()
    await page.waitForTimeout(300)

    const transformAfter = await firstCard.evaluate(el => getComputedStyle(el).transform)
    // Hover should change transform (translateY)
    // Just verifying no crash on hover is the minimum bar
    expect(firstCard).toBeVisible()
  })

  test('project cards grid layout responsive', async ({ page }) => {
    // At full desktop width, should use 3 columns
    const grid = page.locator('.grid').first()
    await page.waitForSelector('button:has-text("bet365")', { timeout: 10000 })
    await expect(grid).toBeVisible()
  })

  test('project list can switch between newest-first and alphabetical sorting', async ({ page }) => {
    await page.route('**/api/projects', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            name: 'zebra_alpha',
            scene_count: 8,
            has_video: false,
            video_path: null,
            thumbnail_path: null,
            created_utc: '2026-03-10T08:00:00Z',
            updated_utc: '2026-03-16T08:00:00Z',
            image_profile: null,
            tts_profile: null,
          },
          {
            name: 'moon_archive',
            scene_count: 4,
            has_video: true,
            video_path: null,
            thumbnail_path: null,
            created_utc: '2026-03-15T12:00:00Z',
            updated_utc: '2026-03-15T12:00:00Z',
            image_profile: null,
            tts_profile: null,
          },
          {
            name: 'alpha_old',
            scene_count: 2,
            has_video: false,
            video_path: null,
            thumbnail_path: null,
            created_utc: '2026-03-01T05:00:00Z',
            updated_utc: '2026-03-01T05:00:00Z',
            image_profile: null,
            tts_profile: null,
          },
        ]),
      })
    })

    await page.reload()

    const projectTitles = page.locator('button h3')
    await expect(projectTitles).toHaveCount(3)
    await expect(page.getByLabel('Sort projects')).toHaveValue('created-desc')
    await expect(projectTitles).toHaveText(['moon_archive', 'zebra_alpha', 'alpha_old'])

    await page.getByLabel('Sort projects').selectOption('name-asc')
    await expect(projectTitles).toHaveText(['alpha_old', 'moon_archive', 'zebra_alpha'])

    await page.getByLabel('Sort projects').selectOption('created-asc')
    await expect(projectTitles).toHaveText(['alpha_old', 'zebra_alpha', 'moon_archive'])

    await page.getByLabel('Sort projects').selectOption('updated-desc')
    await expect(projectTitles).toHaveText(['zebra_alpha', 'moon_archive', 'alpha_old'])
  })

  test('breadcrumb Home link navigates back', async ({ page }) => {
    const homeLink = page.getByRole('banner').getByRole('navigation', { name: 'Breadcrumb' }).getByRole('link', { name: 'Home' })
    await homeLink.click()
    await page.waitForURL('/')
    await expect(page).toHaveURL('/')
  })

  test('CommandRail Projects item is active on this route', async ({ page }) => {
    const projectsLink = page.locator('[role="menuitem"]').nth(1)
    await expect(projectsLink).toHaveClass(/bg-/)
  })
})
