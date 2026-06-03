import type { ImageActionHistoryEntry } from './schemas/plan'

export function formatImageActionLabel(action: string): string {
  const value = String(action || '').replace(/_/g, ' ')
  return value ? value.replace(/\b\w/g, (char) => char.toUpperCase()) : 'Image action'
}

export function formatImageActionSummary(entry: ImageActionHistoryEntry): string {
  if (entry.error) return entry.error
  const scene = entry.scene_title || (entry.scene_index ? `Scene ${entry.scene_index}` : 'Scene')
  return `${scene} ${entry.status || 'updated'}`
}

export function formatImageActionTime(value: string | undefined): string {
  if (!value) return ''
  const date = new Date(value)
  if (!Number.isFinite(date.valueOf())) return value
  return date.toLocaleString()
}

export function imageActionStatusClass(status: string): string {
  if (status === 'succeeded') return 'text-[var(--signal-success)]'
  if (status === 'error' || status === 'failed') return 'text-[var(--signal-danger)]'
  return 'text-[var(--text-tertiary)]'
}
