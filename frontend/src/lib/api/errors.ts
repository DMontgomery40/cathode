import { API_BASE, ApiError } from './client'

function apiOfflineMessage(): string {
  const target = API_BASE || 'http://127.0.0.1:9321'
  return `Could not reach the betTube Studio API at ${target}. Make sure the server is running and try again.`
}

export function getApiErrorMessage(error: unknown, fallback = 'Request failed.'): string {
  if (error instanceof ApiError) {
    return error.operatorHint ? `${error.message} ${error.operatorHint}` : error.message
  }
  if (error instanceof TypeError && /failed to fetch|networkerror|load failed/i.test(error.message)) {
    return apiOfflineMessage()
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message
  }
  if (typeof error === 'string' && error.trim()) {
    return error
  }
  return fallback
}
