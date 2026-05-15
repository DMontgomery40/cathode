import { apiFetch } from './client'

export interface BootstrapResponse {
  providers: {
    api_keys: Record<string, boolean>
    llm_provider: string | null
    image_providers: string[]
    video_providers: string[]
    render_backends: string[]
    remotion_available: boolean
    remotion_capabilities: Record<string, boolean>
    tts_providers: Record<string, string>
    tts_voice_options: Record<string, Array<{ value: string; label: string; description: string }>>
    image_edit_models: string[]
    cost_catalog: {
      version: string
      entries: Array<Record<string, unknown>>
      fx?: Record<string, number>
    }
  }
  defaults: {
    brief: Record<string, unknown>
    render_profile: Record<string, unknown>
    image_profile: Record<string, unknown>
    video_profile: Record<string, unknown>
    tts_profile: Record<string, unknown>
  }
  projects: string[]
}

export function fetchBootstrap(): Promise<BootstrapResponse> {
  return apiFetch<BootstrapResponse>('/bootstrap')
}
