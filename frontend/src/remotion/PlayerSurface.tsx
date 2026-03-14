import { Player } from '@remotion/player'
import { clsx } from 'clsx'
import { CathodeRender, FALLBACK_PROPS, type CathodeRenderProps } from './index.tsx'

interface PlayerSurfaceProps {
  manifest: Record<string, unknown> | null | undefined
  className?: string
  height?: number
}

function asPositiveNumber(value: unknown, fallback: number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

export function PlayerSurface({
  manifest,
  className,
  height = 360,
}: PlayerSurfaceProps) {
  const props = (manifest ?? {}) as CathodeRenderProps
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
        component={CathodeRender}
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
