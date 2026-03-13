import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from './AppShell.tsx'
import { RouteErrorBoundary } from './ErrorBoundary.tsx'
import { WorkspaceHome } from '../routes/WorkspaceHome.tsx'
import { BriefStudio } from '../routes/BriefStudio.tsx'
import { ProjectsList } from '../routes/ProjectsList.tsx'
import { SceneTimeline } from '../routes/SceneTimeline.tsx'
import { RenderControl } from '../routes/RenderControl.tsx'
import { QueueMonitor } from '../routes/QueueMonitor.tsx'
import { GlobalQueue } from '../routes/GlobalQueue.tsx'
import { Settings } from '../routes/Settings.tsx'

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    errorElement: (
      <AppShell />
    ),
    children: [
      { index: true, element: <WorkspaceHome /> },
      { path: 'projects', element: <ProjectsList /> },
      { path: 'projects/:projectId/brief', element: <BriefStudio /> },
      { path: 'projects/:projectId/scenes', element: <SceneTimeline /> },
      { path: 'projects/:projectId/render', element: <RenderControl /> },
      { path: 'projects/:projectId/queue', element: <QueueMonitor /> },
      { path: 'queue', element: <GlobalQueue /> },
      { path: 'settings', element: <Settings /> },
      { path: '*', element: <RouteErrorBoundary /> },
    ],
  },
])
