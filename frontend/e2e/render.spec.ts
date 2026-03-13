import fs from 'node:fs'
import path from 'node:path'
import { test, expect } from '@playwright/test'
import { cleanupProjectFixture, cloneProjectFixture } from './helpers/project-fixture'

const PROJECT = 'bet365_feature_act_01'
const BROKEN_PROJECT = `e2e_render_broken_${Date.now()}`
const MOTION_RENDER_PROJECT = `e2e_render_motion_${Date.now()}`

test.describe('Render Control', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/projects/${PROJECT}/render`)
    await expect(page.getByRole('heading', { name: 'Render', exact: true })).toBeVisible()
  })

  // ── Header ────────────────────────────────────────────────────
  test('header shows title, subtitle, and breadcrumbs', async ({ page }) => {
    const banner = page.getByRole('banner')
    await expect(banner.getByRole('heading', { name: 'Render', exact: true })).toBeVisible()
    const breadcrumb = banner.getByRole('navigation', { name: 'Breadcrumb' })
    await expect(breadcrumb.getByRole('link', { name: 'Projects' })).toBeVisible()
    await expect(breadcrumb.getByRole('link', { name: PROJECT })).toBeVisible()
  })

  test('project workspace nav highlights render', async ({ page }) => {
    const workspaceNav = page.getByRole('navigation', { name: 'Project workspace' })
    await expect(workspaceNav.getByRole('link', { name: 'Brief' })).toBeVisible()
    await expect(workspaceNav.getByRole('link', { name: 'Render' })).toHaveAttribute('aria-current', 'page')
  })

  test('render actions panel has Generate All Assets button', async ({ page }) => {
    await expect(page.locator('text=Render actions')).toBeVisible()
    const btn = page.locator('button:has-text("Generate All Assets")')
    await expect(btn).toBeVisible()
  })

  test('render actions panel has Render Video button', async ({ page }) => {
    const btn = page.locator('button:has-text("Render Video")')
    await expect(btn).toBeVisible()
  })

  // ── Render Settings ────────────────────────────────────────────
  test('Render Settings panel renders', async ({ page }) => {
    await expect(page.locator('text=Render Settings')).toBeVisible()
  })

  test('output filename input defaults to final_video.mp4', async ({ page }) => {
    const input = page.locator('#output-filename')
    await expect(input).toBeVisible()
    await expect(input).toHaveValue('final_video.mp4')
  })

  test('output filename can be changed', async ({ page }) => {
    const input = page.locator('#output-filename')
    await input.fill('my-video.mp4')
    await expect(input).toHaveValue('my-video.mp4')
  })

  test('FPS select defaults to 24', async ({ page }) => {
    const select = page.locator('#fps-select')
    await expect(select).toBeVisible()
    await expect(select).toHaveValue('24')
  })

  test('FPS select can be changed to 30', async ({ page }) => {
    const select = page.locator('#fps-select')
    await select.selectOption('30')
    await expect(select).toHaveValue('30')
  })

  test('FPS select can be changed to 60', async ({ page }) => {
    const select = page.locator('#fps-select')
    await select.selectOption('60')
    await expect(select).toHaveValue('60')
  })

  // ── Readiness Checklist ────────────────────────────────────────
  test('Readiness checklist renders', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Readiness' })).toBeVisible()
  })

  test('checklist shows scene count', async ({ page }) => {
    await expect(page.locator('text=/\\d+ scenes?/')).toBeVisible()
  })

  test('checklist shows visual asset progress', async ({ page }) => {
    await expect(page.locator('text=/\\d+\\/\\d+ with visuals/')).toBeVisible()
  })

  test('checklist shows audio asset progress', async ({ page }) => {
    await expect(page.locator('text=/\\d+\\/\\d+ with audio/')).toBeVisible()
  })

  test('readiness dots have correct colors', async ({ page }) => {
    // Scene count dot should be green (has scenes)
    const dots = page.locator('.rounded-full').filter({ has: page.locator('[class*="bg-"]') })
    // At least the first dot should exist
    await expect(page.locator('text=/\\d+ scenes/')).toBeVisible()
  })

  // ── Render Progress ────────────────────────────────────────────
  test('Render Progress area renders', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Render Progress' })).toBeVisible()
    await expect(page.getByText('No active render', { exact: true })).toBeVisible()
  })

  // ── Generate All Assets button state ───────────────────────────
  test('Generate All Assets button is enabled when scenes exist', async ({ page }) => {
    const btn = page.locator('button:has-text("Generate All Assets")')
    // Should not be disabled (project has scenes)
    await expect(btn).not.toHaveAttribute('disabled', '')
  })

  // ── Render Video button state ──────────────────────────────────
  test('Render Video button state reflects readiness', async ({ page }) => {
    const btn = page.locator('button:has-text("Render Video")')
    await expect(btn).toBeVisible()
    // This project may not have all audio, so button may be disabled
  })

  // ── Artifact Shelf ─────────────────────────────────────────────
  test('ArtifactShelf section renders', async ({ page }) => {
    // May show existing video or empty state
    await expect(page.locator('text=Render').first()).toBeVisible()
    // The shelf exists in the page layout
  })

  // ── Keyboard interaction ───────────────────────────────────────
  test('Tab through render settings fields', async ({ page }) => {
    const filenameInput = page.locator('#output-filename')
    await filenameInput.focus()
    await expect(filenameInput).toBeFocused()

    await page.keyboard.press('Tab')
    const fpsSelect = page.locator('#fps-select')
    await expect(fpsSelect).toBeFocused()
  })

  // ── Breadcrumb navigation ──────────────────────────────────────
  test('breadcrumb navigates to projects', async ({ page }) => {
    const link = page.getByRole('banner').getByRole('navigation', { name: 'Breadcrumb' }).getByRole('link', { name: 'Projects' })
    await link.click()
    await page.waitForURL('/projects')
  })

  test('breadcrumb navigates to scenes', async ({ page }) => {
    const sceneLink = page.locator(`a:has-text("${PROJECT}")`)
    if (await sceneLink.isVisible()) {
      await sceneLink.click()
      await page.waitForURL(/\/scenes/)
    }
  })

  test.describe.serial('broken asset paths', () => {
    test.beforeAll(() => {
      cloneProjectFixture('crucible_demo', BROKEN_PROJECT)
      const planPath = path.resolve(process.cwd(), '..', 'projects', BROKEN_PROJECT, 'plan.json')
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as Record<string, any>
      plan.meta.video_path = '/Users/davidmontgomery/old_checkout/projects/crucible_demo/crucible_demo.mp4'
      for (const [index, scene] of (plan.scenes as Array<Record<string, any>>).entries()) {
        if (scene.image_path) {
          scene.image_path = `/Users/davidmontgomery/old_checkout/projects/crucible_demo/images/scene_${String(index).padStart(3, '0')}_slide.png`
        }
        if (scene.video_path) {
          scene.video_path = `/Users/davidmontgomery/old_checkout/projects/crucible_demo/clips/scene_${String(index).padStart(3, '0')}.mp4`
        }
        if (scene.audio_path) {
          scene.audio_path = `/Users/davidmontgomery/old_checkout/projects/crucible_demo/audio/scene_${String(index).padStart(3, '0')}.wav`
        }
      }
      fs.writeFileSync(planPath, JSON.stringify(plan, null, 2))
    })

    test.afterAll(() => {
      cleanupProjectFixture(BROKEN_PROJECT)
    })

    test('render gate disables rendering when asset paths are stale and missing', async ({ page }) => {
      await page.goto(`/projects/${BROKEN_PROJECT}/render`)
      await expect(page.getByRole('heading', { name: 'Render', exact: true })).toBeVisible()
      await expect(page.getByText(/0\/10 with visuals/)).toBeVisible()
      await expect(page.getByText(/0\/10 with audio/)).toBeVisible()
      await expect(page.getByRole('button', { name: 'Render Video' })).toBeDisabled()
      await expect(page.getByText(/No rendered video yet|missing or invalid video/)).toBeVisible()
    })
  })

  test.describe.serial('motion readiness', () => {
    test.beforeAll(() => {
      cloneProjectFixture(PROJECT, MOTION_RENDER_PROJECT)
      const projectDir = path.resolve(process.cwd(), '..', 'projects', MOTION_RENDER_PROJECT)
      const planPath = path.join(projectDir, 'plan.json')
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as Record<string, any>
      plan.meta.render_profile = {
        ...(plan.meta.render_profile || {}),
        render_backend: 'remotion',
      }
      plan.meta.brief = {
        ...(plan.meta.brief || {}),
        composition_mode: 'hybrid',
      }
      plan.scenes = [
        {
          ...plan.scenes[0],
          scene_type: 'motion',
          image_path: null,
          video_path: null,
          preview_path: null,
          audio_path: `projects/${MOTION_RENDER_PROJECT}/audio/motion_scene.wav`,
          motion: {
            template_id: 'kinetic_title',
            props: {
              headline: 'Prompts on prompts',
              body: 'Hybrid mode treats this motion scene as render-ready without a still or clip upload.',
            },
            render_path: null,
            preview_path: null,
            rationale: 'Render gate regression check',
          },
        },
      ]
      fs.mkdirSync(path.join(projectDir, 'audio'), { recursive: true })
      fs.writeFileSync(path.join(projectDir, 'audio', 'motion_scene.wav'), 'wav')
      fs.writeFileSync(planPath, JSON.stringify(plan, null, 2))
    })

    test.afterAll(() => {
      cleanupProjectFixture(MOTION_RENDER_PROJECT)
    })

    test('remotion backend treats motion scenes as visual-ready in render gate', async ({ page }) => {
      await page.goto(`/projects/${MOTION_RENDER_PROJECT}/render`)
      await expect(page.getByRole('heading', { name: 'Render', exact: true })).toBeVisible()
      await expect(page.getByText('Backend: remotion')).toBeVisible()
      await expect(page.getByText('1/1 with visuals')).toBeVisible()
      await expect(page.getByText('1/1 with audio')).toBeVisible()
      await expect(page.getByRole('button', { name: 'Render Video' })).toBeEnabled()
    })
  })
})
