import { z } from 'zod'

export const BriefSchema = z.object({
  project_name: z.string().min(1, 'Project name is required'),
  source_mode: z.enum(['ideas_notes', 'source_text', 'final_script']),
  video_goal: z.string().default(''),
  audience: z.string().default(''),
  source_material: z.string().default(''),
  target_length_minutes: z.coerce.number().min(0.1).max(30),
  tone: z.string().default(''),
  visual_style: z.string().default(''),
  must_include: z.string().default(''),
  must_avoid: z.string().default(''),
  ending_cta: z.string().default(''),
  paid_media_budget_usd: z.string().default(''),
  composition_mode: z.enum(['auto', 'classic', 'motion_only', 'hybrid']),
  visual_source_strategy: z.enum(['images_only', 'mixed_media', 'video_preferred']),
  video_scene_style: z.enum(['auto', 'cinematic', 'speaking', 'mixed']),
  text_render_mode: z.enum(['visual_authored', 'deterministic_overlay']),
  available_footage: z.string().optional(),
  footage_manifest: z.array(z.record(z.string(), z.unknown())).optional(),
  style_reference_summary: z.string().optional(),
  style_reference_paths: z.array(z.string()).optional(),
  raw_brief: z.string().optional(),
  short_form_format: z.string().optional(),
  short_form_tier: z.string().optional(),
  short_form_approach: z.string().optional(),
  short_form_duration_seconds: z.number().optional(),
  platform_targets: z.array(z.string()).optional(),
  hook_promise: z.string().optional(),
  payoff: z.string().optional(),
  source_anchor_card: z.string().optional(),
  source_context_lock: z.string().optional(),
  caption_strategy: z.string().optional(),
  caption_timing_source: z.string().optional(),
  caption_renderer: z.string().optional(),
  voice_direction: z.string().optional(),
  motion_intensity: z.string().optional(),
}).passthrough()

export type Brief = z.infer<typeof BriefSchema>

export interface SceneComposition {
  family?: string | null
  mode?: string | null
  manifestation?: string | null
  props?: Record<string, unknown>
  transition_after?: unknown
  data?: Record<string, unknown>
  render_path?: string | null
  preview_path?: string | null
  rationale?: string | null
}

export interface SceneMotion {
  template_id?: string | null
  props?: Record<string, unknown>
  render_path?: string | null
  render_exists?: boolean
  preview_path?: string | null
  preview_exists?: boolean
  rationale?: string | null
}

export interface ThreeDataStagePoint {
  x: string
  y: number | null
  label?: string
}

export interface ThreeDataStageSeries {
  id: string
  label: string
  type: 'bar' | 'line'
  points: ThreeDataStagePoint[]
}

export interface ThreeDataStageReferenceBand {
  id: string
  label: string
  yMin?: number | null
  yMax?: number | null
  xRange?: [string, string]
}

export interface ThreeDataStageCallout {
  id: string
  label: string
  x?: string
  y?: number | null
  fromX?: string
  toX?: string
}

export interface ThreeDataStagePanel {
  id: string
  title: string
  yAxisLabel?: string
  series: ThreeDataStageSeries[]
  referenceBands?: ThreeDataStageReferenceBand[]
}

export interface ThreeDataStageCompositionData extends Record<string, unknown> {
  series: ThreeDataStageSeries[]
  data_points?: string[]
  referenceBands?: ThreeDataStageReferenceBand[]
  callouts?: ThreeDataStageCallout[]
  panels?: ThreeDataStagePanel[]
  xAxisLabel?: string
  yAxisLabel?: string
}

export interface Scene {
  uid: string
  id: number
  title: string
  narration: string
  visual_prompt: string
  scene_type: 'image' | 'video' | 'motion' | string
  on_screen_text: string[]
  image_path?: string | null
  image_exists?: boolean
  image_version?: number | null
  video_path?: string | null
  video_exists?: boolean
  video_version?: number | null
  audio_path?: string | null
  audio_exists?: boolean
  audio_version?: number | null
  preview_path?: string | null
  preview_exists?: boolean
  preview_version?: number | null
  video_audio_source?: string | null
  video_scene_kind?: string | null
  speaker_name?: string | null
  tts_override_enabled?: boolean
  tts_provider?: string | null
  tts_voice?: string | null
  tts_speed?: number | null
  composition?: SceneComposition | null
  motion?: SceneMotion | null
  manifestation_plan?: Record<string, unknown> | null
  [key: string]: unknown
}

export interface ImageActionHistoryEntry {
  action: string
  status: string
  scene_uid?: string
  scene_index?: number
  scene_title?: string
  request?: Record<string, unknown>
  result?: Record<string, unknown>
  error?: string | null
  happened_at?: string
}

export interface Plan {
  meta: Record<string, unknown> & {
    project_name?: string
    brief?: Record<string, unknown>
    render_profile?: Record<string, unknown>
    image_profile?: Record<string, unknown>
    video_profile?: Record<string, unknown>
    tts_profile?: Record<string, unknown>
    video_path?: string | null
    video_exists?: boolean
    video_version?: number | null
    cost_estimate?: Record<string, unknown>
    cost_actual?: Record<string, unknown>
    image_action_history?: ImageActionHistoryEntry[]
  }
  scenes: Scene[]
  [key: string]: unknown
}
