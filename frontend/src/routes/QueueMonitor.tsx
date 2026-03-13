import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { clsx } from 'clsx'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader.tsx'
import { ProjectWorkspaceNav } from '../components/composed/ProjectWorkspaceNav.tsx'
import { JobCard } from '../features/jobs/JobCard.tsx'
import { useProjectJobs, useCancelJob } from '../lib/api/scene-hooks.ts'
import type { JobStatus } from '../lib/api/jobs.ts'
import { WorkspaceCanvas, WorkspaceEmptyState, WorkspaceGrid, WorkspacePanel } from '../design-system/recipes'

type FilterValue = 'all' | JobStatus

export function QueueMonitor() {
  const { projectId = '' } = useParams<{ projectId: string }>()
  const { data: jobs, isLoading } = useProjectJobs(projectId, { refetchInterval: 3000 })
  const cancelJobMut = useCancelJob()
  const [filter, setFilter] = useState<FilterValue>('all')

  const allJobs = jobs ?? []
  const filtered = filter === 'all'
    ? allJobs
    : allJobs.filter((j) => j.status === filter)

  const filters: { label: string; value: FilterValue }[] = [
    { label: 'All', value: 'all' },
    { label: 'Running', value: 'running' },
    { label: 'Completed', value: 'succeeded' },
    { label: 'Failed', value: 'failed' },
  ]

  const activeCount = allJobs.filter(
    (j) => j.status === 'queued' || j.status === 'running',
  ).length
  const completedCount = allJobs.filter((j) => j.status === 'succeeded' || j.status === 'partial_success').length
  const failedCount = allJobs.filter((j) => j.status === 'failed').length

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
      {projectId && <ProjectWorkspaceNav projectId={projectId} />}
      <WorkspaceCanvas>
        <WorkspaceGrid
          asideWidth={320}
          main={(
            <WorkspacePanel
              title="Job stream"
              eyebrow="Execution log"
              copy="Filter the current project’s background work without leaving the production context."
            >
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
                    title={filter === 'all' ? 'No jobs yet' : `No ${filter} jobs`}
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
                  <JobCard
                    key={job.job_id}
                    job={job}
                    onCancel={
                      job.status === 'queued' || job.status === 'running'
                        ? () => cancelJobMut.mutate({ jobId: job.job_id, project: projectId })
                        : undefined
                    }
                  />
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
                    <p className="workspace-eyebrow">Active</p>
                    <div className="workspace-panel-title text-[var(--text-3xl)]">{activeCount}</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Completed</p>
                    <div className="workspace-panel-title text-[var(--text-3xl)]">{completedCount}</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Failed</p>
                    <div className="workspace-panel-title text-[var(--text-3xl)]">{failedCount}</div>
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
