function projectRelativePath(project: string, rawPath: string): string | null {
  const value = rawPath.trim()
  if (!value) return null
  const normalized = value.replace(/\\/g, '/')
  const marker = `/projects/${project}/`
  const markerNoLead = `projects/${project}/`
  const absoluteIndex = normalized.lastIndexOf(marker)
  if (absoluteIndex >= 0) {
    return normalized.slice(absoluteIndex + marker.length)
  }
  const relativeIndex = normalized.lastIndexOf(markerNoLead)
  if (relativeIndex >= 0) {
    return normalized.slice(relativeIndex + markerNoLead.length)
  }
  if (normalized.startsWith('/')) {
    return null
  }
  return normalized.replace(/^\/+/, '')
}

export function projectMediaUrl(project: string, rawPath: unknown, version?: unknown): string | null {
  if (!project || typeof rawPath !== 'string') return null
  const relative = projectRelativePath(project, rawPath)
  if (!relative) return null
  const base = `/api/projects/${encodeURIComponent(project)}/media/${relative.split('/').map(encodeURIComponent).join('/')}`
  // Regenerated assets keep their filename; the version (server-reported file
  // mtime) busts the browser cache so players pick up the new bytes.
  return typeof version === 'number' && Number.isFinite(version) ? `${base}?v=${version}` : base
}

export function hasProjectMediaPath(project: string, rawPath: unknown): boolean {
  return Boolean(projectMediaUrl(project, rawPath))
}
