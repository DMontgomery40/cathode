import { useNavigate } from 'react-router-dom'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader'
import { IntentDeck } from '../components/composed/IntentDeck'
import { BackgroundMesh } from '../components/primitives/BackgroundMesh'
import { Badge } from '../components/primitives/Badge'
import { WorkspaceCanvas, WorkspacePanel } from '../design-system/recipes'
import { useProjects } from '../lib/api/hooks.ts'
import { useGlobalQueueSummary } from '../lib/api/global-queue.ts'

function latestProject(projects: { name: string; updated_utc?: string | null; created_utc?: string | null }[] | undefined) {
  if (!projects?.length) return null
  return [...projects].sort((a, b) => {
    const left = a.updated_utc || a.created_utc || ''
    const right = b.updated_utc || b.created_utc || ''
    return right.localeCompare(left)
  })[0]
}

export function WorkspaceHome() {
  const navigate = useNavigate()
  const { data: projects } = useProjects()
  const { activeCount, jobsLoading } = useGlobalQueueSummary()
  const projectCount = projects?.length ?? 0
  const renderedCount = (projects ?? []).filter((project) => project.has_video).length
  const projectBadge = projectCount > 0 ? `${projectCount} project${projectCount === 1 ? '' : 's'}` : undefined
  const queueBadge = !jobsLoading && activeCount > 0
    ? `${activeCount} active`
    : undefined
  const recent = latestProject(projects)

  // Every card is a distinct destination backed by real workspace state —
  // no two cards may resolve to the same route.
  const cards = [
    {
      id: 'new-video',
      title: 'Start a new video',
      description: 'Create an explainer video from a brief, source material, or a rough idea.',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="10" cy="10" r="8" />
          <path d="M10 6V14M6 10H14" />
        </svg>
      ),
      onClick: () => navigate('/projects/new/brief'),
    },
    {
      id: 'short-form',
      title: 'Create a vertical short',
      description: 'Shape a 30-50 second hook-first short for TikTok, Reels, or Shorts.',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="6.5" y="2.5" width="7" height="15" rx="1.6" />
          <path d="M8.5 5.5H11.5" />
          <path d="M9 14.5H11" />
        </svg>
      ),
      badge: '9:16',
      onClick: () => navigate('/short-form'),
    },
    ...(recent ? [{
      id: 'continue',
      title: 'Continue editing',
      description: `Jump back into the scene timeline for "${recent.name}".`,
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 4V16H16" />
          <path d="M4 12L8 8L11 11L16 6" />
        </svg>
      ),
      badge: recent.name,
      onClick: () => navigate(`/projects/${recent.name}/scenes`),
    }] : []),
    {
      id: 'library',
      title: 'Browse projects',
      description: projectCount > 0
        ? `Open any of the ${projectCount} saved project${projectCount === 1 ? '' : 's'} in the library.`
        : 'The project library is empty — new videos will land here.',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="4" width="16" height="12" rx="2" />
          <path d="M8 8L13 10L8 12V8Z" />
        </svg>
      ),
      badge: projectBadge,
      onClick: () => navigate('/projects'),
    },
    {
      id: 'queue',
      title: 'Monitor queue',
      description: !jobsLoading && activeCount > 0
        ? `${activeCount} background job${activeCount === 1 ? ' is' : 's are'} running right now.`
        : 'No active jobs — review past storyboard, asset, and render runs.',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="14" height="4" rx="1" />
          <rect x="3" y="9" width="14" height="4" rx="1" />
          <rect x="3" y="15" width="8" height="2" rx="1" />
        </svg>
      ),
      badge: queueBadge,
      onClick: () => navigate('/queue'),
    },
  ]

  return (
    <div className="relative flex flex-col h-full min-h-screen">
      <BackgroundMesh />
      <div className="relative flex flex-col flex-1" style={{ zIndex: 1 }}>
        <WorkspaceHeader
          title="betTube Studio"
          subtitle="Video production workspace"
        />
        <WorkspaceCanvas size="full">
          <div className="workspace-hero-grid">
            <WorkspacePanel
              title="Choose the next move"
              eyebrow="Start"
              copy="Create a new video or short, jump back into your latest project, or check background jobs."
              variant="floating"
            >
              <IntentDeck cards={cards} columns={3} />
            </WorkspacePanel>

            <div className="workspace-panel-stack">
              <WorkspacePanel
                title="Workspace status"
                eyebrow="Overview"
                copy="Current project and queue totals across this workspace."
              >
                <div className="flex flex-wrap gap-[var(--space-2)]">
                  <Badge variant={projectCount > 0 ? 'active' : 'default'}>{projectCount} projects</Badge>
                  <Badge variant={activeCount > 0 ? 'active' : 'default'}>{activeCount} active jobs</Badge>
                  <Badge variant={renderedCount > 0 ? 'success' : 'default'}>{renderedCount} rendered</Badge>
                  <Badge variant="default">9:16 shorts</Badge>
                </div>
              </WorkspacePanel>

              <WorkspacePanel
                title="Quick totals"
                eyebrow="Library"
                copy="Open Projects to pick a timeline, or Queue when background jobs are active."
              >
                <div className="workspace-kpi-grid">
                  <div>
                    <p className="workspace-eyebrow">Projects</p>
                    <div className="workspace-panel-title text-[var(--text-2xl)]">{projectCount}</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Active jobs</p>
                    <div className="workspace-panel-title text-[var(--text-2xl)]">{activeCount}</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Rendered</p>
                    <div className="workspace-panel-title text-[var(--text-2xl)]">{renderedCount}</div>
                  </div>
                </div>
              </WorkspacePanel>
            </div>
          </div>
        </WorkspaceCanvas>
      </div>
    </div>
  )
}
