const LAST_PROJECT_STORAGE_KEY = 'cathode-last-project'

export function readLastProjectId(): string {
  if (typeof window === 'undefined') return ''
  return window.localStorage.getItem(LAST_PROJECT_STORAGE_KEY) ?? ''
}

export function writeLastProjectId(projectId: string | null): void {
  if (typeof window === 'undefined') return
  if (!projectId) {
    window.localStorage.removeItem(LAST_PROJECT_STORAGE_KEY)
    return
  }
  window.localStorage.setItem(LAST_PROJECT_STORAGE_KEY, projectId)
}
