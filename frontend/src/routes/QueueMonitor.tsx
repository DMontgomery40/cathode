import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { clsx } from 'clsx'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader.tsx'
import { ProjectWorkspaceNav } from '../components/composed/ProjectWorkspaceNav.tsx'
import { JobCard } from '../features/jobs/JobCard.tsx'
import { usePlan } from '../lib/api/hooks.ts'
import { useProjectJobs, useCancelJob } from '../lib/api/scene-hooks.ts'
import { jobStatusEmptyLabel, type Job, type JobStatus } from '../lib/api/jobs.ts'
import { WorkspaceCanvas, WorkspaceEmptyState, WorkspaceGrid, WorkspacePanel } from '../design-system/recipes'

type FilterValue = 'all' | JobStatus

// ---- Staleness threshold: a running job not updated in 5+ minutes is considered stuck ----
const STALE_THRESHOLD_MS = 5 * 60 * 1000

/** Derive a compact step summary for a running job without importing StepChecklist. */
function deriveStepSummary(job: Job): { done: number; total: number; currentLabel: string | null } {
  const steps = job.steps ?? []
  if (steps.length === 0) {
    return { done: 0, total: 0, currentLabel: job.progress_label ?? null }
  }
  const done = steps.filter((s) => s.status === 'succeeded' || s.status === 'skipped').length
  const running = steps.find((s) => s.status === 'running')
  const lastFailed = [...steps].reverse().find((s) => s.status === 'failed')
  return {
    done,
    total: steps.length,
    currentLabel: running?.label ?? lastFailed?.label ?? job.progress_label ?? null,
  }
}

/** True if a running job has any failed step. */
function hasFailedStep(job: Job): boolean {
  return (job.steps ?? []).some((s) => s.status === 'failed')
}

/** True if a running job's updated_utc is older than STALE_THRESHOLD_MS. */
function isStale(job: Job): boolean {
  if (!job.updated_utc) return false
  const updatedAt = new Date(job.updated_utc).getTime()
  return Date.now() - updatedAt > STALE_THRESHOLD_MS
}

/** A small inline chip used to flag anomalous job states. */
function WarningChip({ label }: { label: string }) {
  return (
    <span
      className="inline-flex items-center rounded-[var(--radius-full)] border border-[rgba(200,122,78,0.35)] bg-[rgba(200,122,78,0.12)] text-[var(--signal-warning)] shrink-0"
      style={{ fontSize: '10px', fontWeight: 'var(--weight-medium)', padding: '1px 6px', lineHeight: 1.4 }}
      aria-label={label}
    >
      {label}
    </span>
  )
}

/** Overview row for a single active (queued|running) job. */
function ActiveJobOverviewRow({ job }: { job: Job }) {
  const { done, total, currentLabel } = deriveStepSummary(job)
  const hasFailed = hasFailedStep(job)
  const stale = isStale(job)
  const shortId = job.job_id.length > 10 ? job.job_id.slice(0, 10) + '…' : job.job_id
  const prettyStage = job.requested_stage || job.current_stage || job.kind || ''

  return (
    <li
      className="flex items-center gap-[var(--space-3)] border-b border-[var(--border-subtle)] last:border-b-0"
      style={{ paddingTop: 'var(--space-2)', paddingBottom: 'var(--space-2)' }}
    >
      {/* Status dot */}
      <span
        className={clsx(
          'inline-block rounded-full shrink-0',
          job.status === 'running' ? 'bg-[var(--signal-active)] animate-pulse' : 'bg-[var(--signal-warning)]',
        )}
        style={{ width: 7, height: 7 }}
        aria-hidden="true"
      />

      {/* Short job id */}
      <span
        className="text-[var(--text-tertiary)] font-[family-name:var(--font-mono)] shrink-0"
        style={{ fontSize: '10px' }}
      >
        {shortId}
      </span>

      {/* Stage/kind */}
      {prettyStage && (
        <span
          className="text-[var(--text-tertiary)] shrink-0"
          style={{ fontSize: 'var(--text-xs)' }}
        >
          {prettyStage}
        </span>
      )}

      {/* Step progress */}
      {total > 0 ? (
        <span
          className="text-[var(--text-secondary)] font-[family-name:var(--font-mono)] shrink-0"
          style={{ fontSize: 'var(--text-xs)' }}
        >
          {done}/{total}
        </span>
      ) : null}

      {/* Current step label */}
      {currentLabel && (
        <span
          className={clsx(
            'truncate',
            hasFailed && job.status !== 'running'
              ? 'text-[var(--signal-danger)]'
              : 'text-[var(--text-tertiary)]',
          )}
          style={{ fontSize: 'var(--text-xs)' }}
        >
          {currentLabel}
        </span>
      )}

      {/* Warning chips pushed to the right */}
      <span className="ml-auto flex items-center gap-[var(--space-1)] shrink-0">
        {hasFailed && <WarningChip label="step failed" />}
        {stale && <WarningChip label="stuck?" />}
      </span>
    </li>
  )
}

/** Compact "Active jobs" overview block shown above the job list when there are running jobs. */
function ActiveJobsOverview({ jobs }: { jobs: Job[] }) {
  if (jobs.length === 0) return null

  return (
    <div
      className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)]"
      style={{ marginBottom: 'var(--space-4)' }}
      aria-label="Active jobs overview"
      role="region"
    >
      {/* Header */}
      <div
        className="flex items-center gap-[var(--space-2)] border-b border-[var(--border-subtle)]"
        style={{ padding: 'var(--space-2) var(--space-3)' }}
      >
        <span
          className="inline-block rounded-full bg-[var(--signal-active)] animate-pulse shrink-0"
          style={{ width: 6, height: 6 }}
          aria-hidden="true"
        />
        <span
          className="text-[var(--text-secondary)]"
          style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}
        >
          Active jobs
        </span>
        <span
          className="text-[var(--text-tertiary)]"
          style={{ fontSize: 'var(--text-xs)' }}
        >
          {jobs.length}
        </span>
      </div>

      {/* Rows */}
      <ul
        role="list"
        style={{ margin: 0, padding: `0 var(--space-3)`, listStyle: 'none' }}
        aria-label="Running job step summaries"
      >
        {jobs.map((job) => (
          <ActiveJobOverviewRow key={job.job_id} job={job} />
        ))}
      </ul>
    </div>
  )
}

/** Warning chip shown inline in the job list for stuck or step-failed running jobs. */
function JobListWarningChips({ job }: { job: Job }) {
  const hasFailed = hasFailedStep(job)
  const stale = isStale(job)
  if (!hasFailed && !stale) return null

  return (
    <span className="flex items-center gap-[var(--space-1)]" aria-live="polite">
      {hasFailed && <WarningChip label="step failed" />}
      {stale && <WarningChip label="stuck?" />}
    </span>
  )
}

export function QueueMonitor() {
  const { projectId = '' } = useParams<{ projectId: string }>()
  const { data: plan } = usePlan(projectId)
  const { data: jobs, isLoading } = useProjectJobs(projectId, { refetchInterval: 3000 })
  const cancelJobMut = useCancelJob()
  const [filter, setFilter] = useState<FilterValue>('all')

  const allJobs = jobs ?? []
  const filtered = filter === 'all'
    ? allJobs
    : allJobs.filter((j) => j.status === filter)

  const filters: { label: string; value: FilterValue }[] = [
    { label: 'All', value: 'all' },
    { label: 'Queued', value: 'queued' },
    { label: 'Running', value: 'running' },
    { label: 'Completed', value: 'succeeded' },
    { label: 'Partial', value: 'partial_success' },
    { label: 'Failed', value: 'failed' },
    { label: 'Cancelled', value: 'cancelled' },
  ]

  const activeJobs = allJobs.filter(
    (j) => j.status === 'queued' || j.status === 'running',
  )
  const activeCount = activeJobs.length
  const queuedCount = allJobs.filter((j) => j.status === 'queued').length
  const runningCount = allJobs.filter((j) => j.status === 'running').length
  const completedCount = allJobs.filter((j) => j.status === 'succeeded').length
  const partialCount = allJobs.filter((j) => j.status === 'partial_success').length
  const failedCount = allJobs.filter((j) => j.status === 'failed').length
  const cancelledCount = allJobs.filter((j) => j.status === 'cancelled').length

  return (
    <div className="flex flex-col h-full">
      <WorkspaceHeader
        title="Queue"
        subtitle={activeCount > 0 ? `${activeCount} active` : undefined}
        breadcrumbs={
          projectId
            ? [
                { label: 'Projects', href: '/projects' },
                { label: projectId, href: `/projects/${projectId}/scenes` },
                { label: 'Queue' },
              ]
            : [{ label: 'Queue' }]
        }
        status={activeCount > 0 ? 'generating' : 'idle'}
      />
      {projectId && <ProjectWorkspaceNav projectId={projectId} plan={plan} />}
      <WorkspaceCanvas>
        <WorkspaceGrid
          asideWidth={320}
          main={(
            <WorkspacePanel
              title="Job stream"
              eyebrow="Execution log"
              copy="Filter the current project's background work without leaving the production context."
            >
              {/* Active jobs overview — only visible when there are running/queued jobs */}
              <ActiveJobsOverview jobs={activeJobs} />

              <div className="flex items-center gap-[var(--space-2)]" style={{ marginBottom: 'var(--space-4)' }}>
                {filters.map((f) => (
                  <button
                    key={f.value}
                    onClick={() => setFilter(f.value)}
                    className={clsx(
                      'rounded-[var(--radius-md)] border cursor-pointer outline-none',
                      'focus-visible:shadow-[var(--focus-ring)]',
                      'transition-colors duration-[150ms]',
                      filter === f.value
                        ? 'border-[var(--border-accent)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]'
                        : 'border-[var(--border-subtle)] bg-transparent text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]',
                    )}
                    style={{
                      padding: `var(--space-1) var(--space-3)`,
                      fontSize: 'var(--text-xs)',
                      fontWeight: 'var(--weight-medium)',
                    }}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              <div className="flex flex-col gap-[var(--space-3)]" style={{ maxWidth: 720 }}>
                {isLoading && (
                  <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-sm)' }}>
                    Loading jobs...
                  </span>
                )}

                {!isLoading && filtered.length === 0 && (
                  <WorkspaceEmptyState
                    title={jobStatusEmptyLabel(filter)}
                    copy="Once generation or rendering starts, the queue will keep the full local trail here."
                    icon={(
                      <svg
                        width="32"
                        height="32"
                        viewBox="0 0 32 32"
                        fill="none"
                        stroke="var(--text-tertiary)"
                        strokeWidth="1.5"
                      >
                        <rect x="4" y="4" width="24" height="8" rx="2" />
                        <rect x="4" y="14" width="24" height="8" rx="2" />
                        <rect x="4" y="24" width="14" height="4" rx="2" />
                      </svg>
                    )}
                  />
                )}

                {filtered.map((job) => (
                  <div key={job.job_id} className="flex flex-col gap-[var(--space-1)]">
                    {/* Per-list-item warning chips for running jobs with issues */}
                    {(job.status === 'queued' || job.status === 'running') && (
                      <JobListWarningChips job={job} />
                    )}
                    <JobCard
                      job={job}
                      onCancel={
                        job.status === 'queued' || job.status === 'running'
                          ? () => cancelJobMut.mutate({ jobId: job.job_id, project: projectId })
                          : undefined
                      }
                    />
                  </div>
                ))}
              </div>
            </WorkspacePanel>
          )}
          aside={(
            <div className="workspace-panel-stack">
              <WorkspacePanel
                title="Job health"
                eyebrow="Status"
                copy="Use this rail to understand whether the project is still generating, cleaning up, or ready for the next move."
              >
                <div className="workspace-kpi-grid">
                  <div>
                    <p className="workspace-eyebrow">Total</p>
                    <div className="workspace-panel-title text-[var(--text-3xl)]">{allJobs.length}</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Queued</p>
                    <div className="workspace-panel-title text-[var(--text-3xl)]">{queuedCount}</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Running</p>
                    <div className="workspace-panel-title text-[var(--text-3xl)]">{runningCount}</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Completed</p>
                    <div className="workspace-panel-title text-[var(--text-3xl)]">{completedCount}</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Partial</p>
                    <div className="workspace-panel-title text-[var(--text-3xl)]">{partialCount}</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Failed</p>
                    <div className="workspace-panel-title text-[var(--text-3xl)]">{failedCount}</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Cancelled</p>
                    <div className="workspace-panel-title text-[var(--text-3xl)]">{cancelledCount}</div>
                  </div>
                </div>
              </WorkspacePanel>
            </div>
          )}
        />
      </WorkspaceCanvas>
    </div>
  )
}
