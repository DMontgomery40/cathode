export type JobStatus = 'queued' | 'running' | 'succeeded' | 'partial_success' | 'failed' | 'cancelled' | 'error'

export interface Job {
  status: JobStatus
  job_id: string
  project_name: string
  project_dir: string
  kind: string
  current_stage: string
  retryable: boolean
  suggestion: string
  requested_stage: string
  created_utc: string
  updated_utc: string
  pid?: number | null
  log_path?: string
  request?: Record<string, unknown>
  result?: Record<string, unknown>
  error?: { operatorHint?: string; message?: string } | string | null
  progress?: number | null
  progress_kind?: string
  progress_label?: string
  progress_detail?: string
  progress_scene_id?: number | null
  progress_scene_uid?: string | null
  progress_status?: string
}

export interface JobLog {
  job_id: string
  project_name: string
  log_path: string
  tail_lines: number
  line_count: number
  content: string
}
