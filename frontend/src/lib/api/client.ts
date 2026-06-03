export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  detail: unknown
  operatorHint?: string

  constructor(message: string, status: number, detail: unknown, operatorHint?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.operatorHint = operatorHint
  }
}

function apiUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE}${normalized}`
}

async function parseResponse(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    return response.json()
  }
  return response.text()
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? value as Record<string, unknown> : null
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const hasBody = init.body != null
  if (hasBody && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(apiUrl(path), {
    ...init,
    headers,
  })
  const payload = await parseResponse(response)

  if (!response.ok) {
    const detail = payload && typeof payload === 'object' && 'detail' in payload
      ? (payload as Record<string, unknown>).detail
      : payload
    const detailRecord = recordValue(detail)
    const payloadRecord = recordValue(payload)
    const message = typeof detail === 'string'
      ? detail
      : typeof detailRecord?.message === 'string'
        ? String(detailRecord.message)
        : typeof payloadRecord?.message === 'string'
          ? String(payloadRecord.message)
          : `Request failed with HTTP ${response.status}.`
    const operatorHint = typeof payloadRecord?.operatorHint === 'string'
      ? String(payloadRecord.operatorHint)
      : typeof detailRecord?.operatorHint === 'string'
        ? String(detailRecord.operatorHint)
        : undefined
    throw new ApiError(message, response.status, detail, operatorHint)
  }

  return payload as T
}

export function jsonBody(value: unknown): string {
  return JSON.stringify(value)
}
