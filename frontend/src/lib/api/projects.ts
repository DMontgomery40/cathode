export interface ProjectSummary {
  name: string
  scene_count: number
  has_video: boolean
  video_path?: string | null
  thumbnail_path?: string | null
  created_utc?: string | null
  updated_utc?: string | null
  image_profile?: Record<string, unknown> | null
  tts_profile?: Record<string, unknown> | null
  pipeline_mode?: string | null
  short_form_format?: string | null
  render_aspect_ratio?: string | null
}
