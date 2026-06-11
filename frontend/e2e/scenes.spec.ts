import { test, expect, type Page } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

import { cleanupProjectFixture, cloneProjectFixture, readProjectPlan } from './helpers/project-fixture'

const PROJECT = 'bet365_feature_act_01'
const DISPOSABLE_PROJECT = `e2e_scene_mutation_${Date.now()}`
const MOTION_PROJECT = `e2e_motion_scene_${Date.now()}`
const MANUAL_IMAGE_PROJECT = `e2e_manual_image_${Date.now()}`
const SWITCH_PROJECT = `e2e_scene_switch_${Date.now()}`
const ONE_PIXEL_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=',
  'base64',
)

type MutablePlan = Record<string, unknown> & {
  meta: Record<string, unknown> & {
    brief?: Record<string, unknown>
    render_profile?: Record<string, unknown>
    image_profile?: Record<string, unknown>
    video_profile?: Record<string, unknown>
  }
  scenes: Array<Record<string, unknown>>
}

function writeProjectImage(project: string, filename: string) {
  const imageDir = path.resolve(process.cwd(), '..', 'projects', project, 'images')
  fs.mkdirSync(imageDir, { recursive: true })
  fs.writeFileSync(path.join(imageDir, filename), ONE_PIXEL_PNG)
}

async function selectInspectorOption(page: Page, label: string, value: string, optionName: string) {
  const control = page.getByLabel(label)
  if (await control.evaluate((element) => element instanceof HTMLSelectElement)) {
    await control.selectOption(value)
    return
  }
  await control.click()
  await page.getByRole('listbox', { name: label }).getByRole('option', { name: optionName }).click()
}

async function expectInspectorOption(page: Page, label: string, value: string, optionName: string) {
  const control = page.getByLabel(label)
  if (await control.evaluate((element) => element instanceof HTMLSelectElement || element instanceof HTMLInputElement)) {
    await expect(control).toHaveValue(value)
    return
  }
  await expect(control).toContainText(optionName)
}

async function inspectorOptionLabels(page: Page, label: string): Promise<string[]> {
  const control = page.getByLabel(label)
  if (await control.evaluate((element) => element instanceof HTMLSelectElement)) {
    return control.locator('option').evaluateAll((options) => (
      options.map((option) => (option as HTMLOptionElement).textContent?.trim() ?? '')
    ))
  }
  await control.click()
  const labels = await page.getByRole('listbox', { name: label }).getByRole('option').allTextContents()
  await page.keyboard.press('Escape')
  return labels.map((labelText) => labelText.trim())
}

test.describe('Scene Timeline', () => {
  function setNarrowInspectorLayout() {
    window.localStorage.setItem('bettube-studio-ui', JSON.stringify({
      state: {
        railCollapsed: false,
        railWidth: 240,
        sceneTimelineHeight: 144,
        sceneInspectorWidth: 320,
        sceneInspectorCollapsed: false,
      },
      version: 0,
    }))
  }

  test.describe('read-only sample project', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto(`/projects/${PROJECT}/scenes`)
      await expect(page.getByRole('listbox', { name: 'Scene timeline' })).toBeVisible()
      await expect(page.getByRole('region', { name: 'Scene inspector' })).toBeVisible()
      await expect(page.getByRole('region', { name: 'Media stage' })).toBeVisible()
    })

    test('renders the real sample project without mutating it', async ({ page }) => {
      const options = page.getByRole('listbox', { name: 'Scene timeline' }).getByRole('option')
      const inspector = page.getByRole('region', { name: 'Scene inspector' })
      await expect(options.first()).toBeVisible()
      await expect(page.getByLabel('Scene title')).toBeVisible()
      await expect(page.getByLabel('Narration text')).toBeVisible()
      await expect(page.getByLabel('Image direction')).toBeVisible()
      await expect(page.getByLabel('Composition family')).toBeVisible()
      await expect(page.getByLabel('Composition behavior')).toBeVisible()
      await expect(page.getByLabel('Transition after')).toBeVisible()
      await expect(page.getByRole('button', { name: 'Generate All Assets' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Render Video' })).toBeVisible()
      await expect(page.getByLabel('Image editor')).toBeVisible()
      await expect(inspector.getByRole('button', { name: 'Add Scene Before' })).toBeVisible()
      await expect(inspector.getByRole('button', { name: 'Add Scene After' })).toBeVisible()
      await expect(inspector.getByRole('button', { name: 'Delete Scene' })).toBeVisible()
    })

    test('project workspace nav keeps render reachable from scenes', async ({ page }) => {
      const workspaceNav = page.getByRole('navigation', { name: 'Project workspace' })
      await expect(workspaceNav.getByRole('link', { name: 'Scenes' })).toHaveAttribute('aria-current', 'page')
      await expect(workspaceNav.getByRole('link', { name: 'Render' })).toBeVisible()
    })

    test('compact timeline rail stays media-first instead of toolbar-first', async ({ page }) => {
      const metrics = await page.evaluate(() => {
        const strip = document.querySelector('.scene-timeline-strip')
        const head = document.querySelector('.scene-timeline-strip__head')
        const thumb = document.querySelector('.scene-timeline-card img')
        const actionButtons = Array.from(document.querySelectorAll('.scene-timeline-strip__actions .scene-workspace__floating-button'))
        const stripRect = strip?.getBoundingClientRect()
        const headRect = head?.getBoundingClientRect()
        const thumbRect = thumb?.getBoundingClientRect()
        return {
          stripHeight: stripRect?.height ?? 0,
          headHeight: headRect?.height ?? 0,
          thumbHeight: thumbRect?.height ?? 0,
          maxActionWidth: Math.max(0, ...actionButtons.map((element) => element.getBoundingClientRect().width)),
          maxActionHeight: Math.max(0, ...actionButtons.map((element) => element.getBoundingClientRect().height)),
        }
      })

      expect(metrics.thumbHeight).toBeGreaterThan(metrics.maxActionHeight * 2.4)
      expect(metrics.thumbHeight).toBeGreaterThan(metrics.maxActionWidth * 2.4)
      expect(metrics.headHeight).toBeLessThan(metrics.stripHeight * 0.3)
    })

    test('timeline expands into a full storyboard board without internal scrolling', async ({ page }) => {
      const boardProject = `e2e_timeline_board_${Date.now()}`
      cloneProjectFixture(PROJECT, boardProject)
      const planPath = path.resolve(process.cwd(), '..', 'projects', boardProject, 'plan.json')
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as MutablePlan
      plan.scenes = plan.scenes.slice(0, 4)
      fs.writeFileSync(planPath, JSON.stringify(plan, null, 2))

      await page.setViewportSize({ width: 1756, height: 1329 })
      await page.goto(`/projects/${boardProject}/scenes`)
      const resizeHandle = page.getByRole('separator', { name: 'Resize scene timeline' })

      await expect(resizeHandle).toHaveAttribute('aria-valuemax', '720')
      await resizeHandle.focus()
      await resizeHandle.press('End')
      await expect(resizeHandle).toHaveAttribute('aria-valuenow', '720')

      const metrics = await page.locator('.scene-timeline-strip__surface').evaluate((element) => ({
        layout: element.getAttribute('data-layout'),
        clientHeight: element.clientHeight,
        scrollHeight: element.scrollHeight,
        clientWidth: element.clientWidth,
        scrollWidth: element.scrollWidth,
      }))

      expect(metrics.layout).toBe('grid')
      expect(metrics.clientHeight).toBeGreaterThan(560)
      expect(metrics.scrollHeight).toBeLessThanOrEqual(metrics.clientHeight + 2)
      expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 2)

      cleanupProjectFixture(boardProject)
    })

    test('legacy motion metadata stays in media controls without explicit native opt-in', async ({ page }) => {
      const legacyMotionProject = `e2e_legacy_motion_default_${Date.now()}`
      cloneProjectFixture(PROJECT, legacyMotionProject)
      const planPath = path.resolve(process.cwd(), '..', 'projects', legacyMotionProject, 'plan.json')
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as MutablePlan
      const scene = plan.scenes[0]
      plan.meta = {
        ...(plan.meta || {}),
        composition_mode: 'classic',
        render_profile: {
          ...(plan.meta?.render_profile || {}),
          render_strategy: 'auto',
          render_backend: 'ffmpeg',
          render_backend_reason: 'Classic image/video assembly has no Remotion-only requirements.',
        },
      }
      scene.scene_type = 'motion'
      scene.image_path = null
      scene.motion = {
        template_id: 'bullet_stack',
        props: { headline: 'Legacy motion metadata', bullets: ['A', 'B'] },
        render_path: null,
        preview_path: null,
        rationale: 'Old stored native scene',
      }
      scene.composition = {
        family: 'bullet_stack',
        mode: 'native',
        manifestation: 'native_remotion',
        props: scene.motion.props,
        transition_after: null,
        data: {},
        render_path: null,
        preview_path: null,
        rationale: scene.motion.rationale,
      }
      fs.writeFileSync(planPath, JSON.stringify(plan, null, 2))

      try {
        await page.goto(`/projects/${legacyMotionProject}/scenes`)
        const timeline = page.getByRole('listbox', { name: 'Scene timeline' })
        const firstScene = timeline.getByRole('option').first()
        await expect(firstScene).toContainText('image')
        await expect(firstScene).not.toContainText('motion')
        await expect(page.getByRole('region', { name: 'Media stage' })).toContainText('Visual stage')
        await expect(page.getByRole('button', { name: 'Generate Motion Preview' })).toHaveCount(0)
        await expect(page.getByRole('button', { name: /Overlay Text/ })).toHaveCount(0)
        await expect(page.getByTestId('remotion-player-surface')).toHaveCount(0)
        await expectInspectorOption(page, 'Scene type', 'image', 'Image')

        const sceneTypeOptions = await inspectorOptionLabels(page, 'Scene type')
        const familyOptions = await inspectorOptionLabels(page, 'Composition family')
        const modeOptions = await inspectorOptionLabels(page, 'Composition behavior')

        expect(sceneTypeOptions).toEqual(['Image', 'Video'])
        expect(familyOptions).toEqual(['Static media', 'Media pan'])
        expect(modeOptions).toEqual(['None'])
      } finally {
        cleanupProjectFixture(legacyMotionProject)
      }
    })

    test('selecting another scene updates the inspector', async ({ page }) => {
      const titleInput = page.getByLabel('Scene title')
      const firstTitle = await titleInput.inputValue()

      const secondScene = page.getByRole('listbox', { name: 'Scene timeline' }).getByRole('option').nth(1)
      await secondScene.click()
      await expect(secondScene).toHaveAttribute('aria-selected', 'true')

      await expect(titleInput).not.toHaveValue(firstTitle)
    })

    test('selected scene media renders in the stage', async ({ page }) => {
      const stage = page.getByRole('region', { name: 'Media stage' })
      const image = stage.locator('img')
      const video = stage.locator('video')
      const hasImage = await image.count()
      const hasVideo = await video.count()

      expect(hasImage + hasVideo).toBeGreaterThan(0)
    })

    test('narrow inspector layout stays contained and scrollable', async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 720 })
      await page.evaluate(setNarrowInspectorLayout)
      await page.reload()
      const inspectorRegion = page.getByRole('region', { name: 'Scene inspector' })
      await expect(inspectorRegion).toBeVisible()
      await page.locator('button[aria-controls="scene-preview-content"]').click()

      const layout = await page.evaluate(() => {
        const inspector = document.querySelector('[aria-label="Scene inspector"]')
        if (!(inspector instanceof HTMLElement)) {
          return null
        }

        inspector.scrollTop = 0
        const inspectorRect = inspector.getBoundingClientRect()
        const visualContent = document.getElementById('scene-visual-content')
        const visualContentRect = visualContent?.getBoundingClientRect() ?? null
        const visualButtons = Array.from(document.querySelectorAll('button'))
          .filter((button) => ['Upload Image', 'Upload Video', 'Regenerate Image', 'Edit Image'].includes(button.textContent?.trim() ?? ''))
          .map((button) => button.getBoundingClientRect())
        const lowestVisualButtonBottom = visualButtons.reduce((max, rect) => Math.max(max, rect.bottom), 0)

        const offenders = Array.from(inspector.querySelectorAll('*'))
          .filter((element): element is HTMLElement => element instanceof HTMLElement)
          .map((element) => {
            const rect = element.getBoundingClientRect()
            return {
              tag: element.tagName,
              ariaLabel: element.getAttribute('aria-label'),
              text: (element.textContent ?? '').trim().replace(/\s+/g, ' ').slice(0, 80),
              left: rect.left,
              right: rect.right,
              width: rect.width,
            }
          })
          .filter((element) => element.width > 0)
          .filter((element) => element.left < inspectorRect.left - 1 || element.right > inspectorRect.right + 1)

        const beforeScrollTop = inspector.scrollTop
        inspector.scrollTop = inspector.scrollHeight

        return {
          inspectorScrollWidth: inspector.scrollWidth,
          inspectorClientWidth: inspector.clientWidth,
          inspectorClientHeight: inspector.clientHeight,
          inspectorScrollHeight: inspector.scrollHeight,
          inspectorScrollTop: inspector.scrollTop,
          offenders,
          visualContentBottom: visualContentRect?.bottom ?? null,
          lowestVisualButtonBottom,
          beforeScrollTop,
        }
      })

      expect(layout).not.toBeNull()
      expect(layout?.inspectorScrollWidth).toBeLessThanOrEqual((layout?.inspectorClientWidth ?? 0) + 1)
      expect(layout?.offenders).toEqual([])
      expect(layout?.visualContentBottom).not.toBeNull()
      expect(layout?.lowestVisualButtonBottom).toBeLessThanOrEqual((layout?.visualContentBottom ?? 0) + 1)
      expect(layout?.inspectorScrollHeight).toBeGreaterThan(layout?.inspectorClientHeight ?? 0)
      expect(layout?.inspectorScrollTop).toBeGreaterThan(layout?.beforeScrollTop ?? 0)
      await expect(inspectorRegion.getByRole('button', { name: 'Add Scene Before' })).toBeVisible()
      await expect(inspectorRegion.getByRole('button', { name: 'Add Scene After' })).toBeVisible()
      await expect(inspectorRegion.getByRole('button', { name: 'Delete Scene' })).toBeVisible()
      await expect(page.getByLabel('On-screen text 1')).toHaveCount(0)
      await expect(page.getByRole('button', { name: /Overlay Text/ })).toHaveCount(0)
      await expect(page.getByRole('button', { name: 'Generate Preview' })).toBeVisible()
    })

    test('small viewport compacts navigation and keeps scenes scrollable', async ({ page }) => {
      await page.setViewportSize({ width: 603, height: 720 })
      await page.evaluate(() => {
        window.localStorage.setItem('bettube-studio-ui', JSON.stringify({
          state: {
            railCollapsed: false,
            railWidth: 240,
            sceneTimelineHeight: 144,
            sceneInspectorWidth: 396,
            sceneInspectorCollapsed: false,
          },
          version: 0,
        }))
      })
      await page.reload()

      const nav = page.locator('nav[aria-label="Main navigation"]')
      const workspace = page.locator('.scene-workspace')
      await expect(nav).toBeVisible()
      await expect(workspace).toBeVisible()
      await expect(page.getByRole('button', { name: 'Navigation compacted for narrow window' })).toBeVisible()

      const mainWidth = await page.locator('main').evaluate((element) => element.getBoundingClientRect().width)
      const scrollMetrics = await workspace.evaluate((element) => {
        const beforeScrollTop = element.scrollTop
        element.scrollTop = element.scrollHeight
        return {
          workspaceScrollTop: element.scrollTop,
          beforeScrollTop,
          workspaceScrollHeight: element.scrollHeight,
          workspaceClientHeight: element.clientHeight,
        }
      })

      expect(mainWidth).toBeGreaterThanOrEqual(380)
      expect(scrollMetrics.workspaceScrollHeight).toBeGreaterThan(scrollMetrics.workspaceClientHeight)
      expect(scrollMetrics.workspaceScrollTop).toBeGreaterThan(scrollMetrics.beforeScrollTop)
      await expect(page.locator('button[aria-controls="scene-preview-content"]')).toBeVisible()
    })

    test('operator section shows generation summary without raw request JSON', async ({ page }) => {
      await page.locator('button[aria-controls="scene-operator-content"]').click()
      const operatorContent = page.locator('#scene-operator-content')
      await expect(operatorContent.getByText('Generate image', { exact: true })).toBeVisible()
      await expect(operatorContent.getByText('Image', { exact: true })).toBeVisible()
      await expect(operatorContent.getByText('Replicate / qwen/qwen-image-2512', { exact: true })).toBeVisible()
      await expect(operatorContent.getByText('Edit', { exact: true })).toBeVisible()
      await expect(operatorContent.getByText('qwen/qwen-image-edit-2511', { exact: true })).toBeVisible()
      await expect(operatorContent.getByText('"generate"')).toHaveCount(0)
      await expect(operatorContent.getByText('"provider": "replicate"')).toHaveCount(0)
    })

    test('scene upload buttons open real file choosers', async ({ page }) => {
      const [imageChooser] = await Promise.all([
        page.waitForEvent('filechooser'),
        page.getByRole('button', { name: 'Upload Image' }).click(),
      ])
      expect(imageChooser.isMultiple()).toBe(false)

      const [videoChooser] = await Promise.all([
        page.waitForEvent('filechooser'),
        page.getByRole('button', { name: 'Upload Video' }).click(),
      ])
      expect(videoChooser.isMultiple()).toBe(false)
    })

    test('generate all assets shows scene-by-scene progress under the action button', async ({ page }) => {
      await page.route(`**/api/projects/${PROJECT}/jobs`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              job_id: 'asset-job-1',
              project_name: PROJECT,
              project_dir: `/tmp/${PROJECT}`,
              requested_stage: 'assets',
              current_stage: 'assets',
              status: 'running',
              progress: 0.42,
              progress_kind: 'audio',
              progress_label: 'Generating audio',
              progress_detail: 'Scene 4 of 59 - Opening range',
              request: { kind: 'rerun_stage', stage: 'assets' },
              result: {},
              error: null,
            },
          ]),
        })
      })

      await page.goto(`/projects/${PROJECT}/scenes`)
      await expect(page.getByText('Generating audio', { exact: true })).toBeVisible()
      await expect(page.getByText('Scene 4 of 59 - Opening range', { exact: true })).toBeVisible()
      await expect(page.locator('[role="progressbar"]').first()).toHaveAttribute('aria-valuenow', '42')
    })

    test('job dock names the collapsed project job history', async ({ page }) => {
      await page.route(`**/api/projects/${PROJECT}/jobs`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              job_id: 'completed-job-1',
              project_name: PROJECT,
              project_dir: `/tmp/${PROJECT}`,
              requested_stage: 'render',
              current_stage: 'done',
              status: 'succeeded',
              request: { kind: 'render' },
              result: {},
              error: null,
            },
          ]),
        })
      })

      await page.reload()
      const dock = page.getByRole('region', { name: 'Project job history' })
      await expect(dock).toBeVisible()
      await expect(dock).toContainText('Project job history: 1 recent')
    })

    test('desktop inspector scrolls instead of clipping lower sections', async ({ page }) => {
      await page.setViewportSize({ width: 1756, height: 1329 })
      await page.reload()
      await page.locator('button[aria-controls="scene-preview-content"]').click()
      await page.locator('button[aria-controls="scene-operator-content"]').click()

      const inspectorMetrics = await page.locator('[aria-label="Scene inspector"]').evaluate((element) => {
        element.scrollTop = 0
        const beforeScrollTop = element.scrollTop
        element.scrollTop = element.scrollHeight
        return {
          clientHeight: element.clientHeight,
          scrollHeight: element.scrollHeight,
          scrollTop: element.scrollTop,
          beforeScrollTop,
        }
      })

      expect(inspectorMetrics.scrollHeight).toBeGreaterThan(inspectorMetrics.clientHeight)
      expect(inspectorMetrics.scrollTop).toBeGreaterThan(inspectorMetrics.beforeScrollTop)
      await expect(page.locator('#scene-operator-content')).toBeVisible()
    })
  })

  test.describe.serial('motion scene support', () => {
    test.beforeAll(() => {
      cloneProjectFixture(PROJECT, MOTION_PROJECT)
      const planPath = path.resolve(process.cwd(), '..', 'projects', MOTION_PROJECT, 'plan.json')
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as Record<string, unknown>
      plan.meta.render_profile = {
        ...(plan.meta.render_profile || {}),
        render_strategy: 'force_remotion',
        render_backend: 'remotion',
        render_backend_reason: 'Remotion forced by render_strategy=force_remotion.',
      }
      plan.meta.brief = {
        ...(plan.meta.brief || {}),
        composition_mode: 'motion_only',
      }
      const scene = plan.scenes[0]
      scene.scene_type = 'motion'
      scene.on_screen_text = []
      scene.image_path = null
      scene.video_path = null
      scene.preview_path = null
      scene.motion = {
        template_id: 'bullet_stack',
        props: {
          headline: 'Prompts on prompts',
          body: 'One hiring prompt becomes a whole orchestrated demo pipeline.',
          bullets: ['Job description', 'Storyboard', 'Agents', 'Final render'],
        },
        render_path: null,
        preview_path: null,
        rationale: 'Text-first proof beat',
      }
      scene.composition = {
        family: 'bullet_stack',
        mode: 'native',
        manifestation: 'native_remotion',
        props: scene.motion.props,
        transition_after: null,
        data: {},
        render_path: null,
        preview_path: null,
        rationale: scene.motion.rationale,
      }
      fs.writeFileSync(planPath, JSON.stringify(plan, null, 2))
    })

    test.afterAll(() => {
      cleanupProjectFixture(MOTION_PROJECT)
    })

    test('motion scenes expose template controls in the live workspace', async ({ page }) => {
      await page.goto(`/projects/${MOTION_PROJECT}/scenes`)
      await expect(page.getByRole('region', { name: 'Scene inspector' })).toBeVisible()
      await expectInspectorOption(page, 'Scene type', 'motion', 'Remotion')
      await expectInspectorOption(page, 'Composition family', 'bullet_stack', 'Bullet stack')
      await expect(page.getByRole('button', { name: 'Generate Motion Preview' })).toBeVisible()
      await expect(page.getByLabel('Motion headline')).toHaveValue('Prompts on prompts')
      await expect(page.getByTestId('remotion-player-surface')).toBeVisible()
      await expect(page.getByRole('button', { name: /Overlay Text/ })).toBeVisible()
      await expect(page.getByLabel('Overlay text 1')).toHaveCount(0)
    })
  })

  test.describe.serial('manual image mode', () => {
    test.beforeAll(() => {
      cloneProjectFixture(PROJECT, MANUAL_IMAGE_PROJECT)
      const planPath = path.resolve(process.cwd(), '..', 'projects', MANUAL_IMAGE_PROJECT, 'plan.json')
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as Record<string, unknown>
      plan.meta.image_profile = {
        ...(plan.meta.image_profile || {}),
        provider: 'manual',
      }
      plan.scenes[0].scene_type = 'image'
      plan.scenes[0].image_path = null
      fs.writeFileSync(planPath, JSON.stringify(plan, null, 2))
    })

    test.afterAll(() => {
      cleanupProjectFixture(MANUAL_IMAGE_PROJECT)
    })

    test('manual image mode disables generation and explains the upload-first path', async ({ page }) => {
      await page.goto(`/projects/${MANUAL_IMAGE_PROJECT}/scenes`)
      await expect(page.getByRole('region', { name: 'Scene inspector' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Generate Image' })).toBeDisabled()
      await expect(page.getByText('Manual image mode is upload-first.')).toBeVisible()
    })
  })

  test.describe.serial('cross-project scene selection recovery', () => {
    test.beforeAll(() => {
      cloneProjectFixture(PROJECT, SWITCH_PROJECT)
      const planPath = path.resolve(process.cwd(), '..', 'projects', SWITCH_PROJECT, 'plan.json')
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as {
        scenes: Array<Record<string, unknown>>
      }

      plan.scenes = plan.scenes.map((scene, index) => ({
        ...scene,
        uid: `switch_scene_${index + 1}`,
      }))

      fs.writeFileSync(planPath, `${JSON.stringify(plan, null, 2)}\n`, 'utf8')
    })

    test.afterAll(() => {
      cleanupProjectFixture(SWITCH_PROJECT)
    })

    test('switching projects in-app reselects a valid scene instead of dropping the inspector', async ({ page }) => {
      await page.goto(`/projects/${PROJECT}/scenes`)
      await expect(page.getByRole('region', { name: 'Scene inspector' })).toBeVisible()

      await page.getByRole('listbox', { name: 'Scene timeline' }).getByRole('option').nth(1).click()
      await expect(page.getByLabel('Scene title')).toBeVisible()

      await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('menuitem', { name: 'Projects' }).click()
      await expect(page).toHaveURL(/\/projects$/)

      await page.getByRole('button', { name: new RegExp(SWITCH_PROJECT) }).click()
      await expect(page).toHaveURL(new RegExp(`/projects/${SWITCH_PROJECT}/scenes$`))

      const inspector = page.getByRole('region', { name: 'Scene inspector' })
      await expect(inspector).toBeVisible()
      await expect(page.getByText('Select a scene to inspect')).toHaveCount(0)
      await expect(page.getByLabel('Scene title')).toBeVisible()
      await expect(inspector.getByRole('button', { name: 'Add Scene Before' })).toBeVisible()
    })
  })

  test.describe.serial('disposable mutation project', () => {
    test.beforeAll(() => {
      cloneProjectFixture(PROJECT, DISPOSABLE_PROJECT)
      const planPath = path.join(process.cwd(), '..', 'projects', DISPOSABLE_PROJECT, 'plan.json')
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as {
        meta: Record<string, unknown>
        scenes: Array<{ uid: string; title?: string }>
      }
      const firstScene = plan.scenes[0]
      const videoScene = plan.scenes[1]
      plan.meta = {
        ...plan.meta,
        video_profile: {
          provider: 'replicate',
          generation_model: '',
          model_selection_mode: 'automatic',
          quality_mode: 'standard',
          generate_audio: true,
        },
        image_action_history: [
          {
            action: 'edit',
            status: 'succeeded',
            scene_uid: firstScene.uid,
            scene_index: 1,
            scene_title: firstScene.title || 'Scene 1',
            request: {
              feedback: 'Increase contrast and clean the label',
              model: 'qwen/qwen-image-edit-2511',
            },
            result: {
              image_path: `projects/${DISPOSABLE_PROJECT}/images/image_${firstScene.uid}_edited.png`,
            },
            happened_at: '2026-03-12T20:25:00Z',
          },
        ],
      }
      Object.assign(videoScene, {
        scene_type: 'video',
        image_path: null,
        video_path: null,
        preview_path: null,
        video_scene_kind: null,
        visual_prompt: 'Capture the strongest repo walkthrough moment as a deliberate screen recording clip.',
        video_trim_start: 1.5,
        video_trim_end: null,
        video_playback_speed: 1.25,
        video_hold_last_frame: true,
      })
      fs.writeFileSync(planPath, `${JSON.stringify(plan, null, 2)}\n`, 'utf8')
    })

    test.afterAll(() => {
      cleanupProjectFixture(DISPOSABLE_PROJECT)
    })

    test.beforeEach(async ({ page }) => {
      await page.goto(`/projects/${DISPOSABLE_PROJECT}/scenes`)
      await expect(page.getByRole('listbox', { name: 'Scene timeline' })).toBeVisible()
    })

    test('title edits persist through the real save endpoint', async ({ page }) => {
      const titleInput = page.getByLabel('Scene title')
      const updatedTitle = 'Scene title saved by e2e'

      const saveResponse = page.waitForResponse((response) =>
        response.request().method() === 'PUT'
        && response.url().includes(`/api/projects/${DISPOSABLE_PROJECT}/plan`),
      )

      await titleInput.fill(updatedTitle)
      await saveResponse
      await page.reload()

      await expect(page.getByLabel('Scene title')).toHaveValue(updatedTitle)
    })

    test('composition edits persist through the real save endpoint', async ({ page }) => {
      const saveResponse = page.waitForResponse((response) =>
        response.request().method() === 'PUT'
        && response.url().includes(`/api/projects/${DISPOSABLE_PROJECT}/plan`),
      )

      await selectInspectorOption(page, 'Composition family', 'kinetic_statements', 'Kinetic statements')
      await expectInspectorOption(page, 'Composition behavior', 'native', 'Native')
      await selectInspectorOption(page, 'Transition after', 'fade', 'Fade')
      await saveResponse

      await expect.poll(() => {
        const plan = readProjectPlan(DISPOSABLE_PROJECT) as MutablePlan
        const composition = plan.scenes?.[0]?.composition ?? {}
        return `${composition.family ?? ''}|${composition.mode ?? ''}|${composition.transition_after?.kind ?? ''}`
      }).toBe('kinetic_statements|native|fade')

      const resetPlan = readProjectPlan(DISPOSABLE_PROJECT) as MutablePlan
      const firstScene = resetPlan.scenes[0]
      firstScene.scene_type = 'image'
      firstScene.image_path = `projects/${DISPOSABLE_PROJECT}/images/scene_000.svg`
      firstScene.video_path = null
      firstScene.preview_path = null
      firstScene.motion = null
      firstScene.composition = {
        family: 'media_pan',
        mode: 'none',
        manifestation: 'authored_image',
        props: {
          headline: String(firstScene.title || 'Scene 1'),
          body: String(firstScene.narration || ''),
        },
        transition_after: null,
        data: {},
        render_path: null,
        preview_path: null,
        rationale: 'Reset after native composition persistence check.',
      }
      const planPath = path.join(process.cwd(), '..', 'projects', DISPOSABLE_PROJECT, 'plan.json')
      fs.writeFileSync(planPath, `${JSON.stringify(resetPlan, null, 2)}\n`, 'utf8')

      await page.reload()
      await expectInspectorOption(page, 'Composition family', 'media_pan', 'Media pan')
      await expectInspectorOption(page, 'Composition behavior', 'none', 'None')
      await expectInspectorOption(page, 'Transition after', '', 'None')
    })

    test('image direction refine sends feedback to the correct endpoint', async ({ page }) => {
      const plan = readProjectPlan(DISPOSABLE_PROJECT)
      const firstScene = (plan.scenes as Array<Record<string, unknown>>)[0]
      const sceneUid = String(firstScene.uid)

      await page.route(`**/api/projects/${DISPOSABLE_PROJECT}/scenes/${sceneUid}/prompt-refine`, async (route) => {
        const payload = route.request().postDataJSON() as Record<string, unknown>
        expect(payload.feedback).toBe('Make the direction tighter and more cinematic')

        const updatedPlan = structuredClone(plan) as Record<string, unknown>
        const scenes = updatedPlan.scenes as Array<Record<string, unknown>>
        scenes[0].visual_prompt = 'Direction refined by intercepted request'
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(updatedPlan),
        })
      })

      await page.getByRole('button', { name: 'Improve Direction' }).click()
      await page.getByLabel('Image direction feedback').fill('Make the direction tighter and more cinematic')
      await page.getByRole('button', { name: 'Submit' }).click()

      await expect(page.getByLabel('Image direction')).toHaveValue('Direction refined by intercepted request')
    })

    test('narration refine sends feedback to the correct endpoint', async ({ page }) => {
      const plan = readProjectPlan(DISPOSABLE_PROJECT)
      const firstScene = (plan.scenes as Array<Record<string, unknown>>)[0]
      const sceneUid = String(firstScene.uid)

      await page.route(`**/api/projects/${DISPOSABLE_PROJECT}/scenes/${sceneUid}/narration-refine`, async (route) => {
        const payload = route.request().postDataJSON() as Record<string, unknown>
        expect(payload.feedback).toBe('Make it shorter and sharper')

        const updatedPlan = structuredClone(plan) as Record<string, unknown>
        const scenes = updatedPlan.scenes as Array<Record<string, unknown>>
        scenes[0].narration = 'Narration refined by intercepted request'
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(updatedPlan),
        })
      })

      await page.getByRole('button', { name: 'Refine Narration' }).click()
      await page.getByLabel('Narration refine feedback').fill('Make it shorter and sharper')
      await page.getByRole('button', { name: 'Submit' }).click()

      await expect(page.getByLabel('Narration text')).toHaveValue('Narration refined by intercepted request')
    })

    test('audio generation uses the project profile server-side instead of stale scene overrides', async ({ page }) => {
      const plan = readProjectPlan(DISPOSABLE_PROJECT)
      const firstScene = (plan.scenes as Array<Record<string, unknown>>)[0]
      const sceneUid = String(firstScene.uid)

      await page.route(`**/api/projects/${DISPOSABLE_PROJECT}/scenes/${sceneUid}/audio-generate`, async (route) => {
        const payload = route.request().postDataJSON() as Record<string, unknown>
        expect(payload).toEqual({})

        const updatedPlan = structuredClone(plan) as Record<string, unknown>
        const scenes = updatedPlan.scenes as Array<Record<string, unknown>>
        scenes[0].audio_path = `projects/${DISPOSABLE_PROJECT}/audio/scene_${sceneUid}.wav`
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(updatedPlan),
        })
      })

      await page.getByRole('button', { name: 'Generate Audio' }).click()
      await expect(page.getByRole('region', { name: 'Scene inspector' }).locator('audio')).toBeVisible()
    })

    test('scene-level voice overrides persist to the plan', async ({ page }) => {
      const saveResponse = page.waitForResponse((response) =>
        response.request().method() === 'PUT'
        && response.url().includes(`/api/projects/${DISPOSABLE_PROJECT}/plan`),
      )

      await page.getByLabel('Override project narrator for this scene').check()
      await page.getByLabel('Scene Voice', { exact: true }).selectOption('af_sarah')
      await page.getByLabel('Scene Voice Speed').fill('1.25')
      await saveResponse

      await expect.poll(() => {
        const plan = readProjectPlan(DISPOSABLE_PROJECT) as MutablePlan
        const scene = plan.scenes?.[0] ?? {}
        return `${scene.tts_override_enabled ?? false}|${scene.tts_voice ?? ''}|${scene.tts_speed ?? ''}`
      }).toBe('true|af_sarah|1.25')

      await page.reload()
      await expect(page.getByLabel('Override project narrator for this scene')).toBeChecked()
      await expect(page.getByLabel('Scene Voice', { exact: true })).toHaveValue('af_sarah')
    })

    test('image upload targets the image-upload endpoint', async ({ page }, testInfo) => {
      const plan = readProjectPlan(DISPOSABLE_PROJECT)
      const firstScene = (plan.scenes as Array<Record<string, unknown>>)[0]
      const sceneUid = String(firstScene.uid)
      const uploadPath = testInfo.outputPath('upload-image.png')
      fs.writeFileSync(uploadPath, Buffer.from('fake-image'))

      await page.route(`**/api/projects/${DISPOSABLE_PROJECT}/scenes/${sceneUid}/image-upload`, async (route) => {
        const contentType = route.request().headers()['content-type'] ?? ''
        expect(contentType).toContain('multipart/form-data')
        expect(contentType).not.toContain('application/json')

        const updatedPlan = structuredClone(plan) as Record<string, unknown>
        const scenes = updatedPlan.scenes as Array<Record<string, unknown>>
        scenes[0].image_path = `projects/${DISPOSABLE_PROJECT}/images/image_${sceneUid}.png`
        writeProjectImage(DISPOSABLE_PROJECT, `image_${sceneUid}.png`)
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(updatedPlan),
        })
      })

      await page.locator('input[type="file"][accept="image/*"]').setInputFiles(uploadPath)

      const stageImage = page.getByRole('region', { name: 'Media stage' }).locator('img').filter({ visible: true }).first()
      await expect(stageImage).toBeVisible()
    })

    test('generate image shows an in-flight progress bar with the current scene label', async ({ page }) => {
      const plan = readProjectPlan(DISPOSABLE_PROJECT)
      const firstScene = (plan.scenes as Array<Record<string, unknown>>)[0]
      const sceneUid = String(firstScene.uid)
      const currentSceneTitle = await page.getByLabel('Scene title').inputValue()

      await page.route(`**/api/projects/${DISPOSABLE_PROJECT}/scenes/${sceneUid}/image-generate`, async (route) => {
        const updatedPlan = structuredClone(plan) as Record<string, unknown>
        const scenes = updatedPlan.scenes as Array<Record<string, unknown>>
        scenes[0].image_path = `projects/${DISPOSABLE_PROJECT}/images/image_${sceneUid}.png`
        writeProjectImage(DISPOSABLE_PROJECT, `image_${sceneUid}.png`)
        await new Promise((resolve) => setTimeout(resolve, 400))
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(updatedPlan),
        })
      })

      await page.getByRole('button', { name: /Generate Image|Regenerate Image/ }).click()
      const progressStack = page.locator('.scene-inspector__progress-stack').first()
      await expect(progressStack.getByText(/Generating image|Regenerating image/)).toBeVisible()
      await expect(progressStack.getByText(`Scene 1 - ${currentSceneTitle}`, { exact: true })).toBeVisible()
    })

    test('pending scene edits are flushed before image generation starts', async ({ page }) => {
      const plan = readProjectPlan(DISPOSABLE_PROJECT)
      const firstScene = (plan.scenes as Array<Record<string, unknown>>)[0]
      const sceneUid = String(firstScene.uid)
      const updatedTitle = 'Title saved before generation'
      let saveCompleted = false

      await page.route(`**/api/projects/${DISPOSABLE_PROJECT}/plan`, async (route) => {
        if (route.request().method() !== 'PUT') {
          await route.continue()
          return
        }
        const payload = route.request().postDataJSON() as Record<string, unknown>
        expect(payload.scenes[0].title).toBe(updatedTitle)
        await new Promise((resolve) => setTimeout(resolve, 150))
        saveCompleted = true
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(payload),
        })
      })

      await page.route(`**/api/projects/${DISPOSABLE_PROJECT}/scenes/${sceneUid}/image-generate`, async (route) => {
        expect(saveCompleted).toBe(true)
        const updatedPlan = structuredClone(plan) as Record<string, unknown>
        updatedPlan.scenes[0].title = updatedTitle
        updatedPlan.scenes[0].image_path = `projects/${DISPOSABLE_PROJECT}/images/image_${sceneUid}.png`
        writeProjectImage(DISPOSABLE_PROJECT, `image_${sceneUid}.png`)
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(updatedPlan),
        })
      })

      await page.getByLabel('Scene title').fill(updatedTitle)
      await page.getByRole('button', { name: /Generate Image|Regenerate Image/ }).click()

      await expect(page.getByLabel('Scene title')).toHaveValue(updatedTitle)
      await expect(page.getByRole('region', { name: 'Media stage' }).locator('img').filter({ visible: true }).first()).toBeVisible()
    })

    test('preview generation targets the preview endpoint and shows the player', async ({ page }) => {
      const plan = readProjectPlan(DISPOSABLE_PROJECT)
      const firstScene = (plan.scenes as Array<Record<string, unknown>>)[0]
      const sceneUid = String(firstScene.uid)

      await page.route(`**/api/projects/${DISPOSABLE_PROJECT}/scenes/${sceneUid}/preview`, async (route) => {
        const updatedPlan = structuredClone(plan) as Record<string, unknown>
        const scenes = updatedPlan.scenes as Array<Record<string, unknown>>
        scenes[0].preview_path = `projects/${DISPOSABLE_PROJECT}/previews/preview_scene_000.mp4`
        scenes[0].preview_exists = true
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(updatedPlan),
        })
      })

      await page.locator('button[aria-controls="scene-preview-content"]').click()
      await page.getByRole('button', { name: 'Generate Preview' }).click()
      await expect(page.getByRole('region', { name: 'Scene inspector' }).locator('video')).toBeVisible()
    })

    test('operator section shows persisted recent image activity for the selected scene', async ({ page }) => {
      await page.locator('button[aria-controls="scene-operator-content"]').click()

      await expect(page.getByText('Recent image activity')).toBeVisible()
      await expect(page.getByText('Image edit', { exact: true })).toBeVisible()
      await expect(page.getByText('Increase contrast and clean the label')).toBeVisible()
    })

    test('video scenes expose clip controls and the separate demo capture action', async ({ page }) => {
      const plan = readProjectPlan(DISPOSABLE_PROJECT)
      const videoScene = (plan.scenes as Array<Record<string, unknown>>)[1]
      const sceneUid = String(videoScene.uid)

      await page.getByRole('listbox', { name: 'Scene timeline' }).getByRole('option').nth(1).click()
      await expectInspectorOption(page, 'Scene type', 'video', 'Video')
      await expect(page.getByRole('button', { name: 'Generate Video' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Capture Demo Scene' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Generate Image' })).toHaveCount(0)
      await expect(page.getByText('Clip Notes / Shot Direction')).toBeVisible()
      const saveResponse = page.waitForResponse((response) =>
        response.request().method() === 'PUT'
        && response.url().includes(`/api/projects/${DISPOSABLE_PROJECT}/plan`),
      )
      await page.getByLabel('Clip style').selectOption('auto')
      await saveResponse
      await expect(page.getByLabel('Clip style')).toHaveValue('auto')
      await expect(page.getByLabel('Model selection')).toHaveValue('automatic')
      await expect(page.locator('p').filter({ hasText: /Automatic routing picks the cinematic or speaking lane/ })).toBeVisible()
      await expect(page.getByLabel('Scene audio source')).toHaveValue('narration')
      await expect(page.getByLabel('Clip Start (seconds)')).toHaveValue('1.5')
      await expect(page.getByLabel('Playback Speed')).toHaveValue('1.25')

      await page.route(`**/api/projects/${DISPOSABLE_PROJECT}/agent-demo`, async (route) => {
        const payload = route.request().postDataJSON() as Record<string, unknown>
        expect(payload.scene_uids).toEqual([sceneUid])
        expect(payload.run_until).toBe('assets')
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'queued',
            job_id: 'agent-demo-test',
            project_name: DISPOSABLE_PROJECT,
            project_dir: `/tmp/${DISPOSABLE_PROJECT}`,
            current_stage: 'queued',
            retryable: false,
            suggestion: '',
            requested_stage: 'agent_demo',
            pid: 12345,
            result: {},
            error: null,
            request: payload,
          }),
        })
      })

      await page.getByRole('button', { name: 'Capture Demo Scene' }).click()
    })

    test('scene management controls insert before and after, then delete the selected scene', async ({ page }) => {
      const originalPlan = readProjectPlan(DISPOSABLE_PROJECT)
      const originalScenes = originalPlan.scenes as Array<Record<string, unknown>>
      const originalCount = originalScenes.length
      const originalFirstUid = String(originalScenes[0].uid)
      const inspector = page.getByRole('region', { name: 'Scene inspector' })

      const readSceneUids = () =>
        (readProjectPlan(DISPOSABLE_PROJECT).scenes as Array<Record<string, unknown>>).map((scene) => String(scene.uid))

      await expect(inspector.getByRole('button', { name: 'Add Scene Before' })).toBeVisible()
      await expect(inspector.getByRole('button', { name: 'Add Scene After' })).toBeVisible()
      await expect(inspector.getByRole('button', { name: 'Delete Scene' })).toBeVisible()

      await inspector.getByRole('button', { name: 'Add Scene Before' }).click()
      await expect.poll(() => readSceneUids().length).toBe(originalCount + 1)

      const uidsAfterBefore = readSceneUids()
      const insertedBeforeUid = uidsAfterBefore[0]
      expect(insertedBeforeUid).not.toBe(originalFirstUid)
      expect(uidsAfterBefore[1]).toBe(originalFirstUid)
      await expect(page.getByRole('listbox', { name: 'Scene timeline' }).getByRole('option').first()).toHaveAttribute('aria-selected', 'true')

      await inspector.getByRole('button', { name: 'Add Scene After' }).click()
      await expect.poll(() => readSceneUids().length).toBe(originalCount + 2)

      const uidsAfterAfter = readSceneUids()
      const insertedAfterUid = uidsAfterAfter[1]
      expect(insertedAfterUid).not.toBe(originalFirstUid)
      expect(insertedAfterUid).not.toBe(insertedBeforeUid)
      expect(uidsAfterAfter[2]).toBe(originalFirstUid)
      await expect(page.getByRole('listbox', { name: 'Scene timeline' }).getByRole('option').nth(1)).toHaveAttribute('aria-selected', 'true')

      page.once('dialog', async (dialog) => {
        expect(dialog.message()).toBe('Delete this scene?')
        await dialog.accept()
      })
      await inspector.getByRole('button', { name: 'Delete Scene' }).click()
      await expect.poll(() => readSceneUids().length).toBe(originalCount + 1)

      const uidsAfterDelete = readSceneUids()
      expect(uidsAfterDelete[0]).toBe(insertedBeforeUid)
      expect(uidsAfterDelete[1]).toBe(originalFirstUid)
      expect(uidsAfterDelete).not.toContain(insertedAfterUid)
      await expect(page.getByRole('listbox', { name: 'Scene timeline' }).getByRole('option').nth(1)).toHaveAttribute('aria-selected', 'true')
    })

    test('timeline add card keeps the inspector hidden when the user is in canvas-focus mode', async ({ page }) => {
      const originalCount = (readProjectPlan(DISPOSABLE_PROJECT).scenes as Array<Record<string, unknown>>).length

      await page.getByRole('button', { name: 'Hide Inspector' }).click()
      await expect(page.getByRole('region', { name: 'Scene inspector' })).toHaveCount(0)

      await page.getByLabel('Add scene').click()

      await expect.poll(() => (readProjectPlan(DISPOSABLE_PROJECT).scenes as Array<Record<string, unknown>>).length).toBe(originalCount + 1)
      await expect(page.getByRole('region', { name: 'Scene inspector' })).toHaveCount(0)
      await expect(page.getByRole('button', { name: 'Show Inspector' })).toBeVisible()
    })
  })

  test.describe.serial('template deck composition editors', () => {
    const TEMPLATE_PROJECT = `e2e_template_deck_${Date.now()}`

    test.beforeAll(() => {
      cloneProjectFixture(PROJECT, TEMPLATE_PROJECT)
      const planPath = path.resolve(process.cwd(), '..', 'projects', TEMPLATE_PROJECT, 'plan.json')
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as MutablePlan
      plan.meta.render_profile = {
        ...(plan.meta.render_profile || {}),
        render_backend: 'remotion',
      }
      plan.meta.brief = {
        ...(plan.meta.brief || {}),
        composition_mode: 'motion_only',
      }

      // Scene 0: cover_hook with headline, subtitle, kicker
      Object.assign(plan.scenes[0], {
        scene_type: 'motion',
        image_path: null,
        video_path: null,
        preview_path: null,
        composition: {
          family: 'cover_hook',
          mode: 'native',
          props: {
            headline: 'Your Season Recap',
            subtitle: 'A personalized performance review',
            kicker: 'Session 3 of 10',
          },
        },
      })

      // Scene 1: metric_improvement with before/after, delta, direction
      if (plan.scenes.length > 1) {
        Object.assign(plan.scenes[1], {
          scene_type: 'motion',
          image_path: null,
          video_path: null,
          preview_path: null,
          composition: {
            family: 'metric_improvement',
            mode: 'native',
            props: {
              headline: 'Win Rate',
              metric_name: 'Win rate (rolling 30d)',
              before: { value: '4.2%', label: 'Session 1' },
              after: { value: '6.1%', label: 'Session 3' },
              delta: '+45%',
              direction: 'improvement',
              caption: 'Upward trend',
            },
          },
        })
      }

      // Scene 2: timeline_progression with markers array
      if (plan.scenes.length > 2) {
        Object.assign(plan.scenes[2], {
          scene_type: 'motion',
          image_path: null,
          video_path: null,
          preview_path: null,
          composition: {
            family: 'timeline_progression',
            mode: 'native',
            props: {
              headline: 'Rollout Window',
              span_label: '6-month rollout',
              markers: [
                { label: 'Intake', date: 'Jan', annotation: 'Baseline', status: 'completed' },
                { label: 'Mid-point', date: 'Apr', annotation: 'Check-in', status: 'current' },
              ],
              caption: 'On track',
            },
          },
        })
      }

      fs.writeFileSync(planPath, JSON.stringify(plan, null, 2))
    })

    test.afterAll(() => {
      cleanupProjectFixture(TEMPLATE_PROJECT)
    })

    test('cover_hook editor shows headline, subtitle, and kicker fields', async ({ page }) => {
      await page.goto(`/projects/${TEMPLATE_PROJECT}/scenes`)
      await expect(page.getByRole('region', { name: 'Scene inspector' })).toBeVisible()
      await expectInspectorOption(page, 'Scene type', 'motion', 'Remotion')
      await expectInspectorOption(page, 'Composition family', 'cover_hook', 'Cover hook')
      await expect(page.getByLabel('Cover headline')).toHaveValue('Your Season Recap')
      await expect(page.getByLabel('Cover subtitle')).toHaveValue('A personalized performance review')
      await expect(page.getByLabel('Cover kicker')).toHaveValue('Session 3 of 10')
    })

    test('metric_improvement editor shows before/after panels and delta', async ({ page }) => {
      await page.goto(`/projects/${TEMPLATE_PROJECT}/scenes`)
      await expect(page.getByRole('region', { name: 'Scene inspector' })).toBeVisible()
      await page.getByRole('listbox', { name: 'Scene timeline' }).getByRole('option').nth(1).click()
      await expectInspectorOption(page, 'Composition family', 'metric_improvement', 'Metric improvement')
      await expect(page.getByLabel('Metric headline')).toHaveValue('Win Rate')
      await expect(page.getByLabel('Metric name')).toHaveValue('Win rate (rolling 30d)')
      await expect(page.getByLabel('Before value')).toHaveValue('4.2%')
      await expect(page.getByLabel('Before label')).toHaveValue('Session 1')
      await expect(page.getByLabel('After value')).toHaveValue('6.1%')
      await expect(page.getByLabel('After label')).toHaveValue('Session 3')
      await expect(page.getByLabel('Delta')).toHaveValue('+45%')
      await expect(page.getByLabel('Direction', { exact: true })).toHaveValue('improvement')
    })

    test('timeline_progression editor shows headline, span_label, markers, and caption', async ({ page }) => {
      await page.goto(`/projects/${TEMPLATE_PROJECT}/scenes`)
      await expect(page.getByRole('region', { name: 'Scene inspector' })).toBeVisible()
      await page.getByRole('listbox', { name: 'Scene timeline' }).getByRole('option').nth(2).click()
      await expectInspectorOption(page, 'Composition family', 'timeline_progression', 'Timeline progression')
      await expect(page.getByLabel('Timeline headline')).toHaveValue('Rollout Window')
      await expect(page.getByLabel('Span label')).toHaveValue('6-month rollout')
      await expect(page.getByLabel('Timeline caption')).toHaveValue('On track')
      await expect(page.getByText('Markers (2)')).toBeVisible()
    })

    test('cover_hook prop edits persist through the real save endpoint', async ({ page }) => {
      await page.goto(`/projects/${TEMPLATE_PROJECT}/scenes`)
      await expect(page.getByLabel('Cover headline')).toBeVisible()

      const saveResponse = page.waitForResponse((response) =>
        response.request().method() === 'PUT'
        && response.url().includes(`/api/projects/${TEMPLATE_PROJECT}/plan`),
      )

      await page.getByLabel('Cover headline').fill('Updated Season Recap')
      await saveResponse

      await expect.poll(() => {
        const plan = readProjectPlan(TEMPLATE_PROJECT) as MutablePlan
        const props = plan.scenes?.[0]?.composition?.props ?? {}
        return props.headline ?? ''
      }).toBe('Updated Season Recap')

      await page.reload()
      await expect(page.getByLabel('Cover headline')).toHaveValue('Updated Season Recap')
    })
  })
})
