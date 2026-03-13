import { useRouteError, isRouteErrorResponse, Link } from 'react-router-dom'
import { GlassPanel } from '../components/primitives/GlassPanel.tsx'

export function RouteErrorBoundary() {
  const error = useRouteError()
  const isNotFound = isRouteErrorResponse(error) && error.status === 404

  return (
    <div className="flex items-center justify-center h-full min-h-[400px]" style={{ padding: 'var(--space-8)' }}>
      <GlassPanel variant="elevated" padding="lg" rounded="xl" className="max-w-md w-full text-center">
        <div className="flex flex-col items-center gap-[var(--space-4)]">
          <svg
            width="48"
            height="48"
            viewBox="0 0 48 48"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            className="text-[var(--signal-warning)]"
            aria-hidden="true"
          >
            {isNotFound ? (
              <>
                <circle cx="24" cy="24" r="20" />
                <path d="M18 18L30 30M30 18L18 30" />
              </>
            ) : (
              <>
                <circle cx="24" cy="24" r="20" />
                <path d="M24 16V26" strokeLinecap="round" />
                <circle cx="24" cy="32" r="1.5" fill="currentColor" stroke="none" />
              </>
            )}
          </svg>

          <h2
            className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0"
            style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--weight-semibold)' }}
          >
            {isNotFound ? 'Page not found' : 'Something went wrong'}
          </h2>

          <p
            className="text-[var(--text-secondary)] m-0"
            style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-normal)' }}
          >
            {isNotFound
              ? 'The page you requested does not exist.'
              : 'An unexpected error occurred. Try refreshing or navigating back.'}
          </p>

          {!isNotFound && error instanceof Error && (
            <pre
              className="w-full text-left text-[var(--signal-danger)] bg-[var(--surface-stage)] rounded-[var(--radius-md)] overflow-x-auto"
              style={{
                fontSize: 'var(--text-xs)',
                fontFamily: 'var(--font-mono)',
                padding: 'var(--space-3)',
                margin: 0,
                maxHeight: 200,
              }}
            >
              {error.message}
            </pre>
          )}

          <div className="flex items-center gap-[var(--space-3)]">
            <Link
              to="/"
              className="rounded-[var(--radius-md)] border border-[var(--border-accent)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/20 no-underline outline-none focus-visible:shadow-[var(--focus-ring)]"
              style={{
                padding: 'var(--space-2) var(--space-4)',
                fontSize: 'var(--text-sm)',
                fontWeight: 'var(--weight-medium)',
              }}
            >
              Go Home
            </Link>
            <button
              onClick={() => window.location.reload()}
              className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)] cursor-pointer outline-none focus-visible:shadow-[var(--focus-ring)]"
              style={{
                padding: 'var(--space-2) var(--space-4)',
                fontSize: 'var(--text-sm)',
                fontWeight: 'var(--weight-medium)',
              }}
            >
              Refresh
            </button>
          </div>
        </div>
      </GlassPanel>
    </div>
  )
}
