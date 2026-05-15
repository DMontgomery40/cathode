const DEV_API_BASE = 'http://127.0.0.1:9321/api'
const BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? DEV_API_BASE : '/api')

export class ApiError extends Error {
  status: number
  statusText: string
  body: unknown

  constructor(status: number, statusText: string, body: unknown) {
    super(`API Error ${status}: ${statusText}`)
    this.name = 'ApiError'
    this.status = status
    this.statusText = statusText
    this.body = body
  }
}

export class ApiNetworkError extends Error {
  url: string
  cause: unknown

  constructor(url: string, cause: unknown) {
    const target = describeApiTarget(url)
    super(`Could not reach the Cathode API at ${target}. Make sure the server is running and try again.`)
    this.name = 'ApiNetworkError'
    this.url = url
    this.cause = cause
  }
}

function describeApiTarget(rawUrl: string): string {
  try {
    const resolved = new URL(rawUrl, window.location.origin)
    if (resolved.origin === window.location.origin) {
      return `${window.location.origin}/api`
    }
    return resolved.origin
  } catch {
    return rawUrl
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`
  const headers = new Headers(options.headers ?? {})
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData

  if (!headers.has('Content-Type') && !isFormData) {
    headers.set('Content-Type', 'application/json')
  }

  let res: Response
  try {
    res = await fetch(url, {
      headers,
      ...options,
    })
  } catch (error) {
    throw new ApiNetworkError(url, error)
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(res.status, res.statusText, body)
  }

  return res.json()
}
