// Real in-browser Remotion composition player. This module imports the optional
// Remotion packages (@remotion/player) and the heavy composition root (./index.tsx),
// so it is loaded ONLY via the `remotion-player-surface` alias, which Vite points here
// exclusively when Remotion is installed. When Remotion is absent the alias resolves to
// RemotionPlayerSurface.stub.tsx instead, and this file is never pulled into the build.
// It is excluded from tsconfig.app.json type-checking for the same reason.
import { Player } from '@remotion/player'
import { clsx } from 'clsx'
import { BetTubeStudioRender, type BetTubeStudioRenderProps } from './index.tsx'
import { FALLBACK_PROPS } from './constants.ts'

interface RemotionPlayerSurfaceProps {
  manifest: Record<string, unknown> | null | undefined
  className?: string
  height?: number
}

function asPositiveNumber(value: unknown, fallback: number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

export default function RemotionPlayerSurface({
  manifest,
  className,
  height = 360,
}: RemotionPlayerSurfaceProps) {
  const props = (manifest ?? {}) as BetTubeStudioRenderProps
  const compositionWidth = asPositiveNumber(props.width, FALLBACK_PROPS.width)
  const compositionHeight = asPositiveNumber(props.height, FALLBACK_PROPS.height)
  const fps = asPositiveNumber(props.fps, FALLBACK_PROPS.fps)
  const durationInFrames = asPositiveNumber(
    props.totalDurationInFrames
      || props.scenes?.reduce((sum, scene) => sum + Math.max(1, scene.durationInFrames || 1), 0),
    FALLBACK_PROPS.totalDurationInFrames,
  )

  return (
    <div
      data-testid="remotion-player-surface"
      className={clsx('overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--surface-void)]', className)}
    >
      <Player
        component={BetTubeStudioRender}
        inputProps={{
          ...FALLBACK_PROPS,
          ...props,
          width: compositionWidth,
          height: compositionHeight,
          fps,
          totalDurationInFrames: durationInFrames,
        }}
        durationInFrames={durationInFrames}
        compositionWidth={compositionWidth}
        compositionHeight={compositionHeight}
        fps={fps}
        controls
        style={{
          width: '100%',
          height,
          backgroundColor: '#03050a',
        }}
      />
    </div>
  )
}
