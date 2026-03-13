import { useEffect } from 'react'
import { Outlet, matchPath, useLocation } from 'react-router-dom'
import { SkipLink } from '../design-system/a11y/index.ts'
import { CommandRail } from '../components/composed/CommandRail.tsx'
import { JobDock } from '../features/jobs/JobDock.tsx'
import { ReactErrorBoundary } from './ReactErrorBoundary.tsx'
import { NotificationCenter } from './NotificationCenter.tsx'
import { writeLastProjectId } from '../lib/project-context.ts'

export function AppShell() {
  const location = useLocation()

  useEffect(() => {
    const projectMatch = matchPath('/projects/:projectId/*', location.pathname)
    const projectId = projectMatch?.params.projectId?.trim()
    if (!projectId || projectId === 'new') {
      return
    }
    writeLastProjectId(projectId)
  }, [location.pathname])

  return (
    <div className="min-h-screen bg-[var(--surface-void)] text-[var(--text-primary)] font-[family-name:var(--font-body)]">
      <SkipLink />
      <div className="flex h-screen overflow-hidden">
        <ReactErrorBoundary fallbackTitle="Navigation failed">
          <CommandRail />
        </ReactErrorBoundary>
        <main id="main-content" className="flex-1 overflow-y-auto">
          <ReactErrorBoundary fallbackTitle="Page error">
            <Outlet />
          </ReactErrorBoundary>
        </main>
      </div>
      <NotificationCenter />
      <JobDock />
    </div>
  )
}
