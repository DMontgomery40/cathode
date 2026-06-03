import { test, expect } from '@playwright/test'

test.describe('Short Form Studio', () => {
  test('previews and submits a vertical short-form job payload', async ({ page }) => {
    await page.route('**/api/short-form/options', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          tiers: [
            { value: 'dev-native-credible', label: 'Dev-native credible', description: 'Proof-first.' },
            { value: 'mass-native-technical', label: 'Mass-native technical', description: 'Cold-feed.' },
          ],
          approaches: [
            { value: 'public-reframe', label: 'Public reframe', description: 'Fresh vertical idea.' },
            { value: 'mixed-media-proof', label: 'Mixed-media proof', description: 'Source proof plus generated visuals.' },
            { value: 'source-cutdown', label: 'Source cutdown', description: 'Footage as spine.' },
          ],
          caption_strategies: [
            { value: 'meaning-card-captions', label: 'Meaning-card captions', description: 'Phrase cards.' },
            { value: 'word-level-highlight', label: 'Word-level highlight', description: 'Word timings required.' },
            { value: 'keyword-labels', label: 'Keyword labels', description: 'Sparse labels.' },
          ],
          platform_targets: [
            { value: 'tiktok', label: 'TikTok' },
            { value: 'instagram-reels', label: 'Instagram Reels' },
            { value: 'youtube-shorts', label: 'YouTube Shorts' },
          ],
          run_until: [
            { value: 'storyboard', label: 'Storyboard', description: 'Plan only.' },
            { value: 'assets', label: 'Assets', description: 'Generate assets.' },
            { value: 'render', label: 'Render', description: 'Final MP4.' },
          ],
          defaults: {
            short_form_tier: 'dev-native-credible',
            approach: 'public-reframe',
            caption_strategy: 'meaning-card-captions',
            platform_targets: ['tiktok', 'instagram-reels', 'youtube-shorts'],
            runtime_seconds: 42,
            run_until: 'storyboard',
            render_profile: { aspect_ratio: '9:16', width: 928, height: 1664, fps: 30 },
          },
        }),
      })
    })

    await page.goto('/short-form')
    await expect(page.getByRole('heading', { name: 'Short Form Studio' })).toBeVisible()

    await page.getByLabel('Project Name').fill('short_form_surface')
    await page.getByLabel('Source Material').fill('A longer technical demo about agent teams moving work through betTube Studio.')
    await page.getByLabel('Hook Promise').fill('This is what agent teams look like when they stop being slides.')
    await page.getByLabel('Payoff').fill('The viewer sees the operator handoff and the finished render path.')
    await page.getByLabel('Tier').selectOption('dev-native-credible')
    await page.getByLabel('Short Mode').selectOption('mixed-media-proof')
    await page.getByLabel('Caption Strategy').selectOption('meaning-card-captions')
    await page.getByLabel('Runtime').fill('45')
    await page.getByLabel('Subject').fill('betTube Studio')
    await page.getByLabel('Domain').fill('AI video tooling')
    await page.getByLabel('Evidence Boundary').fill('Prototype workflow evidence, not autonomous publishing proof.')

    await page.route('**/api/short-form/preview', async (route) => {
      const payload = route.request().postDataJSON() as Record<string, unknown>
      expect(payload.project_name).toBe('short_form_surface')
      expect(payload.runtime_seconds).toBe(45)
      expect(payload.approach).toBe('mixed-media-proof')
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          project_name: 'short_form_surface',
          run_until: 'storyboard',
          brief: {
            short_form_format: 'vertical_short',
            short_form_tier: 'dev-native-credible',
            short_form_approach: 'mixed-media-proof',
          },
          render_profile: {
            aspect_ratio: '9:16',
            width: 928,
            height: 1664,
            fps: 30,
          },
          preview: {
            frame: '9:16 928x1664 @ 30fps',
            pipeline: ['brief', 'director', 'normalized_plan', 'storyboard_stop', 'render_stop'],
            guardrails: ['one main idea', 'source-loyal visual prompts'],
          },
        }),
      })
    })

    await page.getByRole('button', { name: 'Preview Payload' }).click()
    await expect(page.getByText('9:16 928x1664 @ 30fps')).toBeVisible()
    await expect(page.getByText('"short_form_format": "vertical_short"')).toBeVisible()

    await page.route('**/api/short-form/jobs', async (route) => {
      const payload = route.request().postDataJSON() as Record<string, unknown>
      expect(payload.project_name).toBe('short_form_surface')
      expect(payload.run_until).toBe('storyboard')
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'queued',
          job_id: 'short-job-123',
          project_name: 'short_form_surface',
          project_dir: '/tmp/short_form_surface',
          kind: 'make_video',
          current_stage: 'queued',
          retryable: false,
          suggestion: '',
          requested_stage: 'storyboard',
          result: {},
          error: null,
        }),
      })
    })

    await page.getByRole('button', { name: 'Start Short' }).click()
    await page.waitForURL('**/projects/short_form_surface/queue')
  })
})
