export const DEFAULT_REPLICATE_CINEMATIC_VIDEO_MODEL = 'kwaivgi/kling-v3-video'
export const DEFAULT_REPLICATE_SPEAKING_VIDEO_MODEL = 'kwaivgi/kling-avatar-v2'
export const CUSTOM_REPLICATE_VIDEO_MODEL = '__custom__'

export const REPLICATE_VIDEO_MODEL_OPTIONS = [
  {
    value: DEFAULT_REPLICATE_CINEMATIC_VIDEO_MODEL,
    label: 'Kling 3 Video',
    description: 'Cinematic text-to-video clips with optional native audio.',
  },
  {
    value: DEFAULT_REPLICATE_SPEAKING_VIDEO_MODEL,
    label: 'Kling Avatar v2',
    description: 'Speaking/avatar clips driven by a portrait reference and dialogue audio.',
  },
] as const

export function getReplicateVideoModelPreset(model: string | null | undefined): string {
  const value = String(model || '').trim()
  if (!value) {
    return DEFAULT_REPLICATE_CINEMATIC_VIDEO_MODEL
  }
  return REPLICATE_VIDEO_MODEL_OPTIONS.some((option) => option.value === value)
    ? value
    : CUSTOM_REPLICATE_VIDEO_MODEL
}

export function resolveReplicateVideoRoute(params: {
  modelSelectionMode?: string | null
  generationModel?: string | null
  generateAudio?: boolean | null
  sceneKind?: string | null
}) {
  const selectionMode = String(params.modelSelectionMode || 'automatic').trim().toLowerCase()
  const explicitModel = String(params.generationModel || '').trim()
  const normalizedSelectionMode = selectionMode === 'advanced' ? 'advanced' : 'automatic'
  const sceneKind = String(params.sceneKind || '').trim().toLowerCase()

  if (normalizedSelectionMode === 'advanced' && explicitModel) {
    const routeKind = explicitModel.toLowerCase().includes('avatar') ? 'speaking' : 'cinematic'
    return {
      selectionMode: normalizedSelectionMode,
      resolvedModel: explicitModel,
      routeKind,
      reason: 'Advanced override',
    }
  }

  const autoPrefersSpeaking = Boolean(params.generateAudio) && sceneKind !== 'cinematic'
  if (autoPrefersSpeaking) {
    return {
      selectionMode: 'automatic',
      resolvedModel: DEFAULT_REPLICATE_SPEAKING_VIDEO_MODEL,
      routeKind: 'speaking',
      reason: 'Clip audio enabled, so Cathode uses the speaking-video lane.',
    }
  }

  return {
    selectionMode: 'automatic',
    resolvedModel: DEFAULT_REPLICATE_CINEMATIC_VIDEO_MODEL,
    routeKind: 'cinematic',
    reason: sceneKind === 'cinematic'
      ? 'Clip style is forcing the cinematic lane.'
      : 'Cathode uses the cinematic lane when clip audio is off.',
  }
}
