import { z } from 'zod'

export const TextRenderModeSchema = z.enum(['visual_authored', 'deterministic_overlay'])
export type TextRenderMode = z.infer<typeof TextRenderModeSchema>

export const BriefSchema = z.object({
  project_name: z.string().min(1, 'Project name is required'),
  source_mode: z.enum(['ideas_notes', 'source_text', 'final_script']),
  video_goal: z.string(),
  audience: z.string(),
  source_material: z.string(),
  target_length_minutes: z.number().positive(),
  tone: z.string(),
  visual_style: z.string(),
  must_include: z.string(),
  must_avoid: z.string(),
  ending_cta: z.string(),
  paid_media_budget_usd: z.string(),
  composition_mode: z.enum(['auto', 'classic', 'motion_only', 'hybrid']),
  visual_source_strategy: z.enum(['images_only', 'mixed_media', 'video_preferred']),
  video_scene_style: z.enum(['auto', 'cinematic', 'speaking', 'mixed']),
  text_render_mode: TextRenderModeSchema,
})

export type Brief = z.infer<typeof BriefSchema>

export interface ThreeDataStagePoint {
  x: string
  y?: number | null
  label?: string
}

export interface ThreeDataStageSeries {
  id?: string
  label?: string
  type?: 'bar' | 'line' | string
  points?: ThreeDataStagePoint[]
}

export interface ThreeDataStageReferenceBand {
  id?: string
  label?: string
  yMin?: number | null
  yMax?: number | null
  xRange?: [string, string] | string[] | null
}

export interface ThreeDataStageCallout {
  id?: string
  label?: string
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
  referenceBands: ThreeDataStageReferenceBand[]
}

export interface ThreeDataStageCompositionData extends Record<string, unknown> {
  xAxisLabel?: string
  yAxisLabel?: string
  data_points?: string[]
  series?: ThreeDataStageSeries[]
  referenceBands?: ThreeDataStageReferenceBand[]
  callouts?: ThreeDataStageCallout[]
  panels?: ThreeDataStagePanel[]
}

export interface SceneComposition {
  family?: string
  mode?: 'none' | 'overlay' | 'native' | string
  props?: Record<string, unknown>
  transition_after?: {
    kind?: string
    duration_in_frames?: number
  } | null
  data?: ThreeDataStageCompositionData | Record<string, unknown> | unknown[] | null
  render_path?: string | null
  render_exists?: boolean
  preview_path?: string | null
  preview_exists?: boolean
  rationale?: string
}

export interface Scene {
  id?: number
  uid: string
  title?: string
  scene_type?: 'image' | 'video' | 'motion'
  visual_prompt?: string
  narration?: string
  speaker_name?: string
  staging_notes?: string | null
  data_points?: string[]
  transition_hint?: 'fade' | 'wipe' | string | null
  tts_override_enabled?: boolean
  tts_provider?: string | null
  tts_voice?: string | null
  tts_speed?: number | null
  elevenlabs_model_id?: string | null
  elevenlabs_text_normalization?: string | null
  elevenlabs_stability?: number | null
  elevenlabs_similarity_boost?: number | null
  elevenlabs_style?: number | null
  elevenlabs_use_speaker_boost?: boolean | null
  video_scene_kind?: 'cinematic' | 'speaking' | string | null
  on_screen_text?: string[]
  image_path?: string | null
  image_exists?: boolean
  video_path?: string | null
  video_exists?: boolean
  video_audio_exists?: boolean
  audio_path?: string | null
  audio_exists?: boolean
  preview_path?: string | null
  preview_exists?: boolean
  duration?: number | null
  video_trim_start?: number
  video_trim_end?: number | null
  video_playback_speed?: number
  video_hold_last_frame?: boolean
  video_audio_source?: 'clip' | 'narration' | string
  video_reference_image_path?: string | null
  video_reference_audio_path?: string | null
  composition?: SceneComposition | null
  motion?: {
    template_id?: string
    props?: {
      headline?: string
      body?: string
      kicker?: string
      bullets?: string[]
      accent?: string
      [key: string]: unknown
    }
    render_path?: string | null
    render_exists?: boolean
    preview_path?: string | null
    preview_exists?: boolean
    rationale?: string
  } | null
}

export interface ImageActionHistoryEntry {
  action?: string
  status?: string
  scene_uid?: string
  scene_index?: number
  scene_title?: string
  request?: Record<string, unknown>
  result?: Record<string, unknown>
  error?: string | null
  happened_at?: string
}

export interface PlanMeta {
  project_name?: string
  brief?: Record<string, unknown>
  render_profile?: Record<string, unknown>
  image_profile?: Record<string, unknown>
  image_action_history?: ImageActionHistoryEntry[]
  tts_profile?: Record<string, unknown>
  video_profile?: Record<string, unknown>
  video_path?: string | null
  video_exists?: boolean
  [key: string]: unknown
}

export interface Plan {
  meta: PlanMeta
  scenes: Scene[]
}
