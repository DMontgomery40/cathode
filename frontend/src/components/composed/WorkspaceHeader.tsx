import { clsx } from 'clsx'
import { useReducedMotion } from '../../design-system/motion'

interface WorkspaceHeaderProps {
  title: string
  subtitle?: string
  breadcrumbs?: { label: string; href?: string }[]
  actions?: React.ReactNode
  status?: 'idle' | 'generating' | 'rendering' | 'error'
}

const statusConfig = {
  idle: {
    label: 'Idle',
    className: 'text-[var(--text-tertiary)] bg-transparent border-[var(--border-subtle)]',
  },
  generating: {
    label: 'Generating',
    className: 'text-[var(--signal-active)] bg-[rgba(91,138,130,0.12)] border-[var(--border-glow)]',
  },
  rendering: {
    label: 'Rendering',
    className: 'text-[var(--accent-primary)] bg-[var(--accent-primary-muted)] border-[var(--border-accent)]',
  },
  error: {
    label: 'Error',
    className: 'text-[var(--signal-danger)] bg-[rgba(200,90,90,0.12)] border-[rgba(200,90,90,0.3)]',
  },
} as const

export function WorkspaceHeader({
  title,
  subtitle,
  breadcrumbs,
  actions,
  status = 'idle',
}: WorkspaceHeaderProps) {
  const reducedMotion = useReducedMotion()
  const statusInfo = statusConfig[status]

  return (
    <header
      role="banner"
      className="flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--surface-shell)]/80 backdrop-blur-[var(--glass-blur)]"
      style={{
        zIndex: 'var(--z-header)',
        padding: `var(--space-4) var(--space-6)`,
        minHeight: 72,
      }}
    >
      {/* Left: breadcrumbs + title */}
      <div className="flex flex-col gap-[var(--space-1)] min-w-0">
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav aria-label="Breadcrumb">
            <ol className="flex items-center gap-[var(--space-1)] list-none p-0 m-0">
              {breadcrumbs.map((crumb, i) => (
                <li key={i} className="flex items-center gap-[var(--space-1)]">
                  {i > 0 && (
                    <span
                      className="text-[var(--text-tertiary)] select-none"
                      style={{ fontSize: 'var(--text-xs)' }}
                      aria-hidden="true"
                    >
                      /
                    </span>
                  )}
                  {crumb.href ? (
                    <a
                      href={crumb.href}
                      className="text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] no-underline outline-none focus-visible:shadow-[var(--focus-ring)] rounded-[var(--radius-sm)]"
                      style={{
                        fontSize: 'var(--text-xs)',
                        fontFamily: 'var(--font-body)',
                      }}
                    >
                      {crumb.label}
                    </a>
                  ) : (
                    <span
                      className="text-[var(--text-tertiary)]"
                      style={{
                        fontSize: 'var(--text-xs)',
                        fontFamily: 'var(--font-body)',
                      }}
                    >
                      {crumb.label}
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </nav>
        )}
        <div className="flex items-baseline gap-[var(--space-3)]">
          <h1
            className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0 truncate"
            style={{
              fontSize: 'var(--text-4xl)',
              fontWeight: 'var(--weight-bold)',
              lineHeight: 'var(--leading-tight)',
              letterSpacing: 'var(--tracking-tight)',
            }}
          >
            {title}
          </h1>
          {subtitle && (
            <span
              className="font-[family-name:var(--font-body)] text-[var(--text-secondary)] shrink-0"
              style={{ fontSize: 'var(--text-sm)' }}
            >
              {subtitle}
            </span>
          )}
        </div>
      </div>

      {/* Right: status + actions */}
      <div className="flex items-center gap-[var(--space-3)] shrink-0">
        <span
          className={clsx(
            'inline-flex items-center rounded-[var(--radius-full)] border',
            'font-[family-name:var(--font-mono)]',
            statusInfo.className,
            status === 'generating' && !reducedMotion && 'animate-pulse',
          )}
          style={{
            fontSize: 'var(--text-xs)',
            padding: `var(--space-1) var(--space-3)`,
            fontWeight: 'var(--weight-medium)',
          }}
          aria-label={`Status: ${statusInfo.label}`}
        >
          <span
            className={clsx(
              'inline-block rounded-full mr-[var(--space-2)]',
              status === 'idle' && 'bg-[var(--text-tertiary)]',
              status === 'generating' && 'bg-[var(--signal-active)]',
              status === 'rendering' && 'bg-[var(--accent-primary)]',
              status === 'error' && 'bg-[var(--signal-danger)]',
            )}
            style={{ width: 6, height: 6 }}
            aria-hidden="true"
          />
          {statusInfo.label}
        </span>
        {actions}
      </div>
    </header>
  )
}
