import { apiFetch } from './client.ts'
import type { Job } from './jobs.ts'

export function startRender(
  project: string,
  opts?: { output_filename?: string; fps?: number },
): Promise<Job> {
  return apiFetch<Job>(
    `/projects/${encodeURIComponent(project)}/render`,
    { method: 'POST', body: JSON.stringify(opts ?? {}) },
  )
}

export function generateAssets(project: string): Promise<Job> {
  return apiFetch<Job>(
    `/projects/${encodeURIComponent(project)}/assets`,
    { method: 'POST' },
  )
}
