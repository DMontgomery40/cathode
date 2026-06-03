interface ReplicateRouteInput {
  modelSelectionMode?: string
  generationModel?: string
  generateAudio?: boolean
  sceneKind?: string
}

export const DEFAULT_REPLICATE_CINEMATIC_VIDEO_MODEL = 'google/veo-3.1-fast'
export const DEFAULT_REPLICATE_SPEAKING_VIDEO_MODEL = 'google/veo-3.1'
export const CUSTOM_REPLICATE_VIDEO_MODEL = '__custom__'

export const REPLICATE_VIDEO_MODEL_OPTIONS = [
  { value: DEFAULT_REPLICATE_CINEMATIC_VIDEO_MODEL, label: 'Veo 3.1 Fast' },
  { value: DEFAULT_REPLICATE_SPEAKING_VIDEO_MODEL, label: 'Veo 3.1' },
  { value: 'minimax/video-01', label: 'Minimax Video 01' },
]

export function getReplicateVideoModelPreset(model: string | null | undefined): string {
  const value = String(model || '').trim()
  if (!value) return DEFAULT_REPLICATE_CINEMATIC_VIDEO_MODEL
  return REPLICATE_VIDEO_MODEL_OPTIONS.some((option) => option.value === value)
    ? value
    : CUSTOM_REPLICATE_VIDEO_MODEL
}

export function resolveReplicateVideoRoute(input: ReplicateRouteInput) {
  const configuredModel = String(input.generationModel || '').trim()
  const sceneKind = String(input.sceneKind || '').trim() || 'cinematic'
  const routeKind = input.generateAudio ? 'video_with_audio' : 'silent_video'
  const resolvedModel = configuredModel || (sceneKind === 'speaking' ? DEFAULT_REPLICATE_SPEAKING_VIDEO_MODEL : DEFAULT_REPLICATE_CINEMATIC_VIDEO_MODEL)
  return {
    routeKind,
    resolvedModel,
    reason: configuredModel
      ? 'Using the project configured Replicate model.'
      : `Automatic ${sceneKind} route selected from scene intent.`,
  }
}

export function replicateVideoRouteLabel(routeKind: string | null | undefined): string {
  if (routeKind === 'video_with_audio') return 'Video + generated clip audio'
  if (routeKind === 'silent_video') return 'Silent video clip'
  return 'Automatic video route'
}
