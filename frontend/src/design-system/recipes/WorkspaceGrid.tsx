import { clsx } from 'clsx'
import type { CSSProperties, ReactNode } from 'react'

interface WorkspaceGridProps {
  main: ReactNode
  aside?: ReactNode
  asideWidth?: number | string
  className?: string
  mainClassName?: string
  asideClassName?: string
}

export function WorkspaceGrid({
  main,
  aside,
  asideWidth = 352,
  className,
  mainClassName,
  asideClassName,
}: WorkspaceGridProps) {
  const style = {
    ['--workspace-aside-width' as string]: typeof asideWidth === 'number' ? `${asideWidth}px` : asideWidth,
  } as CSSProperties

  return (
    <div
      className={clsx('workspace-grid', className)}
      data-layout={aside ? 'split' : 'stack'}
      style={aside ? style : undefined}
    >
      <div className={clsx('workspace-main', mainClassName)}>{main}</div>
      {aside ? <aside className={clsx('workspace-aside', asideClassName)}>{aside}</aside> : null}
    </div>
  )
}
