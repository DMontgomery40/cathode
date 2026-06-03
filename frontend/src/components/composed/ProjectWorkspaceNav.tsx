import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import { Badge } from '../primitives/Badge.tsx'
import { projectModeFromPlan } from '../../lib/project-mode.ts'
import type { Plan } from '../../lib/schemas/plan.ts'

interface ProjectWorkspaceNavProps {
  projectId: string
  plan?: Plan | null
}

const tabs = [
  { label: 'Brief', segment: 'brief' },
  { label: 'Scenes', segment: 'scenes' },
  { label: 'Render', segment: 'render' },
  { label: 'Queue', segment: 'queue' },
] as const

export function ProjectWorkspaceNav({ projectId, plan }: ProjectWorkspaceNavProps) {
  const encodedProjectId = encodeURIComponent(projectId)
  const mode = projectModeFromPlan(plan)

  return (
    <nav
      aria-label="Project workspace"
      className="border-b border-[var(--border-subtle)] bg-[var(--surface-shell)]/65 backdrop-blur-[var(--glass-blur)]"
    >
      <div className="flex items-center justify-between gap-[var(--space-3)] overflow-x-auto px-[var(--space-6)] py-[var(--space-3)]">
        <div className="flex items-center gap-[var(--space-2)]">
          {tabs.map((tab) => (
            <NavLink
              key={tab.segment}
              to={`/projects/${encodedProjectId}/${tab.segment}`}
              className={({ isActive }) =>
                clsx(
                  'inline-flex items-center rounded-[var(--radius-full)] border no-underline outline-none focus-visible:shadow-[var(--focus-ring)]',
                  'font-[family-name:var(--font-mono)] transition-colors duration-150 whitespace-nowrap',
                  isActive
                    ? 'border-[var(--border-accent)] bg-[var(--accent-primary-muted)] text-[var(--accent-primary)]'
                    : 'border-[var(--border-subtle)] bg-transparent text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-[var(--surface-stage)]',
                )
              }
              style={{
                padding: `var(--space-2) var(--space-3)`,
                fontSize: 'var(--text-xs)',
                fontWeight: 'var(--weight-medium)',
              }}
            >
              {tab.label}
            </NavLink>
          ))}
        </div>
        <Badge variant={mode.id === 'vertical_short' ? 'active' : 'default'} size="sm">
          {mode.badge}
        </Badge>
      </div>
    </nav>
  )
}
