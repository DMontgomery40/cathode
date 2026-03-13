import fs from 'node:fs'
import path from 'node:path'
import { test, expect } from '@playwright/test'

import { cleanupProjectFixture, cloneProjectFixture } from './helpers/project-fixture'

const SOURCE_PROJECT = 'bet365_feature_act_01'
const DISPOSABLE_PROJECT = `e2e_settings_surface_${Date.now()}`
const JOB_ID = 'imgjob1234'
const CONTEXT_PROJECT = 'bet365_feature_act_02'

function repoRoot(): string {
  return path.resolve(process.cwd(), '..')
}

function disposableProjectDir(): string {
  return path.join(repoRoot(), 'projects', DISPOSABLE_PROJECT)
}

test.describe('Settings', () => {
  test.beforeAll(() => {
    cloneProjectFixture(SOURCE_PROJECT, DISPOSABLE_PROJECT)

    const projectDir = disposableProjectDir()
    const planPath = path.join(projectDir, 'plan.json')
    const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')) as {
      meta: Record<string, unknown>
      scenes: Array<{ uid: string; title?: string }>
    }
    const firstScene = plan.scenes[0]

    plan.meta = {
      ...plan.meta,
      image_profile: {
        ...(typeof plan.meta.image_profile === 'object' && plan.meta.image_profile ? plan.meta.image_profile : {}),
        edit_model: 'qwen-image-edit-plus',
        dashscope_edit_n: 3,
        dashscope_edit_seed: '17',
        dashscope_edit_negative_prompt: 'avoid extra labels',
        dashscope_edit_prompt_extend: false,
      },
      image_action_history: [
        {
          action: 'edit',
          status: 'error',
          scene_uid: firstScene.uid,
          scene_index: 1,
          scene_title: firstScene.title || 'Scene 1',
          request: {
            feedback: 'Remove the floating label and increase contrast',
            model: 'qwen-image-edit-plus',
            dashscope_edit_n: 3,
          },
          error: 'DashScope quota exceeded during retry window.',
          happened_at: '2026-03-12T20:15:00Z',
        },
        {
          action: 'generate',
          status: 'succeeded',
          scene_uid: firstScene.uid,
          scene_index: 1,
          scene_title: firstScene.title || 'Scene 1',
          request: {
            provider: 'replicate',
            model: 'qwen/qwen-image-2512',
          },
          result: {
            image_path: `projects/${DISPOSABLE_PROJECT}/images/scene_000.png`,
          },
          happened_at: '2026-03-12T20:05:00Z',
        },
      ],
    }
    fs.writeFileSync(planPath, `${JSON.stringify(plan, null, 2)}\n`, 'utf8')

    const jobsDir = path.join(projectDir, '.cathode', 'jobs')
    fs.mkdirSync(jobsDir, { recursive: true })
    const logPath = path.join(jobsDir, `${JOB_ID}.log`)
    fs.writeFileSync(logPath, 'generated image for scene_000\nedit retry queued\n', 'utf8')
    fs.writeFileSync(path.join(jobsDir, `${JOB_ID}.json`), `${JSON.stringify({
      job_id: JOB_ID,
      project_name: DISPOSABLE_PROJECT,
      project_dir: projectDir,
      requested_stage: 'assets',
      status: 'succeeded',
      current_stage: 'done',
      created_utc: '2026-03-12T20:00:00Z',
      updated_utc: '2026-03-12T20:10:00Z',
      pid: null,
      request: { kind: 'rerun_stage', stage: 'assets' },
      result: { current_stage: 'assets', retryable: false },
      error: null,
      suggestion: '',
      log_path: logPath,
    }, null, 2)}\n`, 'utf8')
  })

  test.afterAll(() => {
    cleanupProjectFixture(DISPOSABLE_PROJECT)
  })

  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await expect(page.getByRole('heading', { name: 'Settings', exact: true })).toBeVisible()
  })

  test('target project is selected from a top-level context panel', async ({ page }) => {
    await expect(page.getByText('Target project')).toBeVisible()
    await expect(page.getByLabel('Project')).toBeVisible()
    await expect(page.getByText('Editing context')).toBeVisible()
  })

  test('voice settings no longer hide the project selector inside the voice card', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Voice settings' })).toBeVisible()
    await expect(page.getByLabel('TTS Provider')).toBeVisible()
    await expect(page.getByLabel('Project')).toHaveCount(1)
    await expect(page.getByRole('heading', { name: 'Target project' })).toBeVisible()
  })

  test('image settings expose effective edit params and recent project image activity', async ({ page }) => {
    await page.getByLabel('Project').selectOption(DISPOSABLE_PROJECT)

    await expect(page.getByRole('heading', { name: 'Image profile' })).toBeVisible()
    await expect(page.getByText('Effective edit request')).toBeVisible()
    const effectiveEditRequest = page.locator('pre').filter({ hasText: '"backend": "DashScope-backed"' })
    await expect(effectiveEditRequest).toBeVisible()
    await expect(effectiveEditRequest).toContainText('"dashscope_edit_n": 3')
    await expect(page.getByRole('heading', { name: 'Image activity' })).toBeVisible()
    await expect(page.getByText('Recent scene image actions', { exact: true })).toBeVisible()
    await expect(page.getByText('Background image jobs', { exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Open Queue' })).toBeVisible()

    const activityEntry = page.locator('details').filter({ hasText: 'Image edit' }).first()
    await activityEntry.click()
    await expect(activityEntry.getByText('DashScope quota exceeded during retry window.')).toBeVisible()
  })

  test('background image job logs are expandable directly from settings', async ({ page }) => {
    await page.getByLabel('Project').selectOption(DISPOSABLE_PROJECT)

    await page.getByText(JOB_ID).click()
    await expect(page.getByText('generated image for scene_000')).toBeVisible()
    await expect(page.getByText('edit retry queued')).toBeVisible()
  })

  test('selected project persists after leaving settings and coming back', async ({ page }) => {
    await page.getByLabel('Project').selectOption(CONTEXT_PROJECT)

    await page.getByRole('menuitem', { name: 'Home' }).click()
    await expect(page).toHaveURL('http://127.0.0.1:9322/')

    await page.getByRole('menuitem', { name: 'Settings' }).click()
    await expect(page.getByLabel('Project')).toHaveValue(CONTEXT_PROJECT)

    await page.reload()
    await expect(page.getByLabel('Project')).toHaveValue(CONTEXT_PROJECT)
  })

  test('settings picks up the current project context from project routes', async ({ page }) => {
    await page.goto(`/projects/${CONTEXT_PROJECT}/scenes`)
    await expect(page.getByRole('heading', { name: 'Scenes' })).toBeVisible()

    await page.getByRole('menuitem', { name: 'Settings' }).click()
    await expect(page).toHaveURL(/\/settings$/)
    await expect(page.getByLabel('Project')).toHaveValue(CONTEXT_PROJECT)
  })
})
