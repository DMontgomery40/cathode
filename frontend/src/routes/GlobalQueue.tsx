import { useState } from 'react'
import { clsx } from 'clsx'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader.tsx'
import { JobCard } from '../features/jobs/JobCard.tsx'
import { jobStatusEmptyLabel, type Job } from '../lib/api/jobs.ts'
import { useCancelJob } from '../lib/api/scene-hooks.ts'
import { isActiveJob, useGlobalQueueSummary } from '../lib/api/global-queue.ts'
import { WorkspaceCanvas, WorkspaceEmptyState, WorkspaceGrid, WorkspacePanel } from '../design-system/recipes'

type FilterValue = 'all' | 'active' | 'queued' | 'running' | 'succeeded' | 'partial_success' | 'failed' | 'cancelled'

function matchesFilter(job: Job, filter: FilterValue): boolean {
  if (filter === 'all') return true
  if (filter === 'active') return isActiveJob(job)
  return job.status === filter
}

export function GlobalQueue() {
  const [filter, setFilter] = useState<FilterValue>('all')
  const cancelJob = useCancelJob()
  const {
    projectNames,
    allJobs,
    jobsLoading,
    totalCount,
    activeCount,
    queuedCount,
    runningCount,
    completedCount,
    partialCount,
    failedCount,
    cancelledCount,
  } = useGlobalQueueSummary()

  const filteredJobs = allJobs.filter((job) => matchesFilter(job, filter))

  const filters: { label: string; value: FilterValue }[] = [
    { label: 'All', value: 'all' },
    { label: 'Active', value: 'active' },
    { label: 'Queued', value: 'queued' },
    { label: 'Running', value: 'running' },
    { label: 'Completed', value: 'succeeded' },
    { label: 'Partial', value: 'partial_success' },
    { label: 'Failed', value: 'failed' },
    { label: 'Cancelled', value: 'cancelled' },
  ]

  return (
    <div className="flex flex-col h-full">
      <WorkspaceHeader
        title="Queue"
        subtitle={activeCount > 0 ? `${activeCount} active across projects` : 'All projects'}
        breadcrumbs={[{ label: 'Home', href: '/' }]}
        status={activeCount > 0 ? 'generating' : 'idle'}
      />
      <WorkspaceCanvas>
        <WorkspaceGrid
          asideWidth={320}
          main={(
            <WorkspacePanel
              title="Global job stream"
              eyebrow="Execution log"
              copy="Background work from every project appears here, so active jobs stay visible before you jump into a project."
            >
              <div className="flex flex-wrap items-center gap-[var(--space-2)]" style={{ marginBottom: 'var(--space-4)' }}>
                {filters.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setFilter(item.value)}
                    className={clsx(
                      'rounded-[var(--radius-md)] border cursor-pointer outline-none',
                      'focus-visible:shadow-[var(--focus-ring)] transition-colors duration-[150ms]',
                      filter === item.value
                        ? 'border-[var(--border-accent)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]'
                        : 'border-[var(--border-subtle)] bg-transparent text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]',
                    )}
                    style={{
                      padding: `var(--space-1) var(--space-3)`,
                      fontSize: 'var(--text-xs)',
                      fontWeight: 'var(--weight-medium)',
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              <div className="flex flex-col gap-[var(--space-3)]" style={{ maxWidth: 760 }}>
                {jobsLoading && (
                  <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-sm)' }}>
                    Loading jobs...
                  </span>
                )}

                {!jobsLoading && projectNames.length === 0 && (
                  <WorkspaceEmptyState
                    title="No projects yet"
                    copy="Create a project first; its background jobs will appear here automatically."
                  />
                )}

                {!jobsLoading && projectNames.length > 0 && filteredJobs.length === 0 && (
                  <WorkspaceEmptyState
                    title={jobStatusEmptyLabel(filter)}
                    copy="When a storyboard, asset pass, demo run, or render starts, it will show up here without leaving the global queue."
                  />
                )}

                {filteredJobs.map((job) => (
                  <div key={`${job.project_name}-${job.job_id}`} className="flex flex-col gap-[var(--space-1)]">
                    <a
                      href={`/projects/${encodeURIComponent(job.project_name)}/queue`}
                      className="text-[var(--text-tertiary)] no-underline hover:text-[var(--text-secondary)]"
                      style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)' }}
                    >
                      {job.project_name}
                    </a>
                    <JobCard
                      job={job}
                      project={job.project_name}
                      onCancel={
                        isActiveJob(job)
                          ? () => cancelJob.mutate({ jobId: job.job_id, project: job.project_name })
                          : undefined
                      }
                    />
                  </div>
                ))}
              </div>
            </WorkspacePanel>
          )}
          aside={(
            <WorkspacePanel
              title="Queue health"
              eyebrow="Status"
              copy="Counts are aggregated from each project’s persisted job stream."
            >
              <div className="workspace-kpi-grid">
                <div>
                  <p className="workspace-eyebrow">Total</p>
                  <div className="workspace-panel-title text-[var(--text-3xl)]">{totalCount}</div>
                </div>
                <div>
                  <p className="workspace-eyebrow">Active</p>
                  <div className="workspace-panel-title text-[var(--text-3xl)]">{activeCount}</div>
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
          )}
        />
      </WorkspaceCanvas>
    </div>
  )
}
