import { ApiError } from './client'

export function getApiErrorMessage(error: unknown, fallback = 'Request failed.'): string {
  if (error instanceof ApiError) {
    return error.operatorHint ? `${error.message} ${error.operatorHint}` : error.message
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message
  }
  if (typeof error === 'string' && error.trim()) {
    return error
  }
  return fallback
}
