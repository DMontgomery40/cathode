import type { ReactNode } from 'react'
import { GlassPanel } from '../../components/primitives/GlassPanel'

interface WorkspaceEmptyStateProps {
  title: string
  copy: string
  icon?: ReactNode
  action?: ReactNode
}

export function WorkspaceEmptyState({ title, copy, icon, action }: WorkspaceEmptyStateProps) {
  return (
    <GlassPanel variant="inset" padding="lg" rounded="xl">
      <div className="workspace-empty">
        {icon}
        <div className="flex flex-col gap-[var(--space-2)]">
          <h2 className="workspace-panel-title">{title}</h2>
          <p className="workspace-panel-copy m-0">{copy}</p>
        </div>
        {action}
      </div>
    </GlassPanel>
  )
}
