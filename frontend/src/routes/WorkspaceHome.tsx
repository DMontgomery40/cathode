import { useNavigate } from 'react-router-dom'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader'
import { IntentDeck } from '../components/composed/IntentDeck'
import { BackgroundMesh } from '../components/primitives/BackgroundMesh'
import { Badge } from '../components/primitives/Badge'
import { WorkspaceCanvas, WorkspacePanel } from '../design-system/recipes'

export function WorkspaceHome() {
  const navigate = useNavigate()

  const cards = [
    {
      id: 'new-video',
      title: 'Start a new video',
      description: 'Create an explainer video from a brief, source material, or a quick prompt.',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="10" cy="10" r="8" />
          <path d="M10 6V14M6 10H14" />
        </svg>
      ),
      onClick: () => navigate('/projects/new/brief'),
    },
    {
      id: 'continue',
      title: 'Continue editing',
      description: 'Pick up where you left off on an in-progress project.',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 4V16H16" />
          <path d="M4 12L8 8L11 11L16 6" />
        </svg>
      ),
      badge: '3 projects',
      onClick: () => navigate('/projects'),
    },
    {
      id: 'review',
      title: 'Review footage & style',
      description: 'Browse generated scenes, swap images, and refine visual direction.',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="4" width="16" height="12" rx="2" />
          <path d="M8 8L13 10L8 12V8Z" />
        </svg>
      ),
      onClick: () => navigate('/projects'),
    },
    {
      id: 'render',
      title: 'Render & ship',
      description: 'Assemble final cuts and export completed videos.',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 16V4L10 10L16 4V16" />
        </svg>
      ),
      onClick: () => navigate('/projects'),
    },
    {
      id: 'queue',
      title: 'Monitor queue',
      description: 'Check on active generation and render jobs.',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="14" height="4" rx="1" />
          <rect x="3" y="9" width="14" height="4" rx="1" />
          <rect x="3" y="15" width="8" height="2" rx="1" />
        </svg>
      ),
      badge: '2 queued',
      onClick: () => navigate('/queue'),
    },
  ]

  return (
    <div className="relative flex flex-col h-full min-h-screen">
      <BackgroundMesh />
      <div className="relative flex flex-col flex-1" style={{ zIndex: 1 }}>
        <WorkspaceHeader
          title="Cathode"
          subtitle="Video production workspace"
        />
        <WorkspaceCanvas size="full">
          <div className="workspace-hero-grid">
            <WorkspacePanel
              title="Choose the next move"
              eyebrow="Intent Deck"
              copy="Move between planning, scene editing, rendering, and queue monitoring without changing mental models. The shell stays consistent while the workspace shifts underneath you."
              variant="floating"
            >
              <IntentDeck cards={cards} columns={3} />
            </WorkspacePanel>

            <div className="workspace-panel-stack">
              <WorkspacePanel
                title="Active modes"
                eyebrow="Multimodal flow"
                copy="Cathode should feel fluid across typing, drag and drop, media scrubbing, keyboard navigation, and live asset review."
              >
                <div className="flex flex-wrap gap-[var(--space-2)]">
                  <Badge variant="active">Brief editing</Badge>
                  <Badge variant="active">Drag/drop media</Badge>
                  <Badge variant="active">Keyboard-first</Badge>
                  <Badge variant="active">Timeline review</Badge>
                  <Badge variant="default">Command palette</Badge>
                </div>
              </WorkspacePanel>

              <WorkspacePanel
                title="Control room principles"
                eyebrow="Design system"
                copy="Glass layers, warm technical type, visible system state, and clear route-to-route continuity should shape every workspace rather than being special-case styling."
              >
                <div className="workspace-kpi-grid">
                  <div>
                    <p className="workspace-eyebrow">Surface</p>
                    <div className="workspace-panel-title text-[var(--text-2xl)]">Glass</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Feedback</p>
                    <div className="workspace-panel-title text-[var(--text-2xl)]">Visible</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Layout</p>
                    <div className="workspace-panel-title text-[var(--text-2xl)]">Modular</div>
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
