import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader.tsx'
import { ProjectCard } from '../features/projects/ProjectCard.tsx'
import { Button } from '../components/primitives/Button.tsx'
import { Select } from '../components/primitives/Select.tsx'
import { useProjects } from '../lib/api/hooks.ts'
import type { ProjectSummary } from '../lib/api/projects.ts'
import { WorkspaceCanvas, WorkspaceEmptyState, WorkspacePanel } from '../design-system/recipes'

type ProjectSortOrder = 'created-desc' | 'created-asc' | 'updated-desc' | 'name-asc'

const PROJECT_SORT_OPTIONS = [
  { value: 'created-desc', label: 'Newest first' },
  { value: 'created-asc', label: 'Oldest first' },
  { value: 'updated-desc', label: 'Recently updated' },
  { value: 'name-asc', label: 'A to Z' },
] as const

function timestampValue(iso?: string | null): number {
  if (!iso) return 0
  const timestamp = new Date(iso).valueOf()
  return Number.isFinite(timestamp) ? timestamp : 0
}

function sortProjects(projects: ProjectSummary[], order: ProjectSortOrder): ProjectSummary[] {
  return [...projects].sort((left, right) => {
    if (order === 'name-asc') {
      return left.name.localeCompare(right.name)
    }

    const useCreatedTime = order === 'created-desc' || order === 'created-asc'
    const leftTime = useCreatedTime
      ? timestampValue(left.created_utc || left.updated_utc)
      : timestampValue(left.updated_utc || left.created_utc)
    const rightTime = useCreatedTime
      ? timestampValue(right.created_utc || right.updated_utc)
      : timestampValue(right.updated_utc || right.created_utc)
    if (leftTime !== rightTime) {
      return order === 'created-asc' ? leftTime - rightTime : rightTime - leftTime
    }

    return left.name.localeCompare(right.name)
  })
}

export function ProjectsList() {
  const navigate = useNavigate()
  const { data: projects, isLoading } = useProjects()
  const [sortOrder, setSortOrder] = useState<ProjectSortOrder>('created-desc')
  const projectCount = projects?.length ?? 0
  const sortedProjects = useMemo(
    () => sortProjects(projects ?? [], sortOrder),
    [projects, sortOrder],
  )

  return (
    <div className="flex flex-col h-full">
      <WorkspaceHeader
        title="Projects"
        breadcrumbs={[{ label: 'Home', href: '/' }]}
        actions={
          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate('/projects/new/brief')}
          >
            New Project
          </Button>
        }
      />
      <WorkspaceCanvas>
        <WorkspacePanel
          title="Project library"
          eyebrow="Workspace index"
          copy="Every project should read like a durable production object with a brief, a timeline, generated assets, and a render history."
        >
          <div className="workspace-kpi-grid">
            <div>
              <p className="workspace-eyebrow">Projects</p>
              <div className="workspace-panel-title text-[var(--text-3xl)]">{projectCount}</div>
            </div>
            <div>
              <p className="workspace-eyebrow">Mode</p>
              <div className="workspace-panel-title text-[var(--text-3xl)]">Local-first</div>
            </div>
            <div>
              <p className="workspace-eyebrow">Source of truth</p>
              <div className="workspace-panel-title text-[var(--text-3xl)]">plan.json</div>
            </div>
          </div>
        </WorkspacePanel>

        {!isLoading && sortedProjects.length > 0 ? (
          <div className="flex justify-end">
            <div className="w-full sm:w-[15rem]">
              <Select
                label="Sort projects"
                value={sortOrder}
                onChange={(event) => setSortOrder(event.target.value as ProjectSortOrder)}
                options={PROJECT_SORT_OPTIONS.map((option) => ({ value: option.value, label: option.label }))}
                hint="Newest first uses project creation time. Recently updated uses the latest plan activity."
              />
            </div>
          </div>
        ) : null}

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-[var(--space-4)]">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="rounded-[var(--radius-lg)] bg-[var(--surface-stage)] animate-pulse"
                style={{ height: 220 }}
              />
            ))}
          </div>
        ) : !projects || projects.length === 0 ? (
          <WorkspaceEmptyState
            title="No projects yet"
            copy="Create the first project and Cathode will give it a brief, a scene timeline, and a local artifact trail."
            icon={(
              <svg
                width="48"
                height="48"
                viewBox="0 0 48 48"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                className="text-[var(--text-tertiary)]"
                aria-hidden="true"
              >
                <rect x="6" y="10" width="36" height="28" rx="4" />
                <path d="M20 22L28 26L20 30V22Z" />
              </svg>
            )}
            action={(
              <Button
                variant="primary"
                onClick={() => navigate('/projects/new/brief')}
              >
                Create your first video
              </Button>
            )}
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-[var(--space-4)]">
            {sortedProjects.map((project) => (
              <ProjectCard key={project.name} project={project} />
            ))}
          </div>
        )}
      </WorkspaceCanvas>
    </div>
  )
}
