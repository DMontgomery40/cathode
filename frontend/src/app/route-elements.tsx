import { Suspense, lazy, type ReactNode } from 'react'

const WorkspaceHome = lazy(() =>
  import('../routes/WorkspaceHome.tsx').then((module) => ({ default: module.WorkspaceHome })),
)
const BriefStudio = lazy(() =>
  import('../routes/BriefStudio.tsx').then((module) => ({ default: module.BriefStudio })),
)
const ProjectsList = lazy(() =>
  import('../routes/ProjectsList.tsx').then((module) => ({ default: module.ProjectsList })),
)
const SceneTimeline = lazy(() =>
  import('../routes/SceneTimeline.tsx').then((module) => ({ default: module.SceneTimeline })),
)
const RenderControl = lazy(() =>
  import('../routes/RenderControl.tsx').then((module) => ({ default: module.RenderControl })),
)
const QueueMonitor = lazy(() =>
  import('../routes/QueueMonitor.tsx').then((module) => ({ default: module.QueueMonitor })),
)
const GlobalQueue = lazy(() =>
  import('../routes/GlobalQueue.tsx').then((module) => ({ default: module.GlobalQueue })),
)
const Settings = lazy(() =>
  import('../routes/Settings.tsx').then((module) => ({ default: module.Settings })),
)

function RouteFallback() {
  return (
    <div className="flex h-full min-h-[320px] items-center justify-center">
      <div
        className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] text-[var(--text-secondary)]"
        style={{
          padding: 'var(--space-3) var(--space-4)',
          fontSize: 'var(--text-sm)',
        }}
      >
        Loading workspace
      </div>
    </div>
  )
}

function RouteSuspense({ children }: { children: ReactNode }) {
  return <Suspense fallback={<RouteFallback />}>{children}</Suspense>
}

export function WorkspaceHomeRoute() {
  return (
    <RouteSuspense>
      <WorkspaceHome />
    </RouteSuspense>
  )
}

export function BriefStudioRoute() {
  return (
    <RouteSuspense>
      <BriefStudio />
    </RouteSuspense>
  )
}

export function ProjectsListRoute() {
  return (
    <RouteSuspense>
      <ProjectsList />
    </RouteSuspense>
  )
}

export function SceneTimelineRoute() {
  return (
    <RouteSuspense>
      <SceneTimeline />
    </RouteSuspense>
  )
}

export function RenderControlRoute() {
  return (
    <RouteSuspense>
      <RenderControl />
    </RouteSuspense>
  )
}

export function QueueMonitorRoute() {
  return (
    <RouteSuspense>
      <QueueMonitor />
    </RouteSuspense>
  )
}

export function GlobalQueueRoute() {
  return (
    <RouteSuspense>
      <GlobalQueue />
    </RouteSuspense>
  )
}

export function SettingsRoute() {
  return (
    <RouteSuspense>
      <Settings />
    </RouteSuspense>
  )
}
