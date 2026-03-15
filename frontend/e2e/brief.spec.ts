import { test, expect, type Page } from '@playwright/test'

const EXISTING_PROJECT = 'bet365_feature_act_01'
const MOCK_BOOTSTRAP = {
  providers: {
    api_keys: {
      openai: true,
      anthropic: true,
      replicate: true,
      dashscope: false,
      elevenlabs: false,
    },
    llm_provider: 'anthropic',
    image_providers: ['replicate', 'manual'],
    video_providers: ['replicate', 'manual'],
    render_backends: ['ffmpeg', 'remotion'],
    remotion_available: true,
    remotion_capabilities: {
      render_available: true,
      player_available: true,
      transitions_available: true,
      three_available: true,
    },
    tts_providers: {
      kokoro: 'Kokoro (Local)',
    },
    tts_voice_options: {
      kokoro: [],
      elevenlabs: [],
      openai: [],
      chatterbox: [],
    },
    image_edit_models: ['qwen/qwen-image-edit-2511'],
  },
  defaults: {
    brief: {
      project_name: 'my_video',
      source_mode: 'source_text',
      video_goal: '',
      audience: '',
      source_material: '',
      target_length_minutes: 3,
      tone: '',
      visual_style: '',
      must_include: '',
      must_avoid: '',
      ending_cta: '',
      paid_media_budget_usd: '',
      composition_mode: 'auto',
      visual_source_strategy: 'images_only',
      video_scene_style: 'auto',
      text_render_mode: 'visual_authored',
      available_footage: '',
      footage_manifest: [],
      style_reference_summary: '',
      style_reference_paths: [],
      raw_brief: '',
    },
    render_profile: {
      aspect_ratio: '16:9',
      width: 1664,
      height: 928,
      fps: 24,
      scene_types: ['image', 'video', 'motion'],
      render_strategy: 'auto',
      render_backend: 'ffmpeg',
      text_render_mode: 'visual_authored',
    },
    image_profile: {
      provider: 'replicate',
      generation_model: 'qwen/qwen-image-2512',
      edit_model: 'qwen/qwen-image-edit-2511',
    },
    video_profile: {
      provider: 'manual',
      generation_model: '',
      model_selection_mode: 'automatic',
      quality_mode: 'standard',
      generate_audio: true,
    },
    tts_profile: {
      provider: 'kokoro',
      voice: 'af_bella',
    },
  },
  projects: [],
} as const

async function openAdvancedCreativeControls(page: Page) {
  const summary = page.getByText('Override scene engine and text strategy')
  await expect(summary).toBeVisible()
  await summary.click()
  await expect(page.getByLabel('Scene Engine')).toBeVisible()
}

test.describe('Brief Studio', () => {
  test.describe('New project', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/projects/new/brief')
      await expect(page.getByRole('heading', { name: 'Brief Studio' })).toBeVisible()
    })

    test('page shows header, subtitle, and breadcrumbs', async ({ page }) => {
      const banner = page.getByRole('banner')
      await expect(banner.getByRole('heading', { name: 'Brief Studio' })).toBeVisible()
      await expect(banner.getByText('New project', { exact: true })).toBeVisible()
      // Breadcrumbs
      const breadcrumb = banner.getByRole('navigation', { name: 'Breadcrumb' })
      await expect(breadcrumb.getByRole('link', { name: 'Projects' })).toBeVisible()
      await expect(breadcrumb.getByText('New Project', { exact: true })).toBeVisible()
    })

    // ── Form Sections ───────────────────────────────────────────
    test('Project Basics fieldset renders with inputs', async ({ page }) => {
      await expect(page.locator('legend:has-text("Project Basics")')).toBeVisible()

      const nameInput = page.getByLabel('Project Name')
      await expect(nameInput).toBeVisible()

      const sourceMode = page.getByLabel('Source Mode')
      await expect(sourceMode).toBeVisible()
      await expect(page.locator('legend:has-text("Advanced Creative Controls")')).toBeVisible()
    })

    test('Content fieldset renders with all fields', async ({ page }) => {
      await expect(page.locator('legend:has-text("Content")')).toBeVisible()

      await expect(page.getByLabel('Source Material')).toBeVisible()
      await expect(page.getByLabel('Video Goal')).toBeVisible()
      await expect(page.getByLabel('Audience')).toBeVisible()
      await expect(page.getByLabel('Target Length')).toBeVisible()
    })

    test('Style fieldset renders', async ({ page }) => {
      await expect(page.locator('legend:has-text("Style")')).toBeVisible()
      await expect(page.getByLabel('Tone')).toBeVisible()
      await expect(page.getByLabel('Visual Style')).toBeVisible()
      await expect(page.getByLabel('Visual Source Strategy')).toBeVisible()
      await expect(page.getByLabel('Generated Video Scene Style')).toBeVisible()
    })

    test('Constraints fieldset renders', async ({ page }) => {
      await expect(page.locator('legend:has-text("Constraints")')).toBeVisible()
      await expect(page.getByLabel('Must Include')).toBeVisible()
      await expect(page.getByLabel('Must Avoid')).toBeVisible()
      await expect(page.getByLabel('Ending CTA')).toBeVisible()
    })

    // ── Text Input interactions ──────────────────────────────────
    test('Project Name input accepts text and clears', async ({ page }) => {
      const input = page.getByLabel('Project Name')
      await input.click()
      await input.fill('Test Project Alpha')
      await expect(input).toHaveValue('Test Project Alpha')

      // Clear and refill
      await input.fill('')
      await expect(input).toHaveValue('')
      await input.fill('Renamed Project')
      await expect(input).toHaveValue('Renamed Project')
    })

    test('Source Material textarea accepts multi-line text', async ({ page }) => {
      const textarea = page.getByLabel('Source Material')
      await textarea.click()
      await textarea.fill('Line 1\nLine 2\nLine 3')
      await expect(textarea).toHaveValue('Line 1\nLine 2\nLine 3')
    })

    test('Video Goal input with placeholder', async ({ page }) => {
      const input = page.getByLabel('Video Goal')
      await expect(input).toHaveAttribute('placeholder', /What should the viewer/)
      await input.fill('Teach users about our product')
      await expect(input).toHaveValue('Teach users about our product')
    })

    test('Audience input interaction', async ({ page }) => {
      const input = page.getByLabel('Audience')
      await input.fill('Marketing professionals')
      await expect(input).toHaveValue('Marketing professionals')
    })

    // ── Select interactions ──────────────────────────────────────
    test('Source Mode select has all options', async ({ page }) => {
      const select = page.getByLabel('Source Mode')
      const options = select.locator('option')
      await expect(options).toHaveCount(3)

      // Change selection
      await select.selectOption('source_text')
      await expect(select).toHaveValue('source_text')

      await select.selectOption('final_script')
      await expect(select).toHaveValue('final_script')

      await select.selectOption('ideas_notes')
      await expect(select).toHaveValue('ideas_notes')
    })

    test('Visual Source Strategy select', async ({ page }) => {
      const select = page.getByLabel('Visual Source Strategy')
      await select.selectOption('mixed_media')
      await expect(select).toHaveValue('mixed_media')

      await select.selectOption('video_preferred')
      await expect(select).toHaveValue('video_preferred')
    })

    test('Generated Video Scene Style select steers clip planning', async ({ page }) => {
      const select = page.getByLabel('Generated Video Scene Style')
      await select.selectOption('speaking')
      await expect(select).toHaveValue('speaking')

      await select.selectOption('mixed')
      await expect(select).toHaveValue('mixed')

      await select.selectOption('auto')
      await expect(select).toHaveValue('auto')
    })

    test('Text Strategy select has both modes', async ({ page }) => {
      await openAdvancedCreativeControls(page)
      const select = page.getByLabel('Text Strategy')
      const options = select.locator('option')
      await expect(options).toHaveCount(2)

      await select.selectOption('deterministic_overlay')
      await expect(select).toHaveValue('deterministic_overlay')

      await select.selectOption('visual_authored')
      await expect(select).toHaveValue('visual_authored')
    })

    test('Scene Engine select has all options, including trust-claude auto', async ({ page }) => {
      await openAdvancedCreativeControls(page)
      const select = page.getByLabel('Scene Engine')
      const options = select.locator('option')
      await expect(options).toHaveCount(4)

      await select.selectOption('auto')
      await expect(select).toHaveValue('auto')

      await select.selectOption('hybrid')
      await expect(select).toHaveValue('hybrid')

      await select.selectOption('motion_only')
      await expect(select).toHaveValue('motion_only')

      await select.selectOption('classic')
      await expect(select).toHaveValue('classic')
    })

    test('Scene Engine choices stay visible even if bootstrap is unavailable', async ({ page }) => {
      await page.route('**/api/bootstrap', async (route) => {
        await route.abort()
      })

      await page.reload()
      await expect(page.getByRole('heading', { name: 'Brief Studio' })).toBeVisible()

      await openAdvancedCreativeControls(page)
      const select = page.getByLabel('Scene Engine')
      await expect(select.locator('option')).toHaveCount(4)
      await expect(select.locator('option[value="auto"]')).toHaveText('I Trust Claude to Decide')
    })

    test('Scene Engine shows disabled Remotion-only modes when bootstrap says Remotion is unavailable', async ({ page }) => {
      await page.route('**/api/bootstrap', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ...MOCK_BOOTSTRAP,
            providers: {
              ...MOCK_BOOTSTRAP.providers,
              remotion_available: false,
              render_backends: ['ffmpeg'],
            },
          }),
        })
      })

      await page.reload()
      await expect(page.getByRole('heading', { name: 'Brief Studio' })).toBeVisible()

      await openAdvancedCreativeControls(page)
      const hybridOption = page.locator('option[value="hybrid"]')
      const motionOnlyOption = page.locator('option[value="motion_only"]')
      await expect(hybridOption).toBeDisabled()
      await expect(motionOnlyOption).toBeDisabled()
    })

    // ── Slider interaction ───────────────────────────────────────
    test('Target Length slider displays value and can be changed', async ({ page }) => {
      // Slider display shows "2 min" default
      await expect(page.locator('text=2 min')).toBeVisible()

      // The slider input
      const slider = page.getByLabel('Target Length')
      await expect(slider).toBeVisible()

      // Change slider value
      await slider.fill('5')
      await expect(page.locator('text=5 min')).toBeVisible()
    })

    // ── Tone and Visual Style ────────────────────────────────────
    test('Tone and Visual Style inputs', async ({ page }) => {
      const tone = page.getByLabel('Tone')
      await tone.fill('Professional and warm')
      await expect(tone).toHaveValue('Professional and warm')

      const style = page.getByLabel('Visual Style')
      await style.fill('Cinematic')
      await expect(style).toHaveValue('Cinematic')
    })

    test('paid media budget appears when paid image/video generation is available', async ({ page }) => {
      await page.route('**/api/bootstrap', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_BOOTSTRAP),
        })
      })

      await page.reload()
      await expect(page.getByRole('heading', { name: 'Brief Studio' })).toBeVisible()

      const budgetInput = page.getByLabel('Paid Media Budget (USD)')
      await expect(budgetInput).toBeVisible()
      await budgetInput.fill('45')
      await expect(budgetInput).toHaveValue('45')
    })

    // ── Constraints textareas ────────────────────────────────────
    test('Must Include and Must Avoid textareas', async ({ page }) => {
      const include = page.getByLabel('Must Include')
      await include.fill('Logo placement\nProduct demo')
      await expect(include).toHaveValue('Logo placement\nProduct demo')

      const avoid = page.getByLabel('Must Avoid')
      await avoid.fill('Competitor names')
      await expect(avoid).toHaveValue('Competitor names')
    })

    test('Ending CTA input', async ({ page }) => {
      const cta = page.getByLabel('Ending CTA')
      await cta.fill('Visit example.com')
      await expect(cta).toHaveValue('Visit example.com')
    })

    // ── Submit button ────────────────────────────────────────────
    test('primary and secondary creation actions are visible for new project', async ({ page }) => {
      await expect(page.locator('button[type="submit"]:has-text("F#@K it, we\'re doing it live!!")')).toBeVisible()
      await expect(page.getByRole('button', { name: 'Storyboard Only' })).toBeVisible()
      await expect(page.getByRole('heading', { name: 'Demo target' })).toBeVisible()
    })

    test('live primary action starts a background make-video job and navigates to render', async ({ page }) => {
      await page.getByLabel('Project Name').fill('brief_live_demo')
      await page.getByLabel('Source Material').fill('Prompt plus a job description go in, a demo video comes out.')
      await page.getByLabel('Video Goal').fill('Show the one prompt to final render path.')
      await page.getByLabel('Audience').fill('Hiring manager')
      await page.getByLabel('Visual Source Strategy').selectOption('mixed_media')
      await page.getByLabel('Workspace Path').fill('/Users/davidmontgomery/cathode')
      await page.getByLabel('App URL').fill('http://127.0.0.1:9322')

      await page.route('**/api/jobs/make-video', async (route) => {
        const payload = route.request().postDataJSON() as Record<string, unknown>
        expect(payload.project_name).toBe('brief_live_demo')
        expect((payload.brief as Record<string, unknown>).video_goal).toBe('Show the one prompt to final render path.')
        expect((payload.brief as Record<string, unknown>).composition_mode).toBe('auto')
        expect((payload.agent_demo_profile as Record<string, unknown>).workspace_path).toBe('/Users/davidmontgomery/cathode')
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'queued',
            job_id: 'job-live-demo',
            project_name: 'brief_live_demo',
            project_dir: '/tmp/brief_live_demo',
            current_stage: 'queued',
            retryable: false,
            suggestion: '',
            requested_stage: 'render',
            pid: 1234,
            result: {},
            error: null,
          }),
        })
      })

      await page.locator('button[type="submit"]:has-text("F#@K it, we\'re doing it live!!")').click()
      await page.waitForURL('**/projects/brief_live_demo/render')
      await expect(page.getByRole('heading', { name: 'Render', exact: true })).toBeVisible()
    })

    // ── Tab through all fields ───────────────────────────────────
    test('Tab order traverses all form fields', async ({ page }) => {
      const nameInput = page.getByLabel('Project Name')
      await nameInput.focus()
      await expect(nameInput).toBeFocused()

      // Tab through subsequent fields
      await page.keyboard.press('Tab')
      // Should move to Source Mode
      await page.keyboard.press('Tab')
      // Continue tabbing through the form
      for (let i = 0; i < 10; i++) {
        await page.keyboard.press('Tab')
      }
      // No crashes during tab traversal
    })

    // ── Main creative inputs ─────────────────────────────────────
    test('style refs and footage panels stay in the main workspace at useful widths', async ({ page }) => {
      const stylePanel = page.getByRole('heading', { name: 'Style References', exact: true })
      const footagePanel = page.getByRole('heading', { name: 'Footage Library', exact: true })
      const styleDropzone = page.getByTestId('brief-style-dropzone')
      const footageDropzone = page.getByTestId('brief-footage-dropzone')

      await expect(stylePanel).toBeVisible()
      await expect(footagePanel).toBeVisible()
      await expect(styleDropzone).toBeVisible()
      await expect(footageDropzone).toBeVisible()

      const styleBox = await styleDropzone.boundingBox()
      const footageBox = await footageDropzone.boundingBox()

      expect(styleBox).not.toBeNull()
      expect(footageBox).not.toBeNull()
      expect(styleBox!.width).toBeGreaterThan(320)
      expect(footageBox!.width).toBeGreaterThan(320)
      expect(Math.abs(styleBox!.y - footageBox!.y)).toBeLessThan(20)
      expect(Math.abs(styleBox!.x - footageBox!.x)).toBeGreaterThan(40)
    })

    test('provider matrix shows provider groups', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Providers' })).toBeVisible({ timeout: 10000 })
      await expect(page.getByText('LLM', { exact: true })).toBeVisible()
      await expect(page.getByText('Images', { exact: true })).toBeVisible()
      await expect(page.getByText('Audio', { exact: true })).toBeVisible()
      await expect(page.getByText('API Keys', { exact: true })).toBeVisible()
    })

    test('provider matrix shows API key badges', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Providers' })).toBeVisible({ timeout: 10000 })
      await expect(page.getByText('API Keys', { exact: true })).toBeVisible()
    })
  })

  test.describe('Existing project', () => {
    test('loads existing project brief data', async ({ page }) => {
      await page.goto(`/projects/${EXISTING_PROJECT}/brief`)
      const banner = page.getByRole('banner')
      await expect(banner.getByRole('heading', { name: 'Brief Studio' })).toBeVisible()
      // Should show project name in subtitle
      await expect(banner.getByText(EXISTING_PROJECT, { exact: true }).last()).toBeVisible()

      await expect(page.locator('button[type="submit"]:has-text("F#@K it, we\'re doing it live!!")')).toBeVisible()
      await expect(page.getByRole('button', { name: 'Rebuild Storyboard' })).toBeVisible()
    })

    test('style reference upload uses multipart form data', async ({ page }) => {
      await page.goto(`/projects/${EXISTING_PROJECT}/brief`)
      await expect(page.getByRole('heading', { name: 'Providers' })).toBeVisible({ timeout: 10000 })

      await page.route(`**/api/projects/${EXISTING_PROJECT}/style-refs`, async (route) => {
        const contentType = route.request().headers()['content-type'] ?? ''
        expect(contentType).toContain('multipart/form-data')
        expect(contentType).not.toContain('application/json')

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            meta: {
              brief: {
                style_reference_paths: [`projects/${EXISTING_PROJECT}/style_refs/style_ref_01.png`],
                style_reference_summary: 'Reference summary from upload test',
              },
            },
            scenes: [],
          }),
        })
      })

      await page.evaluate(() => {
        const file = new File([new Uint8Array([137, 80, 78, 71])], 'style-ref.png', { type: 'image/png' })
        const input = document.querySelector('input[type="file"]') as HTMLInputElement | null
        if (!input) {
          throw new Error('Style reference input not found')
        }
        const dataTransfer = new DataTransfer()
        dataTransfer.items.add(file)
        input.files = dataTransfer.files
        input.dispatchEvent(new Event('change', { bubbles: true }))
      })

      await expect(page.locator('text=Reference summary from upload test')).toBeVisible()
    })

    test('brief browse buttons open real file choosers', async ({ page }) => {
      await page.goto(`/projects/${EXISTING_PROJECT}/brief`)
      await expect(page.getByRole('heading', { name: 'Style References', exact: true })).toBeVisible()

      const [styleChooser] = await Promise.all([
        page.waitForEvent('filechooser'),
        page.getByRole('button', { name: 'Browse style refs' }).click(),
      ])
      expect(styleChooser.isMultiple()).toBe(true)

      const [footageChooser] = await Promise.all([
        page.waitForEvent('filechooser'),
        page.getByRole('button', { name: 'Browse footage' }).click(),
      ])
      expect(footageChooser.isMultiple()).toBe(true)
    })

    test('footage upload uses multipart form data', async ({ page }) => {
      await page.goto(`/projects/${EXISTING_PROJECT}/brief`)
      await expect(page.getByRole('heading', { name: 'Footage Library' })).toBeVisible()

      await page.route(`**/api/projects/${EXISTING_PROJECT}/footage`, async (route) => {
        const contentType = route.request().headers()['content-type'] ?? ''
        expect(contentType).toContain('multipart/form-data')
        expect(contentType).not.toContain('application/json')

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            meta: {
              brief: {
                footage_manifest: [
                  {
                    id: 'footage_01',
                    label: 'Demo Clip',
                    kind: 'video_clip',
                    review_status: 'accept',
                    path: `projects/${EXISTING_PROJECT}/clips/footage_01.mp4`,
                  },
                ],
                available_footage: 'Demo Clip: uploaded through the footage panel',
              },
            },
            scenes: [],
          }),
        })
      })

      await page.evaluate(() => {
        const file = new File([new Uint8Array([0, 0, 0, 24])], 'demo-clip.mp4', { type: 'video/mp4' })
        const inputs = Array.from(document.querySelectorAll('input[type="file"]')) as HTMLInputElement[]
        const input = inputs[1]
        if (!input) {
          throw new Error('Footage input not found')
        }
        const dataTransfer = new DataTransfer()
        dataTransfer.items.add(file)
        input.files = dataTransfer.files
        input.dispatchEvent(new Event('change', { bubbles: true }))
      })

      await expect(page.getByText('Demo Clip', { exact: true })).toBeVisible()
      await expect(page.getByText('Demo Clip: uploaded through the footage panel')).toBeVisible()
    })
  })

  test('breadcrumb Projects link navigates back', async ({ page }) => {
    await page.goto('/projects/new/brief')
    await expect(page.getByRole('heading', { name: 'Brief Studio' })).toBeVisible()

    const projectsLink = page.getByRole('banner').getByRole('navigation', { name: 'Breadcrumb' }).getByRole('link', { name: 'Projects' })
    await projectsLink.click()
    await page.waitForURL('**/projects')
    await expect(page).toHaveURL(/\/projects/)
  })
})
