import type { Plan } from '../schemas/plan.ts'

const BASE_URL = '/api'

export interface StyleRefsResponse {
  style_reference_paths: string[]
  style_reference_summary: string
}

export async function uploadStyleRefs(project: string, files: File[]): Promise<Plan> {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  const res = await fetch(
    `${BASE_URL}/projects/${encodeURIComponent(project)}/style-refs`,
    { method: 'POST', body: form },
  )
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(`Upload failed: ${res.status} ${res.statusText} ${JSON.stringify(body)}`)
  }
  return res.json()
}

export function fetchStyleRefs(project: string): Promise<StyleRefsResponse> {
  const url = `${BASE_URL}/projects/${encodeURIComponent(project)}/style-refs`
  return fetch(url).then((r) => {
    if (!r.ok) throw new Error(`Fetch style refs failed: ${r.status}`)
    return r.json()
  })
}
