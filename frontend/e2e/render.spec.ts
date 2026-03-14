import fs from 'node:fs'
import path from 'node:path'
import { test, expect } from '@playwright/test'
import { cleanupProjectFixture, cloneProjectFixture, readProjectPlan } from './helpers/project-fixture'

const PROJECT = 'bet365_feature_act_01'
const BROKEN_PROJECT = `e2e_render_broken_${Date.now()}`
const MOTION_RENDER_PROJECT = `e2e_render_motion_${Date.now()}`
const ROUTE_RESET_PROJECT = `e2e_render_route_reset_${Date.now()}`
const TEXT_MODE_PROJECT = `e2e_render_text_mode_${Date.now()}`

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
    const sceneLabel = page.getByText(/\d+ scenes?/)
    const sceneDot = sceneLabel.locator('xpath=preceding-sibling::span[1]')
    const visualLabel = page.getByText(/\d+\/\d+ with visuals/)
    const visualDot = visualLabel.locator('xpath=preceding-sibling::span[1]')
    const backendLabel = page.getByText(/Backend: (ffmpeg|remotion)/)
    const backendDot = backendLabel.locator('xpath=preceding-sibling::span[1]')
    const audioLabel = page.getByText(/\d+\/\d+ with audio/)
    const audioDot = audioLabel.locator('xpath=preceding-sibling::span[1]')

    await expect(sceneDot).toHaveClass(/bg-\[var\(--signal-success\)\]/)

    const visualText = await visualLabel.innerText()
    const [, visualReady, visualTotal] = visualText.match(/(\d+)\/(\d+)/) ?? []
    await expect(visualDot).toHaveClass(
      Number(visualReady) === Number(visualTotal) && Number(visualTotal) > 0
        ? /bg-\[var\(--signal-success\)\]/
        : /bg-\[var\(--text-tertiary\)\]/,
    )

    const backendText = await backendLabel.innerText()
    await expect(backendDot).toHaveClass(
      backendText.includes('remotion')
        ? /bg-\[var\(--accent-primary\)\]/
        : /bg-\[var\(--text-tertiary\)\]/,
    )

    const audioText = await audioLabel.innerText()
    const [, audioReady, audioTotal] = audioText.match(/(\d+)\/(\d+)/) ?? []
    await expect(audioDot).toHaveClass(
      Number(audioReady) === Number(audioTotal) && Number(audioTotal) > 0
        ? /bg-\[var\(--signal-success\)\]/
        : /bg-\[var\(--text-tertiary\)\]/,
    )
  })

  // ── Render Progress ────────────────────────────────────────────
  test('Render Progress area renders', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Render Progress' })).toBeVisible()
    await expect(page.getByText('No active render', { exact: true })).toBeVisible()
  })

  test('render progress shows live job detail and log tail in the GUI', async ({ page }) => {
    await page.route(`**/api/projects/${PROJECT}/jobs`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            job_id: 'render-job-1',
            project_name: PROJECT,
            project_dir: `/tmp/${PROJECT}`,
            requested_stage: 'render',
            current_stage: 'render',
            status: 'running',
            progress: 0.42,
            progress_label: 'Encoding video',
            progress_detail: 'rendered 120 frames, encoded 98',
            request: { kind: 'rerun_stage', stage: 'render' },
            result: {},
            error: null,
          },
        ]),
      })
    })

    await page.route(`**/api/projects/${PROJECT}/jobs/render-job-1/log?tail_lines=160`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'render-job-1',
          project_name: PROJECT,
          log_path: `/tmp/${PROJECT}/render-job-1.log`,
          tail_lines: 160,
          line_count: 3,
          content: '{"type":"status","label":"Starting Remotion render","detail":"codec=h264 hwaccel=required"}\n{"type":"progress","stage":"encoding","progress":0.42}',
        }),
      })
    })

    await page.goto(`/projects/${PROJECT}/render`)
    await expect(page.getByText('Encoding video', { exact: true })).toBeVisible()
    await expect(page.getByText('rendered 120 frames, encoded 98', { exact: true })).toBeVisible()
    await expect(page.getByText('Live log tail', { exact: true })).toBeVisible()
    await expect(page.getByText('hwaccel=required')).toBeVisible()
  })

  test('software demo overlay manifests keep the media layer and do not duplicate the headline chip', async ({ page }) => {
    const overlayImage = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="1664" height="928" viewBox="0 0 1664 928"><rect width="1664" height="928" fill="#172033"/><rect x="120" y="120" width="1424" height="688" rx="32" fill="#23314f"/><rect x="220" y="220" width="360" height="220" rx="24" fill="#f4d8a0"/><rect x="620" y="220" width="540" height="40" rx="20" fill="#a9c0ff"/><rect x="620" y="290" width="420" height="32" rx="16" fill="#dce6ff"/><rect x="620" y="346" width="480" height="32" rx="16" fill="#dce6ff"/><rect x="220" y="476" width="1160" height="180" rx="28" fill="#2c3e61"/></svg>',
    )}`

    await page.route(`**/api/projects/${PROJECT}/remotion-manifest`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          width: 1664,
          height: 928,
          fps: 24,
          textRenderMode: 'deterministic_overlay',
          totalDurationInFrames: 120,
          scenes: [
            {
              uid: 'overlay-scene',
              sceneType: 'image',
              title: 'Real Estate Demo - The Listing',
              narration: 'Welcome to four twenty-two Maple Ridge Drive.',
              onScreenText: ['422 Maple Ridge Drive', 'Top-rated school district · 3 BR · 2.5 BA'],
              durationInFrames: 120,
              sequenceDurationInFrames: 120,
              imageUrl: overlayImage,
              textLayerKind: 'software_demo_focus',
              composition: {
                family: 'software_demo_focus',
                mode: 'native',
                props: {
                  headline: '422 Maple Ridge Drive',
                },
                transitionAfter: null,
                data: {},
                rationale: '',
              },
            },
          ],
        }),
      })
    })

    await page.goto(`/projects/${PROJECT}/render`)
    const player = page.getByTestId('remotion-player-surface')
    await expect(player).toBeVisible()
    await expect(player.locator('img').first()).toBeVisible()
    await expect(player.getByText('422 Maple Ridge Drive', { exact: true })).toHaveCount(1)
    await expect(player.getByText('Top-rated school district · 3 BR · 2.5 BA', { exact: true })).toBeVisible()
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
    const visualText = await page.getByText(/\d+\/\d+ with visuals/).innerText()
    const audioText = await page.getByText(/\d+\/\d+ with audio/).innerText()
    const [, visualReady, visualTotal] = visualText.match(/(\d+)\/(\d+)/) ?? []
    const [, audioReady, audioTotal] = audioText.match(/(\d+)\/(\d+)/) ?? []
    const shouldBeEnabled = (
      Number(visualTotal) > 0
      && Number(visualReady) === Number(visualTotal)
      && Number(audioReady) === Number(audioTotal)
    )

    if (shouldBeEnabled) {
      await expect(btn).toBeEnabled()
    } else {
      await expect(btn).toBeDisabled()
    }
  })

  // ── Artifact Shelf ─────────────────────────────────────────────
  test('ArtifactShelf section renders', async ({ page }) => {
    const emptyState = page.getByText(/No rendered video yet|missing or invalid video/)
    const shelfVideo = page.locator('video').first()
    if (await emptyState.count()) {
      await expect(emptyState.first()).toBeVisible()
    } else {
      await expect(shelfVideo).toBeVisible()
    }
  })

  // ── Keyboard interaction ───────────────────────────────────────
  test('Tab through render settings fields', async ({ page }) => {
    await expect(page.getByText(/Backend: (ffmpeg|remotion)/)).toBeVisible()
    const filenameInput = page.locator('#output-filename')
    await filenameInput.focus()
    await expect(filenameInput).toBeFocused()

    await page.keyboard.press('Tab')
    const fpsSelect = page.locator('#fps-select')
    await expect(fpsSelect).toBeFocused()

    await page.keyboard.press('Tab')
    const textModeSelect = page.locator('#text-render-mode-select')
    await expect(textModeSelect).toBeFocused()
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

  test.describe.serial('same-session project transitions', () => {
    test.beforeAll(() => {
      cloneProjectFixture(PROJECT, ROUTE_RESET_PROJECT)
      const projectDir = path.resolve(process.cwd(), '..', 'projects', ROUTE_RESET_PROJECT)
      const planPath = path.join(projectDir, 'plan.json')
      const renderDir = path.join(projectDir, 'renders')
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as Record<string, unknown>
      plan.meta.render_profile = {
        ...(plan.meta.render_profile || {}),
        fps: 30,
      }
      plan.meta.video_path = `projects/${ROUTE_RESET_PROJECT}/renders/route-reset.mp4`
      fs.mkdirSync(renderDir, { recursive: true })
      fs.writeFileSync(path.join(renderDir, 'route-reset.mp4'), 'mp4')
      fs.writeFileSync(planPath, JSON.stringify(plan, null, 2))
    })

    test.afterAll(() => {
      cleanupProjectFixture(ROUTE_RESET_PROJECT)
    })

    test('route changes reset render settings to the destination project defaults', async ({ page }) => {
      await page.goto(`/projects/${PROJECT}/render`)
      await page.getByRole('heading', { name: 'Render', exact: true }).waitFor()

      await page.locator('#output-filename').fill('carryover.mp4')
      await page.locator('#fps-select').selectOption('60')

      await page.evaluate((targetPath) => {
        window.history.pushState({}, '', targetPath)
        window.dispatchEvent(new PopStateEvent('popstate', { state: window.history.state }))
      }, `/projects/${ROUTE_RESET_PROJECT}/render`)

      await expect(page.getByRole('banner').getByRole('link', { name: ROUTE_RESET_PROJECT })).toBeVisible()
      await expect(page.locator('#output-filename')).toHaveValue('route-reset.mp4')
      await expect(page.locator('#fps-select')).toHaveValue('30')
    })
  })

  test.describe.serial('text strategy settings', () => {
    test.beforeAll(() => {
      cloneProjectFixture(PROJECT, TEXT_MODE_PROJECT)
      const projectDir = path.resolve(process.cwd(), '..', 'projects', TEXT_MODE_PROJECT)
      const planPath = path.join(projectDir, 'plan.json')
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as Record<string, any>
      plan.meta.brief = {
        ...(plan.meta.brief || {}),
        composition_mode: 'hybrid',
        text_render_mode: 'visual_authored',
      }
      plan.meta.render_profile = {
        ...(plan.meta.render_profile || {}),
        render_backend: 'remotion',
        text_render_mode: 'visual_authored',
      }
      fs.writeFileSync(planPath, JSON.stringify(plan, null, 2))
    })

    test.afterAll(() => {
      cleanupProjectFixture(TEXT_MODE_PROJECT)
    })

    test('render settings persist text strategy into the project plan', async ({ page }) => {
      await page.goto(`/projects/${TEXT_MODE_PROJECT}/render`)
      await expect(page.getByRole('heading', { name: 'Render', exact: true })).toBeVisible()
      await expect(page.getByText('Backend: remotion')).toBeVisible()
      await expect(page.locator('#text-render-mode-select')).toBeEnabled()
      await expect(page.locator('#text-render-mode-select')).toHaveValue('visual_authored')

      await page.locator('#text-render-mode-select').selectOption('deterministic_overlay')
      await expect(page.locator('#text-render-mode-select')).toHaveValue('deterministic_overlay')

      await expect.poll(() => {
        const plan = readProjectPlan(TEXT_MODE_PROJECT) as Record<string, any>
        return `${plan.meta?.brief?.text_render_mode ?? ''}|${plan.meta?.render_profile?.text_render_mode ?? ''}`
      }).toBe('deterministic_overlay|deterministic_overlay')

      await page.reload()
      await expect(page.locator('#text-render-mode-select')).toHaveValue('deterministic_overlay')
    })
  })

  test.describe.serial('broken asset paths', () => {
    test.beforeAll(() => {
      cloneProjectFixture('crucible_demo', BROKEN_PROJECT)
      const planPath = path.resolve(process.cwd(), '..', 'projects', BROKEN_PROJECT, 'plan.json')
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as Record<string, unknown>
      plan.meta.video_path = '/Users/davidmontgomery/old_checkout/projects/crucible_demo/crucible_demo.mp4'
      for (const [index, scene] of (plan.scenes as Array<Record<string, unknown>>).entries()) {
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
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as Record<string, unknown>
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
      await expect(page.getByTestId('remotion-player-surface')).toBeVisible()
    })
  })
})
