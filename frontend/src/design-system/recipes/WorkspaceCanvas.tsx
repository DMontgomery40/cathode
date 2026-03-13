import { clsx } from 'clsx'
import type { ReactNode } from 'react'

interface WorkspaceCanvasProps {
  children: ReactNode
  size?: 'compact' | 'wide' | 'full'
  className?: string
  innerClassName?: string
}

export function WorkspaceCanvas({
  children,
  size = 'wide',
  className,
  innerClassName,
}: WorkspaceCanvasProps) {
  return (
    <section className={clsx('workspace-canvas', className)} data-size={size}>
      <div className={clsx('workspace-canvas__inner', innerClassName)}>{children}</div>
    </section>
  )
}
