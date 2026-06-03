export function resolveRenderOutputFilename({
  videoPath,
  projectName,
  projectId,
}: {
  videoPath?: string | null
  projectName?: string | null
  projectId?: string | null
}): string {
  const raw = String(videoPath || '').trim().replace(/\\/g, '/')
  if (raw) {
    const filename = raw.split('/').pop()
    if (filename && filename.endsWith('.mp4')) {
      return filename
    }
  }
  const project = String(projectName || projectId || 'video').trim() || 'video'
  return `${project}.mp4`
}
