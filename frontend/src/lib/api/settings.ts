import { apiFetch } from './client.ts'

export interface ProvidersInfo {
  api_keys: Record<string, boolean>
  llm_provider: string
  image_providers: string[]
  video_providers: string[]
  tts_providers: Record<string, string>
  image_edit_models: string[]
}

export function fetchProviders(): Promise<ProvidersInfo> {
  return apiFetch<ProvidersInfo>('/providers')
}
