import { clsx } from 'clsx'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader.tsx'
import { WorkspaceCanvas, WorkspaceEmptyState } from '../design-system/recipes'

export function GlobalQueue() {
  return (
    <div className="flex flex-col h-full">
      <WorkspaceHeader
        title="Queue"
        subtitle="All projects"
        breadcrumbs={[{ label: 'Home', href: '/' }]}
      />
      <WorkspaceCanvas size="compact">
        <WorkspaceEmptyState
          title="Select a project to inspect its queue"
          copy="The global queue stays intentionally lightweight. Use the project library to jump into a specific production run and inspect its jobs in context."
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
          action={(
            <a
              href="/projects"
              className={clsx(
                'rounded-[var(--radius-md)] border border-[var(--border-accent)]',
                'bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]',
                'hover:bg-[var(--accent-primary)]/20 no-underline',
                'outline-none focus-visible:shadow-[var(--focus-ring)]',
              )}
              style={{
                padding: 'var(--space-2) var(--space-4)',
                fontSize: 'var(--text-sm)',
                fontWeight: 'var(--weight-medium)',
              }}
            >
              Browse Projects
            </a>
          )}
        />
      </WorkspaceCanvas>
    </div>
  )
}
