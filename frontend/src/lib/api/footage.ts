import { apiFetch } from './client.ts'
import type { Plan } from '../schemas/plan.ts'

export function uploadFootage(project: string, files: File[]): Promise<Plan> {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  return apiFetch<Plan>(
    `/projects/${encodeURIComponent(project)}/footage`,
    { method: 'POST', body: form, headers: {} },
  )
}
