import { useState } from 'react'
import { clsx } from 'clsx'
import { useParams } from 'react-router-dom'
import { JobCard } from './JobCard.tsx'
import { useProjectJobs, useCancelJob } from '../../lib/api/scene-hooks.ts'

export function JobDock() {
  const { projectId = '' } = useParams<{ projectId: string }>()
  const { data: jobs } = useProjectJobs(projectId, { refetchInterval: 3000 })
  const cancelJob = useCancelJob()
  const [expanded, setExpanded] = useState(false)

  const activeJobs = (jobs ?? []).filter(
    (j) => j.status === 'queued' || j.status === 'running',
  )
  const recentJobs = (jobs ?? []).slice(0, 20)

  if (!projectId || recentJobs.length === 0) return null

  return (
    <div
      className="fixed bottom-0 left-0 right-0 border-t border-[var(--border-subtle)] bg-[var(--surface-shell)]/95 backdrop-blur-[var(--glass-blur)]"
      style={{ zIndex: 'var(--z-floating)' }}
      role="region"
      aria-label="Active jobs"
    >
      {/* Collapsed bar */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left cursor-pointer bg-transparent border-none outline-none focus-visible:shadow-[var(--focus-ring)]"
        style={{ padding: `var(--space-2) var(--space-4)` }}
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-[var(--space-2)]">
          <span
            className={clsx(
              'inline-block rounded-full',
              activeJobs.length > 0 ? 'bg-[var(--signal-active)] animate-pulse' : 'bg-[var(--text-tertiary)]',
            )}
            style={{ width: 8, height: 8 }}
          />
          <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
            {activeJobs.length > 0
              ? `${activeJobs.length} job${activeJobs.length !== 1 ? 's' : ''} running`
              : `${recentJobs.length} recent job${recentJobs.length !== 1 ? 's' : ''}`}
          </span>
        </div>
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          stroke="var(--text-tertiary)"
          strokeWidth="1.5"
          className={clsx('transition-transform duration-[150ms]', expanded && 'rotate-180')}
        >
          <path d="M3 5L7 9L11 5" />
        </svg>
      </button>

      {/* Expanded job list */}
      {expanded && (
        <div
          className="flex flex-col gap-[var(--space-2)] overflow-y-auto"
          style={{
            padding: `0 var(--space-4) var(--space-3)`,
            maxHeight: 300,
          }}
        >
          {recentJobs.map((job) => (
            <JobCard
              key={job.job_id}
              job={job}
              project={projectId}
              onCancel={
                job.status === 'queued' || job.status === 'running'
                  ? () => cancelJob.mutate({ jobId: job.job_id, project: projectId })
                  : undefined
              }
            />
          ))}
        </div>
      )}
    </div>
  )
}
