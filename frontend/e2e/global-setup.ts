import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

type SceneFixture = Record<string, unknown>

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(__dirname, '../..')
const PROJECTS_ROOT = path.join(REPO_ROOT, 'projects')
const FIXTURE_PROJECTS = ['bet365_feature_act_01', 'bet365_feature_act_02', 'crucible_demo'] as const

function ensureDir(dir: string) {
  fs.mkdirSync(dir, { recursive: true })
}

function writeUtf8(filePath: string, content: string) {
  ensureDir(path.dirname(filePath))
  fs.writeFileSync(filePath, content, 'utf8')
}

function silentWavBuffer(seconds = 0.25, sampleRate = 8000): Buffer {
  const sampleCount = Math.floor(seconds * sampleRate)
  const dataSize = sampleCount * 2
  const buffer = Buffer.alloc(44 + dataSize)
  buffer.write('RIFF', 0)
  buffer.writeUInt32LE(36 + dataSize, 4)
  buffer.write('WAVE', 8)
  buffer.write('fmt ', 12)
  buffer.writeUInt32LE(16, 16)
  buffer.writeUInt16LE(1, 20)
  buffer.writeUInt16LE(1, 22)
  buffer.writeUInt32LE(sampleRate, 24)
  buffer.writeUInt32LE(sampleRate * 2, 28)
  buffer.writeUInt16LE(2, 32)
  buffer.writeUInt16LE(16, 34)
  buffer.write('data', 36)
  buffer.writeUInt32LE(dataSize, 40)
  return buffer
}

function writeSceneAssets(projectDir: string, projectName: string, index: number) {
  const sceneNumber = String(index + 1).padStart(2, '0')
  const imageName = `scene_${String(index).padStart(3, '0')}.svg`
  const hue = 150 + (index * 17) % 90
  writeUtf8(
    path.join(projectDir, 'images', imageName),
    `<svg xmlns="http://www.w3.org/2000/svg" width="1664" height="928" viewBox="0 0 1664 928">
  <rect width="1664" height="928" fill="#121212"/>
  <rect x="104" y="96" width="1456" height="736" rx="36" fill="#2d2d2d"/>
  <rect x="160" y="156" width="520" height="52" rx="26" fill="#126e51"/>
  <rect x="160" y="268" width="1050" height="38" rx="19" fill="hsl(${hue} 36% 54%)"/>
  <rect x="160" y="340" width="860" height="34" rx="17" fill="#e0e0e0" opacity=".22"/>
  <rect x="160" y="420" width="1180" height="220" rx="28" fill="#1c1c1c"/>
  <text x="190" y="195" fill="#fff" font-family="Inter, Arial, sans-serif" font-size="32" font-weight="700">${projectName}</text>
  <text x="190" y="510" fill="#fede1c" font-family="Inter, Arial, sans-serif" font-size="56" font-weight="700">Scene ${sceneNumber}</text>
</svg>
`,
  )
  ensureDir(path.join(projectDir, 'audio'))
  fs.writeFileSync(path.join(projectDir, 'audio', `scene_${String(index).padStart(3, '0')}.wav`), silentWavBuffer())
}

function brief(projectName: string): Record<string, unknown> {
  return {
    project_name: projectName,
    source_mode: 'source_text',
    video_goal: 'Explain a bet365 product workflow with clear operator proof.',
    audience: 'Internal product and engineering teams',
    source_material: 'A concise walkthrough of an in-progress bet365 feature workflow.',
    target_length_minutes: 3,
    tone: 'Calm, direct, product-led',
    visual_style: 'betTube dark workspace with green and yellow accents',
    must_include: 'Show the queue, scenes, and render workspaces.',
    must_avoid: 'Do not imply live customer data is present.',
    ending_cta: 'Review the project and ship the final render.',
    paid_media_budget_usd: '',
    composition_mode: 'hybrid',
    visual_source_strategy: 'images_only',
    video_scene_style: 'auto',
    text_render_mode: 'visual_authored',
    available_footage: '',
    footage_manifest: [],
    style_reference_summary: '',
    style_reference_paths: [],
    raw_brief: '',
    short_form_format: '',
    short_form_tier: '',
    short_form_approach: '',
    short_form_duration_seconds: 0,
    platform_targets: [],
    hook_promise: '',
    payoff: '',
    source_anchor_card: '',
    source_context_lock: '',
    caption_strategy: '',
    caption_timing_source: '',
    caption_renderer: '',
    voice_direction: '',
    motion_intensity: '',
  }
}

function scene(projectName: string, index: number): SceneFixture {
  const uid = `scene_${String(index).padStart(3, '0')}`
  const title = [
    'Opening queue signal',
    'Project intake',
    'Scene workspace',
    'Render handoff',
    'Settings context',
    'Provider controls',
    'Media review',
    'Budget guardrails',
    'Job history',
    'Ship-ready output',
  ][index] ?? `Scene ${index + 1}`

  return {
    id: index + 1,
    uid,
    title,
    narration: `${title} shows a clear betTube Studio production step.`,
    visual_prompt: `Create a polished betTube Studio production frame for ${title}.`,
    scene_type: 'image',
    on_screen_text: [title, `bet365 feature act ${index + 1}`],
    staging_notes: null,
    data_points: [],
    transition_hint: null,
    refinement_history: [],
    tts_override_enabled: false,
    tts_provider: null,
    tts_voice: null,
    tts_speed: null,
    image_path: `projects/${projectName}/images/scene_${String(index).padStart(3, '0')}.svg`,
    video_path: null,
    video_trim_start: 0,
    video_trim_end: null,
    video_playback_speed: 1,
    video_hold_last_frame: true,
    video_audio_source: 'narration',
    video_reference_image_path: null,
    video_reference_audio_path: null,
    audio_path: `projects/${projectName}/audio/scene_${String(index).padStart(3, '0')}.wav`,
    preview_path: null,
    composition: {
      family: 'media_pan',
      mode: 'none',
      manifestation: 'authored_image',
      props: {
        headline: title,
        body: `bet365 feature act ${index + 1}`,
      },
      transition_after: null,
      data: {},
      render_path: null,
      preview_path: null,
      rationale: 'Scene uses a composed media pan.',
    },
  }
}

function plan(projectName: string): Record<string, unknown> {
  return {
    meta: {
      project_name: projectName,
      created_utc: '2026-06-09T12:00:00Z',
      updated_utc: '2026-06-09T12:00:00Z',
      brief: brief(projectName),
      render_profile: {
        version: 'v1',
        aspect_ratio: '16:9',
        width: 1664,
        height: 928,
        fps: 24,
        scene_types: ['image', 'video', 'motion'],
        render_strategy: 'force_remotion',
        render_backend: 'remotion',
        render_backend_reason: 'Remotion forced by render_strategy=force_remotion.',
        text_render_mode: 'visual_authored',
      },
      video_path: null,
      footage_manifest: [],
      pipeline_mode: 'generic_slides_v1',
      image_profile: {
        provider: 'codex',
        generation_model: 'gpt-image-2',
        edit_model: 'gpt-image-2',
        dashscope_edit_n: 1,
        dashscope_edit_seed: '',
        dashscope_edit_negative_prompt: '',
        dashscope_edit_prompt_extend: true,
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
        speed: 1.1,
      },
      cost_actual: {
        version: '2026-03-14',
        currency: 'USD',
        total_usd: 0,
        entries: [],
      },
      cost_estimate: {
        version: '2026-03-14',
        currency: 'USD',
        total_usd: 0,
        entries: [],
        budget_usd: null,
        status: 'unbudgeted',
      },
    },
    scenes: Array.from({ length: 10 }, (_unused, index) => scene(projectName, index)),
  }
}

function ensureProject(projectName: string) {
  const projectDir = path.join(PROJECTS_ROOT, projectName)
  const planPath = path.join(projectDir, 'plan.json')
  if (fs.existsSync(planPath)) return

  ensureDir(projectDir)
  for (let index = 0; index < 10; index += 1) {
    writeSceneAssets(projectDir, projectName, index)
  }
  writeUtf8(planPath, `${JSON.stringify(plan(projectName), null, 2)}\n`)
}

export default async function globalSetup() {
  ensureDir(PROJECTS_ROOT)
  for (const projectName of FIXTURE_PROJECTS) {
    ensureProject(projectName)
  }
}
