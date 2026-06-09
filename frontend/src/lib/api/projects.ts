import type { JobStatus } from './jobs.ts'

export interface ProjectJobCounts {
  total: number
  queued: number
  running: number
  succeeded: number
  partial_success: number
  failed: number
  cancelled: number
  error: number
  active: number
}

export interface ProjectJobSummary {
  counts: ProjectJobCounts
  latest_status?: JobStatus | null
  latest_job_id?: string | null
  latest_requested_stage?: string | null
  latest_updated_utc?: string | null
}

export interface ProjectSummary {
  name: string
  scene_count: number
  has_video: boolean
  jobs?: ProjectJobSummary | null
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
