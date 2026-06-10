import { useState } from 'react'
import { clsx } from 'clsx'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { DetailGrid } from '../../components/composed/DetailGrid.tsx'
import { getRenderBackendMeta, jobStatusLabel, safeJobDetail, type Job } from '../../lib/api/jobs.ts'
import { useJobLog } from '../../lib/api/scene-hooks.ts'
import StepChecklist from './StepChecklist.tsx'

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

function stageLabel(value?: string): string {
  const raw = String(value || '').trim()
  if (!raw) return 'Job'
  const normalized = raw.replace(/[_-]+/g, ' ')
  return normalized.replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function errorMessage(error: Job['error']): string {
  if (!error) return ''
  if (typeof error === 'string') return safeJobDetail(error)
  return safeJobDetail(error.operatorHint || error.message || '')
}

function logLineCount(content?: string): number {
  return String(content || '')
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0)
    .length
}

export function JobCard({ job, project, onCancel }: JobCardProps) {
  const [expanded, setExpanded] = useState(false)
  const isActive = job.status === 'queued' || job.status === 'running'
  const log = useJobLog(project ?? job.project_name, expanded ? job.job_id : null, { enabled: expanded && Boolean(project || job.project_name) })
  const shortId = job.job_id.length > 12 ? job.job_id.slice(0, 12) + '...' : job.job_id
  const prettyStage = stageLabel(job.requested_stage || job.current_stage || job.kind)
  const prettyError = errorMessage(job.error)
  const renderBackend = getRenderBackendMeta(job.result)
  const renderEngineWarning = renderBackend.warning
    ? renderBackend.warning.replace(/\brender_backend\b/g, 'render engine').replace(/\bbackend\b/g, 'engine')
    : null

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
          {jobStatusLabel(job.status)}
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

      {/* Compact step summary — visible in collapsed view when steps are present */}
      {!expanded && (job.steps?.length ?? 0) > 0 && (
        <div style={{ marginTop: 'var(--space-2)' }}>
          <StepChecklist steps={job.steps ?? []} compact />
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
          {safeJobDetail(job.suggestion) && (
            <div className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
              {safeJobDetail(job.suggestion)}
            </div>
          )}

          {/* Remotion -> ffmpeg fallback warning */}
          {renderEngineWarning && (
            <div
              className="rounded-[var(--radius-md)] border border-[rgba(200,160,60,0.3)] bg-[rgba(200,160,60,0.08)] text-[var(--signal-warning)]"
              style={{ fontSize: 'var(--text-xs)', padding: 'var(--space-2) var(--space-3)' }}
              role="alert"
            >
              <span style={{ fontWeight: 'var(--weight-medium)' }}>Render engine:</span>{' '}
              {renderEngineWarning}
              {renderBackend.used && (
                <span className="text-[var(--text-tertiary)]">
                  {' '}(used: {renderBackend.used})
                </span>
              )}
            </div>
          )}

          {/* Full step checklist — primary state UI */}
          {(job.steps?.length ?? 0) > 0 && (
            <div style={{ marginTop: 'var(--space-1)', marginBottom: 'var(--space-2)' }}>
              <StepChecklist steps={job.steps ?? []} />
            </div>
          )}

          <DetailGrid
            columns={3}
            items={[
              { label: 'Stage', value: prettyStage, title: prettyStage },
              { label: 'Updated', value: formatTime(job.updated_utc) },
              { label: 'Reference', value: job.job_id, title: job.job_id },
            ]}
          />
          {log.data?.content && (
            <div
              className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] text-[var(--text-tertiary)]"
              style={{ fontSize: 'var(--text-xs)', padding: 'var(--space-2) var(--space-3)' }}
            >
              Worker diagnostics captured ({logLineCount(log.data.content)} lines).
            </div>
          )}
        </div>
      )}
    </GlassPanel>
  )
}
