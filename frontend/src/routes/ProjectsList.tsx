import { useNavigate } from 'react-router-dom'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader.tsx'
import { ProjectCard } from '../features/projects/ProjectCard.tsx'
import { Button } from '../components/primitives/Button.tsx'
import { useProjects } from '../lib/api/hooks.ts'
import { WorkspaceCanvas, WorkspaceEmptyState, WorkspacePanel } from '../design-system/recipes'

export function ProjectsList() {
  const navigate = useNavigate()
  const { data: projects, isLoading } = useProjects()
  const projectCount = projects?.length ?? 0

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
            {projects.map((project) => (
              <ProjectCard key={project.name} project={project} />
            ))}
          </div>
        )}
      </WorkspaceCanvas>
    </div>
  )
}
