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

type ManifestScene = Record<string, unknown> & {
  title?: string
  imageUrl?: string
  onScreenText?: unknown
  textLayerKind?: string
  composition?: {
    family?: string
    mode?: string
    manifestation?: string
    props?: Record<string, unknown>
    data?: Record<string, unknown> | null
  }
}

type ChartPoint = {
  x: string
  y: number | null
}

type ChartSeries = {
  id: string
  label: string
  type: 'bar' | 'line'
  points: ChartPoint[]
}

type LegacyComparison = {
  label: string
  start: number
  end: number
}

function manifestScenes(manifest: Record<string, unknown> | null | undefined): ManifestScene[] {
  return Array.isArray(manifest?.scenes) ? manifest.scenes as ManifestScene[] : []
}

function stringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map((item) => String(item || '').trim()).filter(Boolean)
    : []
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

function sceneComposition(scene: ManifestScene): NonNullable<ManifestScene['composition']> {
  return recordValue(scene.composition) as NonNullable<ManifestScene['composition']>
}

function sceneData(scene: ManifestScene): Record<string, unknown> {
  return recordValue(sceneComposition(scene).data)
}

function chartSeriesFromData(data: Record<string, unknown>): ChartSeries[] {
  const rawSeries = Array.isArray(data.series) ? data.series : []
  return rawSeries.map((raw, index): ChartSeries | null => {
    const source = recordValue(raw)
    const rawPoints = Array.isArray(source.points) ? source.points : []
    const points = rawPoints.map((point): ChartPoint | null => {
      const parsedPoint = recordValue(point)
      const rawY = parsedPoint.y
      const y = rawY === null || rawY === undefined || rawY === ''
        ? null
        : Number(rawY)
      return {
        x: String(parsedPoint.x || ''),
        y: y === null || Number.isFinite(y) ? y : null,
      }
    }).filter((point): point is ChartPoint => Boolean(point?.x))
    if (points.length === 0) return null
    return {
      id: String(source.id || `series_${index + 1}`),
      label: String(source.label || `Series ${index + 1}`),
      type: source.type === 'line' ? 'line' : 'bar',
      points,
    }
  }).filter((series): series is ChartSeries => series !== null)
}

function parseLegacyComparison(value: string): LegacyComparison | null {
  const match = value.match(/^([^:]+):\s*\+?(-?\d+(?:\.\d+)?)\s*->\s*\+?(-?\d+(?:\.\d+)?)/)
  if (!match) return null
  const start = Number(match[2])
  const end = Number(match[3])
  if (!Number.isFinite(start) || !Number.isFinite(end)) return null
  return {
    label: match[1].trim(),
    start,
    end,
  }
}

function recoverLegacySeries(data: Record<string, unknown>, fallbackType: 'bar' | 'line'): ChartSeries[] {
  const dataPoints = stringList(data.data_points)
  const comparisons = dataPoints.map(parseLegacyComparison).filter((item): item is LegacyComparison => item !== null)
  if (comparisons.length === 0) return []

  if (fallbackType === 'line' && comparisons.length > 1) {
    return comparisons.map((comparison, index) => ({
      id: `legacy_${index + 1}`,
      label: comparison.label,
      type: 'line',
      points: [
        { x: 'Session 1', y: comparison.start },
        { x: 'Session 2', y: comparison.end },
      ],
    }))
  }

  const comparison = comparisons[0]
  return [{
    id: 'legacy_1',
    label: comparison.label,
    type: fallbackType,
    points: [
      { x: 'Session 1', y: comparison.start },
      { x: 'Session 2', y: comparison.end },
    ],
  }]
}

function normalizedChartSeries(scene: ManifestScene): ChartSeries[] {
  const data = sceneData(scene)
  const explicit = chartSeriesFromData(data)
  const hasNumericPoint = explicit.some((series) => series.points.some((point) => point.y !== null))
  if (hasNumericPoint) return explicit
  const fallbackType = explicit.some((series) => series.type === 'line') ? 'line' : 'bar'
  return recoverLegacySeries(data, fallbackType)
}

function yScale(value: number, min: number, max: number, chartHeight: number): number {
  if (max === min) return chartHeight / 2
  return chartHeight - ((value - min) / (max - min)) * chartHeight
}

function DataStagePreview({ scene }: { scene: ManifestScene }) {
  const data = sceneData(scene)
  const series = normalizedChartSeries(scene)
  const type = series.some((item) => item.type === 'line') ? 'line' : 'bar'
  const numericPoints = series.flatMap((item) => item.points.filter((point): point is ChartPoint & { y: number } => point.y !== null))
  const values = numericPoints.map((point) => point.y)
  const min = Math.min(0, ...values)
  const max = Math.max(1, ...values)
  const width = 960
  const height = 320
  const padding = { left: 96, right: 56, top: 40, bottom: 76 }
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom
  const labels = [
    ...stringList(data.referenceBands).map((item) => item),
    ...stringList(data.callouts).map((item) => item),
  ]
  const referenceLabels = Array.isArray(data.referenceBands)
    ? data.referenceBands.map((item) => String(recordValue(item).label || '').trim()).filter(Boolean)
    : []
  const calloutLabels = Array.isArray(data.callouts)
    ? data.callouts.map((item) => String(recordValue(item).label || '').trim()).filter(Boolean)
    : []
  const rawDataPoints = stringList(data.data_points)
  const nullLabels = chartSeriesFromData(data).flatMap((item) => item.points.filter((point) => point.y === null).map((point) => point.x))

  return (
    <div className="flex h-full w-full flex-col justify-center gap-[var(--space-3)] p-[var(--space-5)]" data-testid="three-data-stage">
      <div className="flex flex-wrap items-center gap-[var(--space-3)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
        {[...referenceLabels, ...calloutLabels, ...labels].map((label) => (
          <span key={label}>{label}</span>
        ))}
        {nullLabels.length > 0 && <span>n/a</span>}
        {rawDataPoints.map((label) => <span key={label}>{label}</span>)}
      </div>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Data stage preview" className="max-w-full">
        <rect x="0" y="0" width={width} height={height} rx="24" fill="#1c1c1c" />
        <line x1={padding.left} y1={padding.top + chartHeight} x2={padding.left + chartWidth} y2={padding.top + chartHeight} stroke="#717171" strokeWidth="2" />
        <line x1={padding.left} y1={padding.top} x2={padding.left} y2={padding.top + chartHeight} stroke="#717171" strokeWidth="2" />
        {type === 'bar' && series[0]?.points.filter((point): point is ChartPoint & { y: number } => point.y !== null).map((point, index, points) => {
          const slot = chartWidth / Math.max(points.length, 1)
          const barWidth = Math.max(46, slot * 0.42)
          const x = padding.left + (slot * index) + (slot - barWidth) / 2
          const scaledY = padding.top + yScale(point.y, min, max, chartHeight)
          const barHeight = Math.max(24, padding.top + chartHeight - scaledY)
          return (
            <g key={`${point.x}-${index}`}>
              <rect data-testid="three-data-stage-bar" x={x} y={padding.top + chartHeight - barHeight} width={barWidth} height={barHeight} rx="8" fill="#126e51" />
              <text x={x + barWidth / 2} y={padding.top + chartHeight + 34} textAnchor="middle" fill="#e0e0e0" fontSize="18">{point.x}</text>
              <text x={x + barWidth / 2} y={padding.top + chartHeight - barHeight - 14} textAnchor="middle" fill="#fede1c" fontSize="18">{point.y}</text>
            </g>
          )
        })}
        {type === 'line' && series.map((item, seriesIndex) => {
          const points = item.points.filter((point): point is ChartPoint & { y: number } => point.y !== null)
          const pathDefinition = points.map((point, index) => {
            const x = padding.left + (chartWidth * index) / Math.max(points.length - 1, 1)
            const y = padding.top + yScale(point.y, min, max, chartHeight)
            return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
          }).join(' ')
          const color = seriesIndex % 2 === 0 ? '#28ffbb' : '#fede1c'
          return (
            <g key={item.id}>
              <path data-testid="three-data-stage-line" d={pathDefinition} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
              {points.map((point, index) => {
                const x = padding.left + (chartWidth * index) / Math.max(points.length - 1, 1)
                const y = padding.top + yScale(point.y, min, max, chartHeight)
                return (
                  <g key={`${item.id}-${point.x}`}>
                    <circle data-testid="three-data-stage-line-point" cx={x} cy={y} r="8" fill={color} />
                    {seriesIndex === 0 && (
                      <text x={x} y={padding.top + chartHeight + 34} textAnchor="middle" fill="#e0e0e0" fontSize="18">{point.x}</text>
                    )}
                    <text x={x} y={y - 18} textAnchor="middle" fill="#ffffff" fontSize="18">{point.y}</text>
                  </g>
                )
              })}
              <text x={padding.left} y={24 + seriesIndex * 24} fill={color} fontSize="18">{item.label}</text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function shouldShowText(scene: ManifestScene): boolean {
  const composition = sceneComposition(scene)
  const family = String(composition.family || '')
  const mode = String(composition.mode || '')
  const manifestation = String(composition.manifestation || '')
  if (family === 'three_data_stage') return false
  if (family === 'static_media' && mode === 'none') return false
  if (manifestation === 'authored_image' && String(scene.textLayerKind || '') === 'none') return false
  return true
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
  const scenes = manifestScenes(manifest)
  const scene = scenes[0] ?? null
  const composition = scene ? sceneComposition(scene) : {}
  const family = String(composition.family || '')
  const imageUrl = typeof scene?.imageUrl === 'string' ? scene.imageUrl : null
  const textItems = scene && shouldShowText(scene)
    ? stringList(scene.onScreenText).slice(0, 4)
    : []

  return (
    <div
      data-testid="remotion-player-surface"
      className={clsx('relative flex items-center justify-center overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--surface-void)]', className)}
      style={{ minHeight: height }}
    >
      {scene && family === 'three_data_stage' ? (
        <DataStagePreview scene={scene} />
      ) : scene ? (
        <>
          {imageUrl && (
            <img
              src={imageUrl}
              alt=""
              className="absolute inset-0 h-full w-full object-cover"
              style={{ transform: 'scale(1)' }}
            />
          )}
          {!imageUrl && (
            <div className="absolute inset-0 bg-[var(--surface-stage)]" />
          )}
          {textItems.length > 0 && (
            <div className="relative z-10 flex h-full w-full flex-col justify-end gap-[var(--space-2)] bg-gradient-to-t from-black/70 via-black/20 to-transparent p-[var(--space-5)]">
              {textItems.map((item, index) => (
                <div
                  key={item}
                  className={index === 0 ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: index === 0 ? 'var(--text-2xl)' : 'var(--text-md)',
                    fontWeight: index === 0 ? 'var(--weight-bold)' : 'var(--weight-medium)',
                  }}
                >
                  {item}
                </div>
              ))}
            </div>
          )}
          <div
            className="absolute right-[var(--space-3)] top-[var(--space-3)] rounded-full border border-[var(--border-subtle)] bg-black/60 px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-tertiary)]"
            style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)' }}
          >
            {width && compositionHeight ? `${width}x${compositionHeight}` : 'manifest'}
            {fps ? ` / ${fps}fps` : ''}
          </div>
        </>
      ) : (
        <div className="flex max-w-[32rem] flex-col gap-[var(--space-2)] px-[var(--space-5)] py-[var(--space-6)] text-center">
          <div
            className="text-[var(--text-primary)]"
            style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-md)', fontWeight: 'var(--weight-semibold)' }}
          >
            Remotion preview unavailable
          </div>
          <div
            className="text-[var(--text-tertiary)]"
            style={{ fontSize: 'var(--text-sm)' }}
          >
            The optional Remotion player packages are not installed in this build. A manifest preview appears here whenever render data is available.
          </div>
          {(width || compositionHeight || fps || scenes.length > 0) && (
            <div
              className="mt-[var(--space-2)] text-[var(--text-tertiary)]"
              style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)' }}
            >
              {width && compositionHeight ? `${width}x${compositionHeight}` : 'manifest loaded'}
              {fps ? ` / ${fps}fps` : ''}
              {scenes.length > 0 ? ` / ${scenes.length} scene${scenes.length === 1 ? '' : 's'}` : ''}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
