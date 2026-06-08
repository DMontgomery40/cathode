import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from './AppShell.tsx'
import { RouteErrorBoundary } from './ErrorBoundary.tsx'
import {
  BriefStudioRoute,
  GlobalQueueRoute,
  ProjectsListRoute,
  QueueMonitorRoute,
  RenderControlRoute,
  SceneTimelineRoute,
  SettingsRoute,
  WorkspaceHomeRoute,
} from './route-elements.tsx'

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    errorElement: (
      <AppShell />
    ),
    children: [
      { index: true, element: <WorkspaceHomeRoute /> },
      { path: 'projects', element: <ProjectsListRoute /> },
      { path: 'projects/:projectId/brief', element: <BriefStudioRoute /> },
      { path: 'projects/:projectId/scenes', element: <SceneTimelineRoute /> },
      { path: 'projects/:projectId/render', element: <RenderControlRoute /> },
      { path: 'projects/:projectId/queue', element: <QueueMonitorRoute /> },
      { path: 'queue', element: <GlobalQueueRoute /> },
      { path: 'settings', element: <SettingsRoute /> },
      { path: '*', element: <RouteErrorBoundary /> },
    ],
  },
])
