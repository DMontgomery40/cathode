import { useState } from 'react'
import { clsx } from 'clsx'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import type { Job } from '../../lib/api/jobs.ts'
import { useJobLog } from '../../lib/api/scene-hooks.ts'

interface JobCardProps {
  job: Job
  project?: string
  onCancel?: () => void
}

function statusColor(status: string): string {
  switch (status) {
    case 'running': return 'bg-[var(--signal-active)]'
    case 'succeeded': return 'bg-[var(--signal-success)]'
    case 'partial_success': return 'bg-[var(--signal-warning)]'
    case 'failed': return 'bg-[var(--signal-danger)]'
    case 'cancelled': return 'bg-[var(--text-tertiary)]'
    default: return 'bg-[var(--signal-warning)]'
  }
}

function formatTime(iso?: string): string {
  if (!iso) return '--'
  const d = new Date(iso)
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

function errorMessage(error: Job['error']): string {
  if (!error) return ''
  if (typeof error === 'string') return error
  return error.operatorHint || error.message || ''
}

export function JobCard({ job, project, onCancel }: JobCardProps) {
  const [expanded, setExpanded] = useState(false)
  const isActive = job.status === 'queued' || job.status === 'running'
  const log = useJobLog(project ?? job.project_name, expanded ? job.job_id : null, { enabled: expanded && Boolean(project || job.project_name) })
  const shortId = job.job_id.length > 12 ? job.job_id.slice(0, 12) + '...' : job.job_id
  const prettyStage = job.requested_stage || job.current_stage || job.kind || 'job'
  const prettyError = errorMessage(job.error)

  return (
    <GlassPanel variant="default" padding="sm">
      <div
        className="flex items-center gap-[var(--space-3)] cursor-pointer"
        onClick={() => setExpanded(!expanded)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setExpanded(!expanded)
          }
        }}
        aria-expanded={expanded}
      >
        <span className={clsx('inline-block rounded-full shrink-0', statusColor(job.status))} style={{ width: 8, height: 8 }} />

        <span
          className="text-[var(--text-secondary)] font-[family-name:var(--font-mono)] truncate"
          style={{ fontSize: 'var(--text-xs)' }}
        >
          {shortId}
        </span>

        {prettyStage && (
          <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
            {prettyStage}
          </span>
        )}

        <span className="text-[var(--text-tertiary)] ml-auto shrink-0" style={{ fontSize: 'var(--text-xs)' }}>
          {formatTime(job.created_utc)}
        </span>

        <span
          className={clsx(
            'rounded-[var(--radius-full)] border shrink-0',
            job.status === 'failed'
              ? 'text-[var(--signal-danger)] border-[rgba(200,90,90,0.3)]'
              : 'text-[var(--text-secondary)] border-[var(--border-subtle)]',
          )}
          style={{
            fontSize: '10px',
            padding: '1px 6px',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {job.status}
        </span>

        {isActive && onCancel && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onCancel()
            }}
            className="text-[var(--text-tertiary)] hover:text-[var(--signal-danger)] outline-none focus-visible:shadow-[var(--focus-ring)] rounded-[var(--radius-sm)] shrink-0"
            style={{ padding: 'var(--space-1)', fontSize: 'var(--text-xs)' }}
            aria-label="Cancel job"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Progress for running jobs */}
      {isActive && job.progress != null && (
        <div
          className="w-full rounded-[var(--radius-full)] bg-[var(--surface-stage)] overflow-hidden"
          style={{ height: 3, marginTop: 'var(--space-2)' }}
        >
          <div
            className="h-full bg-[var(--accent-primary)] transition-all duration-[250ms]"
            style={{ width: `${Math.max((job.progress ?? 0) * 100, 2)}%` }}
          />
        </div>
      )}

      {/* Expanded detail */}
      {expanded && (
        <div
          className="flex flex-col gap-[var(--space-1)] border-t border-[var(--border-subtle)]"
          style={{ marginTop: 'var(--space-2)', paddingTop: 'var(--space-2)' }}
        >
          {prettyError && (
            <div
              className="text-[var(--signal-danger)]"
              style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)' }}
            >
              {prettyError}
            </div>
          )}
          {job.suggestion && (
            <div className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
              {job.suggestion}
            </div>
          )}
          {job.request && Object.keys(job.request).length > 0 && (
            <pre
              className="text-[var(--text-tertiary)] overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)]"
              style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', margin: 0, padding: 'var(--space-2)' }}
            >
              {JSON.stringify(job.request, null, 2)}
            </pre>
          )}
          {job.result != null && (
            <pre
              className="text-[var(--text-tertiary)] overflow-x-auto"
              style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', margin: 0 }}
            >
              {JSON.stringify(job.result, null, 2)}
            </pre>
          )}
          <div className="text-[var(--text-tertiary)]" style={{ fontSize: '10px' }}>
            ID: {job.job_id}
          </div>
          <div className="text-[var(--text-tertiary)]" style={{ fontSize: '10px' }}>
            Updated: {formatTime(job.updated_utc)}
          </div>
          {log.data?.content && (
            <pre
              className="max-h-[16rem] overflow-auto rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-void)]"
              style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', margin: 0, padding: 'var(--space-2)' }}
            >
              {log.data.content}
            </pre>
          )}
        </div>
      )}
    </GlassPanel>
  )
}
