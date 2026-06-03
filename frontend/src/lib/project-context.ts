const LAST_PROJECT_KEY = 'cathode:last-project-id'

export function readLastProjectId(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  return window.localStorage.getItem(LAST_PROJECT_KEY) ?? ''
}

export function writeLastProjectId(projectId: string) {
  if (typeof window === 'undefined' || !projectId.trim()) {
    return
  }
  window.localStorage.setItem(LAST_PROJECT_KEY, projectId.trim())
}
