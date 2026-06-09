import { clsx } from 'clsx'

interface RemotionUnavailableProps {
  manifest: Record<string, unknown> | null | undefined
  className?: string
  height?: number
}

function positiveNumber(value: unknown): number | null {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

/**
 * Remotion-free placeholder shown in place of the live composition <Player> when the
 * optional Remotion player packages are not installed. Rendered scene media and the
 * final video play independently of this surface, so this never blocks playback.
 */
export default function RemotionUnavailable({
  manifest,
  className,
  height = 360,
}: RemotionUnavailableProps) {
  const width = positiveNumber(manifest?.width)
  const compositionHeight = positiveNumber(manifest?.height)
  const fps = positiveNumber(manifest?.fps)
  const scenes = Array.isArray(manifest?.scenes) ? manifest.scenes.length : null

  return (
    <div
      data-testid="remotion-player-surface"
      className={clsx('flex items-center justify-center overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--surface-void)]', className)}
      style={{ minHeight: height }}
    >
      <div className="flex max-w-[32rem] flex-col gap-[var(--space-2)] px-[var(--space-5)] py-[var(--space-6)] text-center">
        <div
          className="text-[var(--text-primary)]"
          style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-md)', fontWeight: 'var(--weight-semibold)' }}
        >
          Live composition preview unavailable
        </div>
        <div
          className="text-[var(--text-tertiary)]"
          style={{ fontSize: 'var(--text-sm)' }}
        >
          The optional Remotion player packages are not installed in this build. Rendered scene media and the final video still play normally — install the optional Remotion toolchain to enable the live composition preview.
        </div>
        {(width || compositionHeight || fps || scenes !== null) && (
          <div
            className="mt-[var(--space-2)] text-[var(--text-tertiary)]"
            style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)' }}
          >
            {width && compositionHeight ? `${width}x${compositionHeight}` : 'manifest loaded'}
            {fps ? ` / ${fps}fps` : ''}
            {scenes !== null ? ` / ${scenes} scene${scenes === 1 ? '' : 's'}` : ''}
          </div>
        )}
      </div>
    </div>
  )
}
