import type { ReactNode } from 'react'
import { clsx } from 'clsx'
import { GlassPanel } from '../../components/primitives/GlassPanel'

interface WorkspacePanelProps {
  title: string
  eyebrow?: string
  copy?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
  variant?: 'default' | 'elevated' | 'inset' | 'floating'
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

export function WorkspacePanel({
  title,
  eyebrow,
  copy,
  actions,
  children,
  className,
  variant = 'default',
  padding = 'lg',
}: WorkspacePanelProps) {
  return (
    <GlassPanel variant={variant} padding={padding} rounded="lg" className={className}>
      <div className="workspace-panel-head">
        <div className="min-w-0">
          {eyebrow ? <p className="workspace-eyebrow">{eyebrow}</p> : null}
          <h2 className="workspace-panel-title">{title}</h2>
          {copy ? <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">{copy}</p> : null}
        </div>
        {actions ? <div className="shrink-0">{actions}</div> : null}
      </div>
      <div className={clsx('min-w-0')}>{children}</div>
    </GlassPanel>
  )
}
