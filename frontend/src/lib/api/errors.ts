import { ApiError, ApiNetworkError } from './client.ts'

export function getApiErrorMessage(error: unknown, fallback = 'Something went wrong.'): string {
  if (error instanceof ApiNetworkError) {
    return error.message
  }

  if (error instanceof ApiError) {
    const body = error.body
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail?: unknown }).detail
      if (typeof detail === 'string' && detail.trim()) {
        return detail
      }
    }
    if (body && typeof body === 'object') {
      if ('message' in body && typeof (body as { message?: unknown }).message === 'string') {
        const message = String((body as { message?: unknown }).message).trim()
        const operatorHint = 'operatorHint' in body && typeof (body as { operatorHint?: unknown }).operatorHint === 'string'
          ? String((body as { operatorHint?: unknown }).operatorHint).trim()
          : ''
        return operatorHint ? `${message}\n${operatorHint}` : message
      }
      if ('operatorHint' in body && typeof (body as { operatorHint?: unknown }).operatorHint === 'string') {
        const hint = String((body as { operatorHint?: unknown }).operatorHint).trim()
        if (hint) {
          return hint
        }
      }
    }

    return `${error.status} ${error.statusText}`
  }

  if (error instanceof Error && error.message.trim()) {
    if (/failed to fetch|load failed/i.test(error.message)) {
      return 'Could not reach the Cathode API. Make sure the server is running and try again.'
    }
    return error.message
  }

  return fallback
}
