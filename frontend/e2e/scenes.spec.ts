import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

import { cleanupProjectFixture, cloneProjectFixture, readProjectPlan } from './helpers/project-fixture'

const PROJECT = 'bet365_feature_act_01'
const DISPOSABLE_PROJECT = `e2e_scene_mutation_${Date.now()}`
const MOTION_PROJECT = `e2e_motion_scene_${Date.now()}`

test.describe('Scene Timeline', () => {
  function setNarrowInspectorLayout() {
    window.localStorage.setItem('cathode-ui', JSON.stringify({
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
      const options = page.getByRole('option')
      await expect(options.first()).toBeVisible()
      await expect(page.getByLabel('Scene title')).toBeVisible()
      await expect(page.getByLabel('Narration text')).toBeVisible()
      await expect(page.getByLabel('Visual prompt')).toBeVisible()
      await expect(page.getByRole('button', { name: 'Generate All Assets' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Render Video' })).toBeVisible()
      await expect(page.getByLabel('Image editor')).toBeVisible()
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

    test('selecting another scene updates the inspector', async ({ page }) => {
      const titleInput = page.getByLabel('Scene title')
      const firstTitle = await titleInput.inputValue()

      const secondScene = page.getByRole('option').nth(1)
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
      await expect(page.getByRole('region', { name: 'Scene inspector' })).toBeVisible()
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
      await expect(page.getByLabel('On-screen text 1')).toBeVisible()
      await expect(page.getByRole('button', { name: 'Generate Preview' })).toBeVisible()
    })

    test('small viewport compacts navigation and keeps scenes scrollable', async ({ page }) => {
      await page.setViewportSize({ width: 603, height: 720 })
      await page.evaluate(() => {
        window.localStorage.setItem('cathode-ui', JSON.stringify({
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

    test('operator section shows effective generation payload', async ({ page }) => {
      await page.locator('button[aria-controls="scene-operator-content"]').click()
      const operatorContent = page.locator('#scene-operator-content')
      await expect(operatorContent.getByText('Generate image', { exact: true })).toBeVisible()
      await expect(operatorContent).toContainText('"generate"')
      await expect(operatorContent).toContainText('"provider": "replicate"')
      await expect(operatorContent).toContainText('"edit"')
      await expect(operatorContent).toContainText('"model": "qwen/qwen-image-edit-2511"')
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
      const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as Record<string, any>
      plan.meta.render_profile = {
        ...(plan.meta.render_profile || {}),
        render_backend: 'remotion',
      }
      plan.meta.brief = {
        ...(plan.meta.brief || {}),
        composition_mode: 'hybrid',
      }
      const scene = plan.scenes[0]
      scene.scene_type = 'motion'
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
      fs.writeFileSync(planPath, JSON.stringify(plan, null, 2))
    })

    test.afterAll(() => {
      cleanupProjectFixture(MOTION_PROJECT)
    })

    test('motion scenes expose template controls in the live workspace', async ({ page }) => {
      await page.goto(`/projects/${MOTION_PROJECT}/scenes`)
      await expect(page.getByRole('region', { name: 'Scene inspector' })).toBeVisible()
      await expect(page.getByLabel('Scene type')).toHaveValue('motion')
      await expect(page.getByLabel('Motion template')).toHaveValue('bullet_stack')
      await expect(page.getByRole('button', { name: 'Generate Motion Preview' })).toBeVisible()
      await expect(page.getByLabel('Motion headline')).toHaveValue('Prompts on prompts')
      await expect(page.getByRole('region', { name: 'Media stage' })).toContainText('Motion template')
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
          provider: 'manual',
          generation_model: '',
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

    test('prompt refine sends feedback to the correct endpoint', async ({ page }) => {
      const plan = readProjectPlan(DISPOSABLE_PROJECT)
      const firstScene = (plan.scenes as Array<Record<string, unknown>>)[0]
      const sceneUid = String(firstScene.uid)

      await page.route(`**/api/projects/${DISPOSABLE_PROJECT}/scenes/${sceneUid}/prompt-refine`, async (route) => {
        const payload = route.request().postDataJSON() as Record<string, unknown>
        expect(payload.feedback).toBe('Make the prompt tighter and more cinematic')

        const updatedPlan = structuredClone(plan) as Record<string, unknown>
        const scenes = updatedPlan.scenes as Array<Record<string, unknown>>
        scenes[0].visual_prompt = 'Prompt refined by intercepted request'
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(updatedPlan),
        })
      })

      await page.getByRole('button', { name: 'Refine Prompt' }).click()
      await page.getByLabel('Prompt refine feedback').fill('Make the prompt tighter and more cinematic')
      await page.getByRole('button', { name: 'Submit' }).click()

      await expect(page.getByLabel('Visual prompt')).toHaveValue('Prompt refined by intercepted request')
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
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(updatedPlan),
        })
      })

      await page.locator('input[type="file"][accept="image/*"]').setInputFiles(uploadPath)

      const stageImage = page.getByRole('region', { name: 'Media stage' }).locator('img')
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

    test('preview generation targets the preview endpoint and shows the player', async ({ page }) => {
      const plan = readProjectPlan(DISPOSABLE_PROJECT)
      const firstScene = (plan.scenes as Array<Record<string, unknown>>)[0]
      const sceneUid = String(firstScene.uid)

      await page.route(`**/api/projects/${DISPOSABLE_PROJECT}/scenes/${sceneUid}/preview`, async (route) => {
        const updatedPlan = structuredClone(plan) as Record<string, unknown>
        const scenes = updatedPlan.scenes as Array<Record<string, unknown>>
        scenes[0].preview_path = `projects/${DISPOSABLE_PROJECT}/previews/preview_scene_000.mp4`
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

    test('video scenes expose clip controls and the separate agent demo action', async ({ page }) => {
      const plan = readProjectPlan(DISPOSABLE_PROJECT)
      const videoScene = (plan.scenes as Array<Record<string, unknown>>)[1]
      const sceneUid = String(videoScene.uid)

      await page.getByRole('option').nth(1).click()
      await expect(page.getByLabel('Scene type')).toHaveValue('video')
      await expect(page.getByRole('button', { name: 'Generate Video' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Agent Demo Scene' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Generate Image' })).toHaveCount(0)
      await expect(page.getByText('Clip Notes / Shot Direction')).toBeVisible()
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

      await page.getByRole('button', { name: 'Agent Demo Scene' }).click()
    })
  })
})
