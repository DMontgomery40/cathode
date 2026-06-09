import { clsx } from 'clsx'
import type { JobStep, JobStepCategory, JobStepStatus } from '../../lib/api/jobs.ts'

interface StepChecklistProps {
  steps: JobStep[]
  compact?: boolean
  className?: string
}

const CATEGORY_LABELS: Record<JobStepCategory, string> = {
  setup: 'Setup',
  storyboard: 'Storyboard',
  plan: 'Plan',
  budget: 'Budget',
  assets: 'Assets',
  render: 'Render',
  compress: 'Compress',
  review: 'Review',
  demo: 'Demo',
  cleanup: 'Cleanup',
}

/** Format a duration in milliseconds as "Xms" / "X.Xs" / "Xm Ys". */
function formatDuration(ms?: number | null): string {
  if (ms == null || !Number.isFinite(ms) || ms < 0) return ''
  if (ms < 1000) return `${Math.round(ms)}ms`
  const totalSeconds = ms / 1000
  if (totalSeconds < 60) {
    // One decimal for sub-minute durations, e.g. "2.3s"
    return `${totalSeconds.toFixed(1)}s`
  }
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = Math.round(totalSeconds % 60)
  // Zero-pad seconds, e.g. "1m 04s"
  return `${minutes}m ${String(seconds).padStart(2, '0')}s`
}

/** Color token for a step status (text color). */
function statusTextColor(status: JobStepStatus): string {
  switch (status) {
    case 'succeeded': return 'text-[var(--signal-success)]'
    case 'running': return 'text-[var(--accent-primary)]'
    case 'failed': return 'text-[var(--signal-danger)]'
    case 'skipped':
    case 'cancelled':
    case 'pending':
    default: return 'text-[var(--text-tertiary)]'
  }
}

/** Accessible label describing a step's status. */
function statusAriaLabel(status: JobStepStatus): string {
  switch (status) {
    case 'succeeded': return 'Succeeded'
    case 'running': return 'Running'
    case 'failed': return 'Failed'
    case 'skipped': return 'Skipped'
    case 'cancelled': return 'Cancelled'
    case 'pending':
    default: return 'Pending'
  }
}

/** Small status indicator glyph, colored by status. */
function StatusIndicator({ status }: { status: JobStepStatus }) {
  const base = 'inline-flex items-center justify-center shrink-0 select-none'
  const color = statusTextColor(status)

  if (status === 'succeeded') {
    return (
      <span
        className={clsx(base, color)}
        style={{ width: 14, height: 14, fontSize: '11px', lineHeight: 1 }}
        aria-hidden="true"
      >
        {/* check mark */}
        ✓
      </span>
    )
  }

  if (status === 'failed') {
    return (
      <span
        className={clsx(base, color)}
        style={{ width: 14, height: 14, fontSize: '11px', lineHeight: 1 }}
        aria-hidden="true"
      >
        {/* cross mark */}
        ✕
      </span>
    )
  }

  if (status === 'skipped' || status === 'cancelled') {
    return (
      <span
        className={clsx(base, color)}
        style={{ width: 14, height: 14, fontSize: '11px', lineHeight: 1 }}
        aria-hidden="true"
      >
        {/* dash glyph for skipped/cancelled */}
        –
      </span>
    )
  }

  if (status === 'running') {
    return (
      <span className={clsx(base)} style={{ width: 14, height: 14 }} aria-hidden="true">
        <span
          className="inline-block rounded-full bg-[var(--accent-primary)] animate-pulse"
          style={{ width: 8, height: 8 }}
        />
      </span>
    )
  }

  // pending: hollow/outline dot
  return (
    <span className={clsx(base)} style={{ width: 14, height: 14 }} aria-hidden="true">
      <span
        className="inline-block rounded-full border border-[var(--text-tertiary)]"
        style={{ width: 8, height: 8 }}
      />
    </span>
  )
}

/** A single dense step row. */
function StepRow({ step }: { step: JobStep }) {
  const duration = formatDuration(step.duration_ms)
  const isFailed = step.status === 'failed'
  const isMuted = step.status === 'skipped' || step.status === 'cancelled' || step.status === 'pending'

  return (
    <li
      className="flex flex-col gap-[var(--space-1)]"
      style={{ paddingTop: 'var(--space-1)', paddingBottom: 'var(--space-1)' }}
    >
      <div className="flex items-center gap-[var(--space-2)]">
        <StatusIndicator status={step.status} />
        <span className="sr-only">{statusAriaLabel(step.status)}:</span>

        <span
          className={clsx(
            'truncate',
            isMuted ? 'text-[var(--text-tertiary)]' : 'text-[var(--text-primary)]',
          )}
          style={{ fontSize: 'var(--text-sm)' }}
        >
          {step.label}
        </span>

        {step.detail && !isFailed && (
          <span
            className="text-[var(--text-tertiary)] truncate"
            style={{ fontSize: 'var(--text-xs)' }}
          >
            {step.detail}
          </span>
        )}

        {duration && (
          <span
            className="text-[var(--text-tertiary)] ml-auto shrink-0 font-[family-name:var(--font-mono)]"
            style={{ fontSize: '10px' }}
          >
            {duration}
          </span>
        )}
      </div>

      {isFailed && (step.error || step.hint || step.detail) && (
        <div
          className="flex flex-col gap-[2px] rounded-[var(--radius-md)] border border-[rgba(200,90,90,0.2)] bg-[rgba(200,90,90,0.08)]"
          style={{
            marginLeft: 'calc(14px + var(--space-2))',
            padding: 'var(--space-2) var(--space-3)',
          }}
        >
          {(step.error || step.detail) && (
            <span
              className="text-[var(--signal-danger)] font-[family-name:var(--font-mono)]"
              style={{ fontSize: 'var(--text-xs)' }}
            >
              {step.error || step.detail}
            </span>
          )}
          {step.hint && (
            <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
              {step.hint}
            </span>
          )}
        </div>
      )}
    </li>
  )
}

/** Subtle category header. */
function CategoryHeader({ category }: { category: JobStepCategory }) {
  return (
    <li
      className="text-[var(--text-tertiary)]"
      style={{
        fontSize: '10px',
        fontWeight: 'var(--weight-medium)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginTop: 'var(--space-2)',
        marginBottom: 'var(--space-1)',
      }}
      aria-hidden="true"
    >
      {CATEGORY_LABELS[category] ?? category}
    </li>
  )
}

const EMPTY_HINT = (
  <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
    No steps yet
  </span>
)

export default function StepChecklist({ steps, compact = false, className }: StepChecklistProps) {
  if (!steps || steps.length === 0) {
    return <div className={className}>{EMPTY_HINT}</div>
  }

  const total = steps.length
  const done = steps.filter((s) => s.status === 'succeeded' || s.status === 'skipped').length
  const running = steps.filter((s) => s.status === 'running')
  const failed = steps.filter((s) => s.status === 'failed')

  // ---- Compact mode ----
  if (compact) {
    const headline = running[0]?.label || failed[failed.length - 1]?.label || ''
    // Show only running + failed steps to keep the panel small, preserving original order.
    const visible = steps.filter((s) => s.status === 'running' || s.status === 'failed')

    return (
      <div
        className={clsx('flex flex-col gap-[var(--space-1)]', className)}
        role="group"
        aria-label="Job step summary"
      >
        <div className="flex items-baseline gap-[var(--space-2)]">
          <span
            className="text-[var(--text-secondary)] shrink-0 font-[family-name:var(--font-mono)]"
            style={{ fontSize: 'var(--text-xs)' }}
          >
            {done}/{total} steps
          </span>
          {headline && (
            <span
              className={clsx(
                'truncate',
                failed.length > 0 && running.length === 0
                  ? 'text-[var(--signal-danger)]'
                  : 'text-[var(--text-tertiary)]',
              )}
              style={{ fontSize: 'var(--text-xs)' }}
            >
              {headline}
            </span>
          )}
        </div>

        {visible.length > 0 && (
          <ul role="list" className="flex flex-col" style={{ margin: 0, padding: 0, listStyle: 'none' }}>
            {visible.map((step) => (
              <StepRow key={step.id} step={step} />
            ))}
          </ul>
        )}
      </div>
    )
  }

  // ---- Full mode ----
  // Group steps under category headers while preserving overall step order.
  // We walk steps in their given order and emit a header whenever the category changes.
  const rows: Array<{ kind: 'header'; category: JobStepCategory; key: string } | { kind: 'step'; step: JobStep }> = []
  let lastCategory: JobStepCategory | null = null
  for (const step of steps) {
    if (step.category !== lastCategory) {
      rows.push({ kind: 'header', category: step.category, key: `header-${step.category}-${step.id}` })
      lastCategory = step.category
    }
    rows.push({ kind: 'step', step })
  }

  return (
    <div className={className} role="group" aria-label="Job steps">
      <div className="sr-only" aria-live="polite">
        {done} of {total} steps complete
        {running[0] ? `, currently ${running[0].label}` : ''}
        {failed.length > 0 ? `, ${failed.length} failed` : ''}
      </div>
      <ul role="list" className="flex flex-col" style={{ margin: 0, padding: 0, listStyle: 'none' }}>
        {rows.map((row) =>
          row.kind === 'header' ? (
            <CategoryHeader key={row.key} category={row.category} />
          ) : (
            <StepRow key={row.step.id} step={row.step} />
          ),
        )}
      </ul>
    </div>
  )
}
