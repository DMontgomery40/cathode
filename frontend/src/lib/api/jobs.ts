export type JobStatus = 'queued' | 'running' | 'succeeded' | 'partial_success' | 'failed' | 'cancelled' | 'error'

export type JobStepStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped' | 'cancelled'

export type JobStepCategory =
  | 'setup'
  | 'storyboard'
  | 'plan'
  | 'budget'
  | 'assets'
  | 'render'
  | 'compress'
  | 'review'
  | 'demo'
  | 'cleanup'

export interface JobStep {
  id: string
  label: string
  category: JobStepCategory
  status: JobStepStatus
  detail?: string | null
  error?: string | null
  hint?: string | null
  scene_id?: string | null
  scene_uid?: string | null
  artifact_path?: string | null
  created_utc?: string | null
  started_utc?: string | null
  completed_utc?: string | null
  duration_ms?: number | null
}

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
  // Render backend metadata may be returned either at result.* or nested
  // under result.render.* depending on the job path; use getRenderBackendMeta.
  result?: Record<string, unknown>
  error?: { operatorHint?: string; message?: string } | string | null
  progress?: number | null
  progress_kind?: string
  progress_label?: string
  progress_detail?: string
  progress_scene_id?: number | null
  progress_scene_uid?: string | null
  progress_status?: string
  steps?: JobStep[]
}

export function jobStatusLabel(status: JobStatus | string | null | undefined): string {
  switch (status) {
    case 'queued': return 'Queued'
    case 'running': return 'Running'
    case 'succeeded': return 'Completed'
    case 'partial_success': return 'Partial'
    case 'failed': return 'Failed'
    case 'cancelled': return 'Cancelled'
    case 'error': return 'Error'
    default: return 'Unknown'
  }
}

export function jobStatusEmptyLabel(status: JobStatus | 'all' | 'active' | string): string {
  if (status === 'all') return 'No jobs yet'
  if (status === 'active') return 'No active jobs'
  return `No ${jobStatusLabel(status).toLowerCase()} jobs`
}

export interface JobLog {
  job_id: string
  project_name: string
  log_path: string
  tail_lines: number
  line_count: number
  content: string
}

type RenderBackendRecord = {
  render_backend_warning?: unknown
  render_backend_used?: unknown
  render?: unknown
}

function stringOrNull(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null
}

function asRenderBackendRecord(value: unknown): RenderBackendRecord | null {
  return value && typeof value === 'object' ? value as RenderBackendRecord : null
}

export function getRenderBackendMeta(result: Job['result']): { warning: string | null; used: string | null } {
  const root = asRenderBackendRecord(result)
  const nested = asRenderBackendRecord(root?.render)

  return {
    warning: stringOrNull(root?.render_backend_warning) ?? stringOrNull(nested?.render_backend_warning),
    used: stringOrNull(root?.render_backend_used) ?? stringOrNull(nested?.render_backend_used),
  }
}
