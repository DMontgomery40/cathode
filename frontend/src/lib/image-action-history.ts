import type { ImageActionHistoryEntry } from './schemas/plan.ts'

function truncate(value: string, max = 96): string {
  if (value.length <= max) return value
  return `${value.slice(0, max - 1)}…`
}

export function formatImageActionLabel(action: string | undefined): string {
  switch (action) {
    case 'upload':
      return 'Image upload'
    case 'generate':
      return 'Image generate'
    case 'edit':
      return 'Image edit'
    default:
      return 'Image action'
  }
}

export function formatImageActionTime(iso: string | undefined): string {
  if (!iso) return '--'
  const when = new Date(iso)
  if (Number.isNaN(when.valueOf())) return '--'
  return when.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function formatImageActionSummary(entry: ImageActionHistoryEntry): string {
  const request = entry.request ?? {}
  if (entry.action === 'upload') {
    const filename = String(request.filename || 'Uploaded file')
    const contentType = String(request.content_type || 'unknown')
    return `${truncate(filename)} • ${contentType}`
  }
  if (entry.action === 'generate') {
    const provider = String(request.provider || 'manual')
    const model = String(request.model || 'default')
    return `${provider} • ${truncate(model)}`
  }
  if (entry.action === 'edit') {
    const model = String(request.model || 'default')
    const feedback = String(request.feedback || '').trim()
    return feedback ? `${truncate(model)} • ${truncate(feedback, 72)}` : truncate(model)
  }
  return 'Recent image operation'
}

export function imageActionStatusClass(status: string | undefined): string {
  switch (status) {
    case 'error':
      return 'border-[rgba(200,90,90,0.3)] text-[var(--signal-danger)]'
    case 'succeeded':
      return 'border-[rgba(74,179,117,0.28)] text-[var(--signal-success)]'
    default:
      return 'border-[var(--border-subtle)] text-[var(--text-tertiary)]'
  }
}
