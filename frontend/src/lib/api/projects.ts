import { apiFetch } from './client'

export interface ProjectSummary {
  name: string
  scene_count: number
  has_video: boolean
  video_path: string | null
  thumbnail_path: string | null
  created_utc: string | null
  updated_utc: string | null
  image_profile: Record<string, unknown> | null
  tts_profile: Record<string, unknown> | null
}

export function fetchProjects(): Promise<ProjectSummary[]> {
  return apiFetch<ProjectSummary[]>('/projects')
}

export function createProject(body: {
  project_name: string
  brief: Record<string, unknown>
  provider?: string | null
  image_profile?: Record<string, unknown> | null
  video_profile?: Record<string, unknown> | null
  agent_demo_profile?: Record<string, unknown> | null
  tts_profile?: Record<string, unknown> | null
  render_profile?: Record<string, unknown> | null
  overwrite?: boolean
}): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>('/projects', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
