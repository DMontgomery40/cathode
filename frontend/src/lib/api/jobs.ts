import { apiFetch } from './client.ts'

export type JobStatus = 'queued' | 'running' | 'succeeded' | 'partial_success' | 'failed' | 'cancelled' | 'error'

export interface JobLog {
  job_id: string
  project_name: string
  log_path: string
  tail_lines: number
  line_count: number
  content: string
}

export interface AgentDemoRequest {
  scene_uids?: string[]
  preferred_agent?: string
  workspace_path?: string
  app_url?: string
  launch_command?: string
  expected_url?: string
  run_until?: string
}

export interface MakeVideoJobRequest {
  project_name: string
  brief: Record<string, unknown>
  provider?: string | null
  image_profile?: Record<string, unknown> | null
  video_profile?: Record<string, unknown> | null
  agent_demo_profile?: Record<string, unknown> | null
  tts_profile?: Record<string, unknown> | null
  render_profile?: Record<string, unknown> | null
  overwrite?: boolean
  run_until?: string
}

export interface Job {
  job_id: string
  project_name: string
  project_dir: string
  kind?: string
  type?: string
  requested_stage: string
  current_stage: string
  status: JobStatus
  progress?: number
  pid?: number | null
  retryable?: boolean
  suggestion?: string
  request?: Record<string, unknown>
  result?: Record<string, unknown>
  error?: { message?: string; operatorHint?: string } | string | null
  progress_kind?: string
  progress_label?: string
  progress_detail?: string
  progress_scene_id?: number | null
  progress_scene_uid?: string | null
  progress_status?: string
  created_utc?: string
  updated_utc?: string
  log_path?: string
}

export function fetchProjectJobs(project: string): Promise<Job[]> {
  return apiFetch<Job[]>(
    `/projects/${encodeURIComponent(project)}/jobs`,
  )
}

export function dispatchAgentDemo(project: string, request: AgentDemoRequest): Promise<Job> {
  return apiFetch<Job>(
    `/projects/${encodeURIComponent(project)}/agent-demo`,
    { method: 'POST', body: JSON.stringify(request) },
  )
}

export function dispatchMakeVideo(request: MakeVideoJobRequest): Promise<Job> {
  return apiFetch<Job>(
    '/jobs/make-video',
    { method: 'POST', body: JSON.stringify(request) },
  )
}

export function fetchJobStatus(jobId: string, project?: string): Promise<Job> {
  const q = project ? `?project=${encodeURIComponent(project)}` : ''
  return apiFetch<Job>(`/jobs/${encodeURIComponent(jobId)}${q}`)
}

export function cancelJob(jobId: string, project?: string): Promise<Job> {
  const q = project ? `?project=${encodeURIComponent(project)}` : ''
  return apiFetch<Job>(`/jobs/${encodeURIComponent(jobId)}/cancel${q}`, {
    method: 'POST',
  })
}

export function fetchProjectJobLog(project: string, jobId: string, tailLines = 200): Promise<JobLog> {
  return apiFetch<JobLog>(
    `/projects/${encodeURIComponent(project)}/jobs/${encodeURIComponent(jobId)}/log?tail_lines=${encodeURIComponent(String(tailLines))}`,
  )
}
