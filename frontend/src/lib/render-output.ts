type RenderOutputNameArgs = {
  projectId?: string | null
  projectName?: string | null
  videoPath?: string | null
}

const DEFAULT_RENDER_OUTPUT_BASENAME = 'final_video'

function sanitizeRenderOutputStem(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) {
    return DEFAULT_RENDER_OUTPUT_BASENAME
  }

  const withoutExtension = trimmed.replace(/\.[A-Za-z0-9]+$/, '')
  const underscored = withoutExtension.replace(/\s+/g, '_')
  const cleaned = underscored.replace(/[^A-Za-z0-9_-]/g, '_')
  return cleaned || DEFAULT_RENDER_OUTPUT_BASENAME
}

export function resolveRenderOutputFilename({
  projectId,
  projectName,
  videoPath,
}: RenderOutputNameArgs): string {
  const existingFilename = typeof videoPath === 'string' && videoPath.trim()
    ? videoPath.split('/').pop()?.trim()
    : ''
  if (existingFilename) {
    return existingFilename
  }

  const stem = sanitizeRenderOutputStem(projectName || projectId || '')
  return `${stem}.mp4`
}
