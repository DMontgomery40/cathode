const LAST_PROJECT_KEY = 'bettube-studio:last-project-id'

export function readLastProjectId(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  return window.localStorage.getItem(LAST_PROJECT_KEY) ?? ''
}

export function writeLastProjectId(projectId: string) {
  if (typeof window === 'undefined') {
    return
  }
  if (!projectId.trim()) {
    window.localStorage.removeItem(LAST_PROJECT_KEY)
    return
  }
  window.localStorage.setItem(LAST_PROJECT_KEY, projectId.trim())
}
