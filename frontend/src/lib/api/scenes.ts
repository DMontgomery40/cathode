import { apiFetch } from './client.ts'
import type { Plan } from '../schemas/plan.ts'

export function uploadSceneImage(
  project: string,
  sceneUid: string,
  file: File,
): Promise<Plan> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch<Plan>(
    `/projects/${encodeURIComponent(project)}/scenes/${encodeURIComponent(sceneUid)}/image-upload`,
    { method: 'POST', body: form, headers: {} },
  )
}

export function uploadSceneVideo(
  project: string,
  sceneUid: string,
  file: File,
): Promise<Plan> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch<Plan>(
    `/projects/${encodeURIComponent(project)}/scenes/${encodeURIComponent(sceneUid)}/video-upload`,
    { method: 'POST', body: form, headers: {} },
  )
}

export function generateSceneImage(
  project: string,
  sceneUid: string,
  opts?: { provider?: string; model?: string },
): Promise<Plan> {
  return apiFetch<Plan>(
    `/projects/${encodeURIComponent(project)}/scenes/${encodeURIComponent(sceneUid)}/image-generate`,
    { method: 'POST', body: JSON.stringify(opts ?? {}) },
  )
}

export function generateSceneVideo(
  project: string,
  sceneUid: string,
  opts?: { provider?: string; model?: string; model_selection_mode?: string; quality_mode?: string; generate_audio?: boolean },
): Promise<Plan> {
  return apiFetch<Plan>(
    `/projects/${encodeURIComponent(project)}/scenes/${encodeURIComponent(sceneUid)}/video-generate`,
    { method: 'POST', body: JSON.stringify(opts ?? {}) },
  )
}

export function editSceneImage(
  project: string,
  sceneUid: string,
  feedback: string,
  opts?: { model?: string },
): Promise<Plan> {
  return apiFetch<Plan>(
    `/projects/${encodeURIComponent(project)}/scenes/${encodeURIComponent(sceneUid)}/image-edit`,
    { method: 'POST', body: JSON.stringify({ feedback, ...opts }) },
  )
}

export function generateSceneAudio(
  project: string,
  sceneUid: string,
  opts?: { tts_provider?: string; voice?: string; speed?: number },
): Promise<Plan> {
  return apiFetch<Plan>(
    `/projects/${encodeURIComponent(project)}/scenes/${encodeURIComponent(sceneUid)}/audio-generate`,
    { method: 'POST', body: JSON.stringify(opts ?? {}) },
  )
}

export function refinePrompt(
  project: string,
  sceneUid: string,
  feedback: string,
  provider?: string,
): Promise<Plan> {
  return apiFetch<Plan>(
    `/projects/${encodeURIComponent(project)}/scenes/${encodeURIComponent(sceneUid)}/prompt-refine`,
    { method: 'POST', body: JSON.stringify({ feedback, provider }) },
  )
}

export function refineNarration(
  project: string,
  sceneUid: string,
  feedback: string,
  provider?: string,
): Promise<Plan> {
  return apiFetch<Plan>(
    `/projects/${encodeURIComponent(project)}/scenes/${encodeURIComponent(sceneUid)}/narration-refine`,
    { method: 'POST', body: JSON.stringify({ feedback, provider }) },
  )
}

export function generateScenePreview(
  project: string,
  sceneUid: string,
): Promise<Plan> {
  return apiFetch<Plan>(
    `/projects/${encodeURIComponent(project)}/scenes/${encodeURIComponent(sceneUid)}/preview`,
    { method: 'POST' },
  )
}

export function fetchSceneRemotionManifest(
  project: string,
  sceneUid: string,
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/projects/${encodeURIComponent(project)}/scenes/${encodeURIComponent(sceneUid)}/remotion-manifest`,
  )
}
