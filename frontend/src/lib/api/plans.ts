import { apiFetch } from './client.ts'
import type { Plan } from '../schemas/plan.ts'

export function fetchPlan(project: string): Promise<Plan> {
  return apiFetch<Plan>(`/projects/${encodeURIComponent(project)}/plan`)
}

export function savePlan(project: string, plan: Plan): Promise<Plan> {
  return apiFetch<Plan>(`/projects/${encodeURIComponent(project)}/plan`, {
    method: 'PUT',
    body: JSON.stringify(plan),
  })
}

export function rebuildStoryboard(
  project: string,
  payload?: { provider?: string; brief?: Record<string, unknown>; agent_demo_profile?: Record<string, unknown> },
): Promise<Plan> {
  return apiFetch<Plan>(`/projects/${encodeURIComponent(project)}/storyboard`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  })
}

export function fetchRemotionManifest(project: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/projects/${encodeURIComponent(project)}/remotion-manifest`)
}
