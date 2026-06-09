import { Suspense, lazy, Component, type ReactNode } from 'react'
import RemotionUnavailable from './RemotionUnavailable.tsx'

// The live composition player is optional. It is loaded lazily via the
// `remotion-player-surface` alias, which Vite points at the real @remotion/player surface
// only when Remotion is installed (otherwise a Remotion-free stub). This wrapper imports
// nothing from Remotion, so PlayerSurface itself always builds and never blocks the app.
const RemotionPlayerSurface = lazy(() => import('remotion-player-surface'))

interface PlayerSurfaceProps {
  manifest: Record<string, unknown> | null | undefined
  className?: string
  height?: number
}

interface ErrorBoundaryProps {
  fallback: ReactNode
  children: ReactNode
}

class PlayerErrorBoundary extends Component<ErrorBoundaryProps, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

export function PlayerSurface({ manifest, className, height = 360 }: PlayerSurfaceProps) {
  const fallback = <RemotionUnavailable manifest={manifest} className={className} height={height} />
  return (
    <PlayerErrorBoundary fallback={fallback}>
      <Suspense fallback={fallback}>
        <RemotionPlayerSurface manifest={manifest} className={className} height={height} />
      </Suspense>
    </PlayerErrorBoundary>
  )
}
