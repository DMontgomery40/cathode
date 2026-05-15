function normalizePath(rawPath: string): string {
  return rawPath.replaceAll('\\', '/')
}

export function relativeProjectMediaPath(project: string, rawPath: string): string | null {
  const normalized = normalizePath(rawPath).replace(/^\/+/, '')
  const markers = [
    `projects/${project}/`,
    `/projects/${project}/`,
  ]

  for (const marker of markers) {
    const index = normalized.lastIndexOf(marker)
    if (index >= 0) {
      return normalized.slice(index + marker.length)
    }
  }

  if (normalized.startsWith('projects/')) {
    return null
  }

  if (rawPath.startsWith('/')) {
    return null
  }

  return normalized
}

export function hasProjectMediaPath(project: string, rawPath: string | null | undefined): boolean {
  if (!rawPath) {
    return false
  }
  return relativeProjectMediaPath(project, rawPath) !== null
}

export function projectMediaUrl(project: string, rawPath: string | null | undefined): string | null {
  if (!rawPath) {
    return null
  }
  const relativePath = relativeProjectMediaPath(project, rawPath)
  if (!relativePath) {
    return null
  }
  const encoded = relativePath
    .split('/')
    .filter(Boolean)
    .map((part) => encodeURIComponent(part))
    .join('/')
  return `/api/projects/${encodeURIComponent(project)}/media/${encoded}`
}
