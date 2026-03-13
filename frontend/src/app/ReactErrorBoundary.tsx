import { Component, type ReactNode } from 'react'
import { GlassPanel } from '../components/primitives/GlassPanel.tsx'

interface Props {
  children: ReactNode
  fallbackTitle?: string
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ReactErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children
    }

    return (
      <div className="flex items-center justify-center h-full min-h-[300px]" style={{ padding: 'var(--space-8)' }}>
        <GlassPanel variant="elevated" padding="lg" rounded="xl" className="max-w-lg w-full">
          <div className="flex flex-col gap-[var(--space-4)]">
            <div className="flex items-center gap-[var(--space-3)]">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                className="text-[var(--signal-warning)] shrink-0"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M12 8V12" strokeLinecap="round" />
                <circle cx="12" cy="16" r="1" fill="currentColor" stroke="none" />
              </svg>
              <h2
                className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0"
                style={{ fontSize: 'var(--text-lg)', fontWeight: 'var(--weight-semibold)' }}
              >
                {this.props.fallbackTitle ?? 'Something went wrong'}
              </h2>
            </div>

            {this.state.error && (
              <pre
                className="text-[var(--signal-danger)] bg-[var(--surface-stage)] rounded-[var(--radius-md)] overflow-x-auto"
                style={{
                  fontSize: 'var(--text-xs)',
                  fontFamily: 'var(--font-mono)',
                  padding: 'var(--space-3)',
                  margin: 0,
                  maxHeight: 160,
                }}
              >
                {this.state.error.message}
              </pre>
            )}

            <div className="flex gap-[var(--space-3)]">
              <button
                onClick={() => this.setState({ hasError: false, error: null })}
                className="rounded-[var(--radius-md)] border border-[var(--border-accent)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/20 cursor-pointer outline-none focus-visible:shadow-[var(--focus-ring)]"
                style={{
                  padding: 'var(--space-2) var(--space-4)',
                  fontSize: 'var(--text-sm)',
                  fontWeight: 'var(--weight-medium)',
                }}
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)] cursor-pointer outline-none focus-visible:shadow-[var(--focus-ring)]"
                style={{
                  padding: 'var(--space-2) var(--space-4)',
                  fontSize: 'var(--text-sm)',
                  fontWeight: 'var(--weight-medium)',
                }}
              >
                Reload Page
              </button>
            </div>
          </div>
        </GlassPanel>
      </div>
    )
  }
}
