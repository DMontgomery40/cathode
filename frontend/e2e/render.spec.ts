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

  test('output filename input defaults to the project name', async ({ page }) => {
    const input = page.locator('#output-filename')
    await expect(input).toBeVisible()
    await expect(input).toHaveValue(`${PROJECT}.mp4`)
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

  test('static media manifests keep authored visuals without generic overlay chrome or pan', async ({ page }) => {
    const backgroundImage = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="1664" height="928" viewBox="0 0 1664 928"><rect width="1664" height="928" fill="#0f1524"/><circle cx="540" cy="420" r="210" fill="#ffb66b" fill-opacity="0.28"/><rect x="240" y="250" width="460" height="310" rx="44" fill="#f0a357" fill-opacity="0.18"/><rect x="960" y="220" width="140" height="140" rx="28" fill="#f4d8a0" fill-opacity="0.22"/><rect x="960" y="420" width="180" height="32" rx="16" fill="#f4d8a0" fill-opacity="0.18"/><rect x="960" y="520" width="180" height="32" rx="16" fill="#f4d8a0" fill-opacity="0.18"/></svg>',
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
              uid: 'static-media-scene',
              sceneType: 'image',
              title: 'Clinical Follow-up Still',
              narration: 'Plan a follow-up and keep reinforcing the gains.',
              onScreenText: [
                'Exact Authored Label',
                'Lifestyle panel copy',
              ],
              durationInFrames: 120,
              sequenceDurationInFrames: 120,
              imageUrl: backgroundImage,
              composition: {
                family: 'static_media',
                mode: 'none',
                props: {
                  headline: 'Exact Authored Label',
                  body: 'Lifestyle panel copy',
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
    const image = player.locator('img').first()
    await expect(image).toBeVisible()
    await expect(player.getByText('Exact Authored Label', { exact: true })).toHaveCount(0)
    await expect(player.getByText('Lifestyle panel copy', { exact: true })).toHaveCount(0)
    expect(await image.evaluate((node) => (node as HTMLElement).style.transform)).toBe('scale(1)')
  })

  test('structured data-stage manifests render stable chart labels from composition data', async ({ page }) => {
    await page.route(`**/api/projects/${PROJECT}/remotion-manifest`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          width: 1664,
          height: 928,
          fps: 24,
          textRenderMode: 'visual_authored',
          totalDurationInFrames: 120,
          scenes: [
            {
              uid: 'data-stage-scene',
              sceneType: 'image',
              title: 'Trail Making B: The Improvement',
              narration: 'Session one starts higher and session five ends lower.',
              onScreenText: [
                'Trail Making Test B',
                'Session 1: 75 sec -> Session 5: 63 sec',
                '12 seconds faster',
              ],
              durationInFrames: 120,
              sequenceDurationInFrames: 120,
              textLayerKind: 'none',
              composition: {
                family: 'three_data_stage',
                mode: 'native',
                props: {
                  headline: 'Trail Making Test B',
                  kicker: 'Trail Making B: The Improvement',
                  layoutVariant: 'bars_with_delta',
                  palette: 'teal_on_navy',
                },
                transitionAfter: null,
                rationale: '',
                data: {
                  xAxisLabel: 'Session',
                  yAxisLabel: 'Time (seconds)',
                  series: [
                    {
                      id: 'trail_making_b',
                      label: 'Trail Making Test B',
                      type: 'bar',
                      points: [
                        { x: 'Session 1', y: 75 },
                        { x: 'Session 2', y: null },
                        { x: 'Session 3', y: null },
                        { x: 'Session 4', y: null },
                        { x: 'Session 5', y: 63 },
                      ],
                    },
                  ],
                  referenceBands: [
                    {
                      id: 'trail_b_reference',
                      label: 'Reference range',
                      yMin: 0,
                      yMax: 120,
                    },
                  ],
                  callouts: [
                    {
                      id: 'delta',
                      fromX: 'Session 1',
                      toX: 'Session 5',
                      label: '12 seconds faster',
                    },
                  ],
                },
              },
            },
          ],
        }),
      })
    })

    await page.goto(`/projects/${PROJECT}/render`)
    const player = page.getByTestId('remotion-player-surface')
    await expect(player).toBeVisible()
    await expect(player.getByTestId('three-data-stage')).toBeVisible()
    await expect(player.getByText('Session 1', { exact: true })).toBeVisible()
    await expect(player.getByText('Session 5', { exact: true })).toBeVisible()
    await expect(player.getByText('Reference range', { exact: true })).toBeVisible()
    await expect(player.getByText('12 seconds faster', { exact: true }).first()).toBeVisible()
    await expect(player.getByText('n/a', { exact: true }).first()).toBeVisible()
    await expect(player.locator('[data-testid="three-data-stage-bar"]')).toHaveCount(2)
    const barHeights = await player.locator('[data-testid="three-data-stage-bar"]').evaluateAll((nodes) =>
      nodes.map((node) => Number(node.getAttribute('height') || '0')),
    )
    expect(Math.max(...barHeights)).toBeGreaterThan(40)
    const visibleBarBounds = await player.locator('[data-testid="three-data-stage-bar"]').evaluateAll((nodes) =>
      nodes.map((node) => {
        const rect = node.getBoundingClientRect()
        return { width: rect.width, height: rect.height }
      }),
    )
    expect(Math.max(...visibleBarBounds.map((bounds) => bounds.height))).toBeGreaterThan(40)
    expect(Math.max(...visibleBarBounds.map((bounds) => bounds.width))).toBeGreaterThan(20)
  })

  test('structured data-stage line charts draw visible geometry on the initial frame', async ({ page }) => {
    await page.route(`**/api/projects/${PROJECT}/remotion-manifest`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          width: 1664,
          height: 928,
          fps: 24,
          textRenderMode: 'visual_authored',
          totalDurationInFrames: 120,
          scenes: [
            {
              uid: 'data-stage-line-scene',
              sceneType: 'image',
              title: 'Alpha Ratio: Shifted Across Sessions',
              narration: 'The line crosses from above range to below range.',
              onScreenText: [
                'F3/F4 Alpha Ratio',
                'Session 1: 1.3 (above range)',
                'Sessions 4-5: 0.6-0.7 (below range)',
              ],
              durationInFrames: 120,
              sequenceDurationInFrames: 120,
              textLayerKind: 'none',
              composition: {
                family: 'three_data_stage',
                mode: 'native',
                props: {
                  headline: 'F3/F4 Alpha Ratio',
                  kicker: 'Alpha Ratio: Shifted Across Sessions',
                  layoutVariant: 'line_with_zones',
                  palette: 'multi_zone_on_charcoal',
                },
                transitionAfter: null,
                rationale: '',
                data: {
                  xAxisLabel: 'Session',
                  yAxisLabel: 'F3/F4 Alpha Ratio',
                  series: [
                    {
                      id: 'alpha_ratio',
                      label: 'F3/F4 Alpha Ratio',
                      type: 'line',
                      points: [
                        { x: 'Session 1', y: 1.3 },
                        { x: 'Session 2', y: 0.9 },
                        { x: 'Session 3', y: 1.0 },
                        { x: 'Session 4', y: 0.6 },
                        { x: 'Session 5', y: 0.7 },
                      ],
                    },
                  ],
                  referenceBands: [
                    {
                      id: 'alpha_ratio_reference',
                      label: 'In-range band',
                      yMin: 0.8,
                      yMax: 1.1,
                    },
                  ],
                  callouts: [
                    {
                      id: 'above_range',
                      x: 'Session 1',
                      y: 1.3,
                      label: 'Above range',
                    },
                  ],
                },
              },
            },
          ],
        }),
      })
    })

    await page.goto(`/projects/${PROJECT}/render`)
    const player = page.getByTestId('remotion-player-surface')
    await expect(player).toBeVisible()
    await expect(player.getByTestId('three-data-stage')).toBeVisible()
    await expect(player.getByText('Session 1', { exact: true })).toBeVisible()
    await expect(player.getByText('Session 5', { exact: true })).toBeVisible()
    await expect(player.getByText('In-range band', { exact: true })).toBeVisible()
    const linePath = player.locator('[data-testid="three-data-stage-line"]')
    await expect(linePath).toHaveCount(1)
    await expect(player.locator('[data-testid="three-data-stage-line-point"]')).toHaveCount(5)
    const lineDefinition = await linePath.getAttribute('d')
    expect(lineDefinition).toContain('L')
    const lineBounds = await linePath.evaluate((node) => {
      const rect = node.getBoundingClientRect()
      return { width: rect.width, height: rect.height }
    })
    expect(lineBounds.width).toBeGreaterThan(120)
    expect(lineBounds.height).toBeGreaterThan(20)
  })

  test('legacy null-valued data-stage bars recover visible geometry from comparison copy', async ({ page }) => {
    await page.route(`**/api/projects/${PROJECT}/remotion-manifest`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          width: 1664,
          height: 928,
          fps: 24,
          textRenderMode: 'visual_authored',
          totalDurationInFrames: 120,
          scenes: [
            {
              uid: 'legacy-null-bar-scene',
              sceneType: 'image',
              title: 'Simpler Tasks: A Mixed Picture',
              narration: 'Trail Making A slowed slightly but stayed in range.',
              onScreenText: [
                'Trail Making A: 33 -> 41 sec (still in range)',
                'Reaction time: 296 -> 293 ms',
                'Variability: +-43 -> +-69 ms',
              ],
              durationInFrames: 120,
              sequenceDurationInFrames: 120,
              textLayerKind: 'none',
              composition: {
                family: 'three_data_stage',
                mode: 'native',
                props: {
                  layoutVariant: 'bars_with_band',
                  palette: 'teal_on_navy',
                },
                transitionAfter: null,
                rationale: '',
                data: {
                  xAxisLabel: 'Category',
                  yAxisLabel: 'Value',
                  data_points: [
                    'Trail Making A: 33 -> 41 sec (still in range)',
                    'Reaction time: 296 -> 293 ms',
                    'Variability: +-43 -> +-69 ms',
                  ],
                  series: [
                    {
                      id: 'series_1',
                      label: 'Simpler Tasks: A Mixed Picture',
                      type: 'bar',
                      points: [
                        { x: 'Trail Making A: 33 -> 41 sec (still in range)', y: null },
                        { x: 'Reaction time: 296 -> 293 ms', y: null },
                        { x: 'Variability: +-43 -> +-69 ms', y: null },
                      ],
                    },
                  ],
                },
              },
            },
          ],
        }),
      })
    })

    await page.goto(`/projects/${PROJECT}/render`)
    const player = page.getByTestId('remotion-player-surface')
    await expect(player).toBeVisible()
    await expect(player.getByTestId('three-data-stage')).toBeVisible()
    await expect(player.getByText('Session 1', { exact: true })).toBeVisible()
    await expect(player.getByText('Session 2', { exact: true })).toBeVisible()
    await expect(player.locator('[data-testid="three-data-stage-bar"]')).toHaveCount(2)
    const recoveredBarHeights = await player.locator('[data-testid="three-data-stage-bar"]').evaluateAll((nodes) =>
      nodes.map((node) => Number(node.getAttribute('height') || '0')),
    )
    expect(Math.max(...recoveredBarHeights)).toBeGreaterThan(30)
  })

  test('legacy null-valued data-stage lines recover geometry and target bands from comparison copy', async ({ page }) => {
    await page.route(`**/api/projects/${PROJECT}/remotion-manifest`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          width: 1664,
          height: 928,
          fps: 24,
          textRenderMode: 'visual_authored',
          totalDurationInFrames: 120,
          scenes: [
            {
              uid: 'legacy-null-line-scene',
              sceneType: 'image',
              title: 'Background Rhythms: The Cautionary Signal',
              narration: 'Theta beta rose above the target range.',
              onScreenText: [
                'Theta/Beta Ratio: 2.0 -> 3.7',
                'Target: 0.9-2.1',
                'Low-yield flag - worth rechecking',
              ],
              durationInFrames: 120,
              sequenceDurationInFrames: 120,
              textLayerKind: 'none',
              composition: {
                family: 'three_data_stage',
                mode: 'native',
                props: {
                  layoutVariant: 'line_with_zones',
                  palette: 'multi_zone_on_charcoal',
                },
                transitionAfter: null,
                rationale: '',
                data: {
                  xAxisLabel: 'Category',
                  yAxisLabel: 'Value',
                  data_points: [
                    'Theta/Beta Ratio: 2.0 -> 3.7',
                    'Target: 0.9-2.1',
                    'Low-yield flag - worth rechecking',
                  ],
                  series: [
                    {
                      id: 'series_1',
                      label: 'Background Rhythms: The Cautionary Signal',
                      type: 'line',
                      points: [
                        { x: 'Theta/Beta Ratio: 2.0 -> 3.7', y: null },
                        { x: 'Target: 0.9-2.1', y: null },
                        { x: 'Low-yield flag - worth rechecking', y: null },
                      ],
                    },
                  ],
                },
              },
            },
          ],
        }),
      })
    })

    await page.goto(`/projects/${PROJECT}/render`)
    const player = page.getByTestId('remotion-player-surface')
    await expect(player).toBeVisible()
    await expect(player.getByTestId('three-data-stage')).toBeVisible()
    await expect(player.getByText('Session 1', { exact: true })).toBeVisible()
    await expect(player.getByText('Session 2', { exact: true })).toBeVisible()
    await expect(player.getByText('Target: 0.9-2.1', { exact: true }).first()).toBeVisible()
    const recoveredLine = player.locator('[data-testid="three-data-stage-line"]')
    await expect(recoveredLine).toHaveCount(1)
    await expect(player.locator('[data-testid="three-data-stage-line-point"]')).toHaveCount(2)
    const recoveredLineDefinition = await recoveredLine.getAttribute('d')
    const recoveredLineXValues = [...(recoveredLineDefinition ?? '').matchAll(/[ML]\s*([0-9.]+)\s+([0-9.]+)/g)]
      .map((match) => Number(match[1]))
    expect(Math.max(...recoveredLineXValues) - Math.min(...recoveredLineXValues)).toBeGreaterThan(650)
    const recoveredLineBounds = await recoveredLine.evaluate((node) => {
      const rect = node.getBoundingClientRect()
      return { height: rect.height }
    })
    expect(recoveredLineBounds.height).toBeGreaterThan(20)
  })

  test('legacy multi-comparison data-stage lines recover multiple visible series', async ({ page }) => {
    await page.route(`**/api/projects/${PROJECT}/remotion-manifest`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          width: 1664,
          height: 928,
          fps: 24,
          textRenderMode: 'visual_authored',
          totalDurationInFrames: 120,
          scenes: [
            {
              uid: 'legacy-null-multi-line-scene',
              sceneType: 'image',
              title: 'Connectivity: Your Brain Networks',
              narration: 'One pathway strengthened while another declined slightly.',
              onScreenText: [
                'CZ-PZ (midline): 0.51 -> 0.72 - Strengthened',
                'C3-C4 (left-right): 0.43 -> 0.36 - Mild decline',
              ],
              durationInFrames: 120,
              sequenceDurationInFrames: 120,
              textLayerKind: 'none',
              composition: {
                family: 'three_data_stage',
                mode: 'native',
                props: {
                  layoutVariant: 'line_with_band',
                  palette: 'teal_on_navy',
                },
                transitionAfter: null,
                rationale: '',
                data: {
                  xAxisLabel: 'Category',
                  yAxisLabel: 'Value',
                  data_points: [
                    'CZ-PZ (midline): 0.51 -> 0.72 - Strengthened',
                    'C3-C4 (left-right): 0.43 -> 0.36 - Mild decline',
                  ],
                  series: [
                    {
                      id: 'series_1',
                      label: 'Connectivity: Your Brain Networks',
                      type: 'line',
                      points: [
                        { x: 'CZ-PZ (midline): 0.51 -> 0.72 - Strengthened', y: null },
                        { x: 'C3-C4 (left-right): 0.43 -> 0.36 - Mild decline', y: null },
                      ],
                    },
                  ],
                },
              },
            },
          ],
        }),
      })
    })

    await page.goto(`/projects/${PROJECT}/render`)
    const player = page.getByTestId('remotion-player-surface')
    await expect(player).toBeVisible()
    await expect(player.getByTestId('three-data-stage')).toBeVisible()
    await expect(player.getByText('Session 1', { exact: true })).toBeVisible()
    await expect(player.getByText('Session 2', { exact: true })).toBeVisible()
    await expect(player.getByText('CZ-PZ (midline)', { exact: true }).first()).toBeVisible()
    await expect(player.getByText('C3-C4 (left-right)', { exact: true }).first()).toBeVisible()
    await expect(player.getByText('0.78', { exact: true })).toHaveCount(0)
    await expect(player.getByText('0.51', { exact: true }).first()).toBeVisible()
    await expect(player.getByText('0.72', { exact: true }).first()).toBeVisible()
    await expect(player.getByText('0.43', { exact: true }).first()).toBeVisible()
    await expect(player.getByText('0.36', { exact: true }).first()).toBeVisible()
    const recoveredLines = player.locator('[data-testid="three-data-stage-line"]')
    await expect(recoveredLines).toHaveCount(2)
    await expect(player.locator('[data-testid="three-data-stage-line-point"]')).toHaveCount(4)
    const recoveredLineSpans = await recoveredLines.evaluateAll((nodes) =>
      nodes.map((node) => {
        const definition = node.getAttribute('d') || ''
        const xValues = [...definition.matchAll(/[ML]\s*([0-9.]+)\s+([0-9.]+)/g)].map((match) => Number(match[1]))
        return Math.max(...xValues) - Math.min(...xValues)
      }),
    )
    expect(Math.min(...recoveredLineSpans)).toBeGreaterThan(650)
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
