import { clsx } from 'clsx'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import type { Job } from '../../lib/api/jobs.ts'

interface RenderProgressProps {
  job: Job | null
  onCancel: () => void
}

function stageLabel(status: string): string {
  switch (status) {
    case 'queued': return 'Queued'
    case 'running': return 'Rendering'
    case 'succeeded': return 'Complete'
    case 'partial_success': return 'Partial'
    case 'failed': return 'Failed'
    case 'cancelled': return 'Cancelled'
    default: return status
  }
}

export function RenderProgress({ job, onCancel }: RenderProgressProps) {
  if (!job) {
    return (
      <GlassPanel variant="default" padding="md">
        <h3
          className="text-[var(--text-secondary)] m-0"
          style={{
            fontSize: 'var(--text-xs)',
            fontWeight: 'var(--weight-medium)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: 'var(--space-4)',
          }}
        >
          Render Progress
        </h3>
        <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-sm)' }}>
          No active render
        </span>
      </GlassPanel>
    )
  }

  const isActive = job.status === 'queued' || job.status === 'running'
  const isFailed = job.status === 'failed'
  const progress = job.progress ?? 0

  return (
    <GlassPanel variant="default" padding="md">
      <h3
        className="text-[var(--text-secondary)] m-0"
        style={{
          fontSize: 'var(--text-xs)',
          fontWeight: 'var(--weight-medium)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          marginBottom: 'var(--space-4)',
        }}
      >
        Render Progress
      </h3>

      <div className="flex flex-col gap-[var(--space-3)]">
        {/* Status badge */}
        <div className="flex items-center gap-[var(--space-2)]">
          <span
            className={clsx(
              'inline-block rounded-full',
              isActive && 'bg-[var(--signal-active)]',
              job.status === 'succeeded' && 'bg-[var(--signal-success)]',
              job.status === 'partial_success' && 'bg-[var(--signal-warning)]',
              isFailed && 'bg-[var(--signal-danger)]',
              job.status === 'cancelled' && 'bg-[var(--text-tertiary)]',
            )}
            style={{ width: 8, height: 8 }}
          />
          <span
            className={clsx(
              'font-[family-name:var(--font-mono)]',
              isFailed ? 'text-[var(--signal-danger)]' : 'text-[var(--text-primary)]',
            )}
            style={{ fontSize: 'var(--text-sm)' }}
          >
            {stageLabel(job.status)}
          </span>
          {(job.requested_stage || job.current_stage || job.type) && (
            <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
              ({job.requested_stage || job.current_stage || job.type})
            </span>
          )}
        </div>

        {/* Progress bar */}
        {isActive && (
          <div className="w-full rounded-[var(--radius-full)] bg-[var(--surface-stage)] overflow-hidden" style={{ height: 6 }}>
            <div
              className="h-full rounded-[var(--radius-full)] bg-[var(--accent-primary)] transition-all duration-[250ms]"
              style={{ width: `${Math.max(progress * 100, 2)}%` }}
              role="progressbar"
              aria-valuenow={Math.round(progress * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        )}

        {/* Error message */}
        {isFailed && job.error && (
          <div
            className="text-[var(--signal-danger)] bg-[rgba(200,90,90,0.08)] rounded-[var(--radius-md)] border border-[rgba(200,90,90,0.2)]"
            style={{
              fontSize: 'var(--text-xs)',
              padding: `var(--space-2) var(--space-3)`,
              fontFamily: 'var(--font-mono)',
            }}
          >
            {typeof job.error === 'string' ? job.error : job.error?.operatorHint || job.error?.message}
          </div>
        )}

        {/* Cancel button */}
        {isActive && (
          <button
            onClick={onCancel}
            className="self-start rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)] cursor-pointer outline-none focus-visible:shadow-[var(--focus-ring)]"
            style={{
              padding: `var(--space-2) var(--space-3)`,
              fontSize: 'var(--text-xs)',
              fontWeight: 'var(--weight-medium)',
            }}
          >
            Cancel
          </button>
        )}
      </div>
    </GlassPanel>
  )
}
