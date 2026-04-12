import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { FileTriggerButton } from '../../components/primitives/FileTriggerButton.tsx'
import { useReducedMotion, transitions } from '../../design-system/motion'
import { formatImageActionLabel, formatImageActionSummary, formatImageActionTime, imageActionStatusClass } from '../../lib/image-action-history.ts'
import type {
  ImageActionHistoryEntry,
  Scene,
  ThreeDataStageCallout,
  ThreeDataStageCompositionData,
  ThreeDataStagePanel,
  ThreeDataStagePoint,
  ThreeDataStageReferenceBand,
  ThreeDataStageSeries,
} from '../../lib/schemas/plan.ts'
import { projectMediaUrl } from '../../lib/media-url.ts'
import { resolveRenderOutputFilename } from '../../lib/render-output.ts'
import { sceneHasRenderableAudio } from '../../lib/scene-media.ts'
import {
  CUSTOM_REPLICATE_VIDEO_MODEL,
  DEFAULT_REPLICATE_CINEMATIC_VIDEO_MODEL,
  REPLICATE_VIDEO_MODEL_OPTIONS,
  getReplicateVideoModelPreset,
  resolveReplicateVideoRoute,
} from '../../lib/video-generation.ts'

type VoiceOption = {
  value: string
  label: string
  description: string
}

type CompositionFamilyOption = {
  value: string
  label: string
  motionAllowed: boolean
}

const COMPOSITION_FAMILY_OPTIONS: CompositionFamilyOption[] = [
  { value: 'static_media', label: 'Static media', motionAllowed: false },
  { value: 'media_pan', label: 'Media pan', motionAllowed: false },
  { value: 'software_demo_focus', label: 'Software demo focus', motionAllowed: false },
  { value: 'kinetic_statements', label: 'Kinetic statements', motionAllowed: true },
  { value: 'bullet_stack', label: 'Bullet stack', motionAllowed: true },
  { value: 'quote_focus', label: 'Quote focus', motionAllowed: true },
  { value: 'three_data_stage', label: 'Three data stage', motionAllowed: true },
  { value: 'surreal_tableau_3d', label: 'Surreal tableau 3D', motionAllowed: true },
  { value: 'cover_hook', label: 'Cover hook', motionAllowed: true },
  { value: 'orientation', label: 'Orientation', motionAllowed: true },
  { value: 'synthesis_summary', label: 'Synthesis summary', motionAllowed: true },
  { value: 'closing_cta', label: 'Closing CTA', motionAllowed: true },
  { value: 'clinical_explanation', label: 'Clinical explanation', motionAllowed: true },
  { value: 'metric_improvement', label: 'Metric improvement', motionAllowed: true },
  { value: 'brain_region_focus', label: 'Brain region focus', motionAllowed: true },
  { value: 'metric_comparison', label: 'Metric comparison', motionAllowed: true },
  { value: 'timeline_progression', label: 'Timeline progression', motionAllowed: true },
  { value: 'analogy_metaphor', label: 'Analogy / metaphor', motionAllowed: true },
]

const SURREAL_COPY_TREATMENT_OPTIONS = [
  { value: 'none', label: 'No copy' },
  { value: 'kicker_chip', label: 'Kicker chip' },
  { value: 'lower_third', label: 'Lower third' },
]

const THREE_DATA_STAGE_LAYOUT_OPTIONS = [
  { value: 'bars_with_delta', label: 'Bars with delta' },
  { value: 'bars_with_band', label: 'Bars with band' },
  { value: 'line_with_band', label: 'Line with band' },
  { value: 'line_with_multi_band', label: 'Line with multi-band' },
  { value: 'line_with_zones', label: 'Line with zones' },
]

const THREE_DATA_STAGE_PALETTE_OPTIONS = [
  { value: 'teal_on_navy', label: 'Teal on navy' },
  { value: 'amber_on_navy', label: 'Amber on navy' },
  { value: 'teal_amber_on_charcoal', label: 'Teal and amber on charcoal' },
  { value: 'multi_zone_on_charcoal', label: 'Multi-zone on charcoal' },
]

interface SceneInspectorProps {
  scene: Scene | null
  project: string
  sceneIndex: number
  actions?: ReactNode
  onSceneChange: (updated: Scene) => void
  onUploadImage: (file: File) => void
  onUploadVideo: (file: File) => void
  uploadPending?: boolean
  uploadError?: string | null
  imageEditModel?: string | null
  imageEditModels?: string[]
  onImageEditModelChange?: (model: string) => void
  imageGenerationProvider?: string | null
  imageGenerationModel?: string | null
  requestPreview?: Record<string, unknown> | null
  actionTrace?: {
    title: string
    endpoint: string
    request: Record<string, unknown>
    status: 'idle' | 'running' | 'succeeded' | 'error'
    happenedAt: string
    error?: string | null
  } | null
  imageActionHistory?: ImageActionHistoryEntry[]
  onEditImage: (feedback: string) => void
  imageEditPending?: boolean
  imageEditError?: string | null
  onGenerateImage: () => void
  videoGenerationProvider?: string | null
  videoGenerationModel?: string | null
  videoModelSelectionMode?: string | null
  videoQualityMode?: string | null
  videoGenerateAudio?: boolean
  videoProviders?: string[]
  onVideoProfileChange?: (patch: Record<string, unknown>) => void
  onGenerateVideo: () => void
  videoGeneratePending?: boolean
  videoGenerateError?: string | null
  onGenerateAudio: () => void
  ttsProfile?: Record<string, unknown> | null
  ttsProviders?: Record<string, string>
  ttsVoiceOptions?: Record<string, VoiceOption[]>
  onGenerateAllAssets?: () => void
  generateAllPending?: boolean
  onRenderVideo?: () => void
  renderPending?: boolean
  renderDisabled?: boolean
  renderWorkspaceHref?: string | null
  projectVideoPath?: string | null
  projectVideoExists?: boolean
  renderReadinessCopy?: string | null
  onRunAgentDemo?: () => void
  onRunAgentDemoPass?: () => void
  agentDemoPending?: boolean
  agentDemoJob?: {
    job_id: string
    status: string
    progress_label?: string
    progress_detail?: string
    suggestion?: string
  } | null
  agentDemoLog?: string | null
  onRefinePrompt: (feedback: string) => void
  onRefineNarration: (feedback: string) => void
  onGeneratePreview: () => void
  saving: boolean
  assetProgress?: {
    label: string
    detail: string
    progress?: number | null
    indeterminate?: boolean
  } | null
  visualProgress?: {
    label: string
    detail: string
    progress?: number | null
    indeterminate?: boolean
  } | null
  audioProgress?: {
    label: string
    detail: string
    progress?: number | null
    indeterminate?: boolean
  } | null
  previewProgress?: {
    label: string
    detail: string
    progress?: number | null
    indeterminate?: boolean
  } | null
}

function ActionButton({
  onClick,
  disabled,
  children,
  variant = 'default',
}: {
  onClick: () => void
  disabled?: boolean
  children: React.ReactNode
  variant?: 'default' | 'primary'
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'scene-inspector__action-button',
        'rounded-[var(--radius-md)] border outline-none cursor-pointer',
        'transition-colors duration-[150ms]',
        'focus-visible:shadow-[var(--focus-ring)]',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        variant === 'primary'
          ? 'border-[var(--border-accent)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/20'
          : 'border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)]',
      )}
      style={{
        padding: `var(--space-2) var(--space-3)`,
        fontSize: 'var(--text-xs)',
        fontFamily: 'var(--font-body)',
        fontWeight: 'var(--weight-medium)',
      }}
    >
      {children}
    </button>
  )
}

function ActionLink({
  href,
  children,
  variant = 'default',
}: {
  href: string
  children: React.ReactNode
  variant?: 'default' | 'primary'
}) {
  return (
    <Link
      to={href}
      className={clsx(
        'scene-inspector__action-button',
        'rounded-[var(--radius-md)] border outline-none cursor-pointer no-underline',
        'transition-colors duration-[150ms]',
        'focus-visible:shadow-[var(--focus-ring)]',
        variant === 'primary'
          ? 'border-[var(--border-accent)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/20'
          : 'border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)]',
      )}
      style={{
        padding: `var(--space-2) var(--space-3)`,
        fontSize: 'var(--text-xs)',
        fontFamily: 'var(--font-body)',
        fontWeight: 'var(--weight-medium)',
      }}
    >
      {children}
    </Link>
  )
}

function SectionLabel({ title, meta }: { title: string; meta?: string }) {
  return (
    <div className="scene-inspector__section-label flex min-w-0 items-center justify-between gap-[var(--space-2)]">
      <span
        className="scene-inspector__section-title text-[var(--text-secondary)]"
        style={{
          fontSize: 'var(--text-xs)',
          fontWeight: 'var(--weight-medium)',
          fontFamily: 'var(--font-body)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}
      >
        {title}
      </span>
      {meta && (
        <span
          className="scene-inspector__section-meta text-[var(--text-tertiary)]"
          style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
        >
          {meta}
        </span>
      )}
    </div>
  )
}

function InspectorSection({
  id,
  title,
  meta,
  open,
  onToggle,
  children,
}: {
  id: string
  title: string
  meta?: string
  open: boolean
  onToggle: () => void
  children: ReactNode
}) {
  const reducedMotion = useReducedMotion()

  return (
    <GlassPanel variant="inset" padding="sm" rounded="lg" className="overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={`${id}-content`}
        className="flex w-full items-center justify-between gap-[var(--space-3)] rounded-[var(--radius-md)] bg-transparent px-[var(--space-1)] py-[var(--space-1)] text-left outline-none focus-visible:shadow-[var(--focus-ring)]"
      >
        <SectionLabel title={title} meta={meta} />
        <span
          aria-hidden="true"
          className="text-[var(--text-tertiary)]"
          style={{
            transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: reducedMotion ? 'none' : `transform ${transitions.dockSlide}`,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M5 3.5L9 7L5 10.5" />
          </svg>
        </span>
      </button>
      <div
        id={`${id}-content`}
        className="inspector-section__content"
        data-open={open}
        hidden={!open}
        aria-hidden={!open}
      >
        <div className="pt-[var(--space-3)]">{children}</div>
      </div>
    </GlassPanel>
  )
}

function InlineProgress({
  label,
  detail,
  progress,
  indeterminate = false,
}: {
  label: string
  detail: string
  progress?: number | null
  indeterminate?: boolean
}) {
  const bounded = Math.max(0, Math.min(progress ?? 0.08, 1))

  return (
    <div className="scene-inspector__progress-stack" role="status" aria-live="polite">
      <div className="scene-inspector__progress-bar" aria-hidden="true">
        <div
          className={clsx(
            'scene-inspector__progress-fill',
            indeterminate && 'scene-inspector__progress-fill--indeterminate',
          )}
          style={indeterminate ? undefined : { width: `${Math.max(bounded * 100, 6)}%` }}
          role={indeterminate ? undefined : 'progressbar'}
          aria-valuenow={indeterminate ? undefined : Math.round(bounded * 100)}
          aria-valuemin={indeterminate ? undefined : 0}
          aria-valuemax={indeterminate ? undefined : 100}
        />
      </div>
      <div className="flex flex-col gap-[2px]">
        <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}>
          {label}
        </span>
        <span className="text-[var(--text-tertiary)]" style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
          {detail}
        </span>
      </div>
    </div>
  )
}

function defaultCompositionModeForFamily(family: string): 'none' | 'overlay' | 'native' {
  const normalized = String(family || '').trim()
  if (normalized === 'software_demo_focus') {
    return 'overlay'
  }
  if ([
    'kinetic_statements', 'bullet_stack', 'quote_focus', 'three_data_stage', 'surreal_tableau_3d',
    'cover_hook', 'orientation', 'synthesis_summary', 'closing_cta', 'clinical_explanation',
    'metric_improvement', 'brain_region_focus', 'metric_comparison', 'timeline_progression', 'analogy_metaphor',
  ].includes(normalized)) {
    return 'native'
  }
  return 'none'
}

function isSurrealTableauFamily(family: string): boolean {
  return String(family || '').trim() === 'surreal_tableau_3d'
}

function isThreeDataStageFamily(family: string): boolean {
  return String(family || '').trim() === 'three_data_stage'
}

const CLINICAL_TEMPLATE_FAMILIES = new Set([
  'cover_hook',
  'orientation',
  'synthesis_summary',
  'closing_cta',
  'clinical_explanation',
  'metric_improvement',
  'brain_region_focus',
  'metric_comparison',
  'timeline_progression',
  'analogy_metaphor',
])

function isClinicalTemplateFamily(family: string): boolean {
  return CLINICAL_TEMPLATE_FAMILIES.has(String(family || '').trim())
}

function familyRequiresMotionScene(family: string, mode?: string): boolean {
  const normalizedFamily = String(family || '').trim()
  const normalizedMode = String(mode || defaultCompositionModeForFamily(normalizedFamily)).trim().toLowerCase()
  if (normalizedMode !== 'native') {
    return false
  }
  return COMPOSITION_FAMILY_OPTIONS.some((option) => option.value === normalizedFamily && option.motionAllowed)
}

function inferSurrealLayoutVariant(scene: Scene): 'orbit_tableau' | 'symbolic_duet' {
  const text = [
    scene.title,
    scene.visual_prompt,
    scene.staging_notes,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return ['orbit', 'orbiting', 'orbital', 'dolly around'].some((hint) => text.includes(hint))
    ? 'orbit_tableau'
    : 'symbolic_duet'
}

function inferThreeDataStageLayoutVariant(scene: Scene): string {
  const text = [
    scene.title,
    scene.visual_prompt,
    scene.staging_notes,
    scene.narration,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()

  if (text.includes('zone') || text.includes('above range') || text.includes('below range')) {
    return 'line_with_zones'
  }
  if (text.includes('multi-band') || text.includes('multi band')) {
    return 'line_with_multi_band'
  }
  if (text.includes('ratio') || text.includes('trend') || text.includes('line') || text.includes('variable') || text.includes('across sessions')) {
    return 'line_with_band'
  }
  if (text.includes('faster') || text.includes('delta') || text.includes('improvement')) {
    return 'bars_with_delta'
  }
  return 'bars_with_band'
}

function parseOptionalNumber(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null
  }
  if (typeof value === 'string' && value.trim() === '') {
    return null
  }
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function numberInputValue(value: unknown): string {
  const parsed = parseOptionalNumber(value)
  return parsed === null ? '' : String(parsed)
}

function fallbackThreeDataStageLabels(scene: Scene): string[] {
  if (Array.isArray(scene.data_points) && scene.data_points.length > 0) {
    return scene.data_points.map((item) => String(item).trim()).filter(Boolean)
  }
  if (Array.isArray(scene.on_screen_text) && scene.on_screen_text.length > 0) {
    return scene.on_screen_text.map((item) => String(item).trim()).filter(Boolean).slice(0, 4)
  }
  return []
}

function normalizeThreeDataStagePoint(
  entry: unknown,
  index: number,
  fallbackX: string,
): ThreeDataStagePoint {
  const item = entry && typeof entry === 'object' ? entry as Record<string, unknown> : {}
  const x = String(item.x || fallbackX || `Point ${index + 1}`).trim() || `Point ${index + 1}`
  const label = String(item.label || '').trim()
  return {
    x,
    y: parseOptionalNumber(item.y),
    label: label || undefined,
  }
}

function normalizeThreeDataStageData(scene: Scene, raw: NonNullable<Scene['composition']>['data']): ThreeDataStageCompositionData {
  const fallbackLabels = fallbackThreeDataStageLabels(scene)
  const base = raw && typeof raw === 'object' && !Array.isArray(raw)
    ? { ...(raw as Record<string, unknown>) }
    : {}
  const rawSeries = Array.isArray(base.series) ? base.series : []
  const series: ThreeDataStageSeries[] = rawSeries.length > 0
    ? rawSeries.map((entry, index) => {
        const item = entry && typeof entry === 'object' ? entry as Record<string, unknown> : {}
        const points = Array.isArray(item.points) ? item.points : []
        return {
          id: String(item.id || `series_${index + 1}`).trim() || `series_${index + 1}`,
          label: String(item.label || scene.title || `Series ${index + 1}`).trim() || `Series ${index + 1}`,
          type: String(item.type || 'bar').trim() === 'line' ? 'line' : 'bar',
          points: (points.length > 0 ? points : fallbackLabels.map((label) => ({ x: label, y: null }))).map((point, pointIndex) =>
            normalizeThreeDataStagePoint(point, pointIndex, fallbackLabels[pointIndex] || `Point ${pointIndex + 1}`),
          ),
        }
      })
    : [{
        id: 'series_1',
        label: scene.title || 'Series 1',
        type: inferThreeDataStageLayoutVariant(scene).startsWith('line') ? 'line' : 'bar',
        points: (fallbackLabels.length > 0 ? fallbackLabels : ['Point 1', 'Point 2', 'Point 3']).map((label) => ({
          x: label,
          y: null,
          label: undefined,
        })),
      }]

  const referenceBands: ThreeDataStageReferenceBand[] = Array.isArray(base.referenceBands)
    ? base.referenceBands.map((entry, index) => {
        const item = entry && typeof entry === 'object' ? entry as Record<string, unknown> : {}
        const xRange = Array.isArray(item.xRange) && item.xRange.length >= 2
          ? [String(item.xRange[0] || '').trim(), String(item.xRange[1] || '').trim()] as [string, string]
          : undefined
        return {
          id: String(item.id || `band_${index + 1}`).trim() || `band_${index + 1}`,
          label: String(item.label || '').trim() || 'Reference range',
          yMin: parseOptionalNumber(item.yMin),
          yMax: parseOptionalNumber(item.yMax),
          xRange,
        }
      })
    : []

  const callouts: ThreeDataStageCallout[] = Array.isArray(base.callouts)
    ? base.callouts.map((entry, index) => {
        const item = entry && typeof entry === 'object' ? entry as Record<string, unknown> : {}
        return {
          id: String(item.id || `callout_${index + 1}`).trim() || `callout_${index + 1}`,
          label: String(item.label || '').trim() || 'Callout',
          x: String(item.x || '').trim() || undefined,
          y: parseOptionalNumber(item.y),
          fromX: String(item.fromX || '').trim() || undefined,
          toX: String(item.toX || '').trim() || undefined,
        }
      })
    : []

  const panels: ThreeDataStagePanel[] | undefined = Array.isArray(base.panels) && base.panels.length > 0
    ? base.panels.map((rawPanel, panelIndex) => {
        const panel = rawPanel && typeof rawPanel === 'object' ? rawPanel as Record<string, unknown> : {}
        const panelSeries = Array.isArray(panel.series) ? panel.series : []
        const panelBands = Array.isArray(panel.referenceBands) ? panel.referenceBands : []
        return {
          id: String(panel.id || `panel_${panelIndex + 1}`).trim(),
          title: String(panel.title || `Panel ${panelIndex + 1}`).trim(),
          yAxisLabel: String(panel.yAxisLabel || '').trim() || undefined,
          series: panelSeries.length > 0
            ? panelSeries.map((entry, sIdx) => {
                const item = entry && typeof entry === 'object' ? entry as Record<string, unknown> : {}
                const points = Array.isArray(item.points) ? item.points : []
                return {
                  id: String(item.id || `series_${sIdx + 1}`).trim() || `series_${sIdx + 1}`,
                  label: String(item.label || `Series ${sIdx + 1}`).trim(),
                  type: String(item.type || 'bar').trim() === 'line' ? 'line' : 'bar',
                  points: points.map((point, pIdx) =>
                    normalizeThreeDataStagePoint(point, pIdx, `Point ${pIdx + 1}`),
                  ),
                }
              })
            : [{
                id: 'series_1',
                label: String(panel.title || `Panel ${panelIndex + 1}`).trim(),
                type: 'bar' as const,
                points: [{ x: 'Point 1', y: null }],
              }],
          referenceBands: panelBands.map((entry, bIdx) => {
            const item = entry && typeof entry === 'object' ? entry as Record<string, unknown> : {}
            return {
              id: String(item.id || `band_${bIdx + 1}`).trim(),
              label: String(item.label || 'Reference range').trim(),
              yMin: parseOptionalNumber(item.yMin),
              yMax: parseOptionalNumber(item.yMax),
            }
          }),
        }
      })
    : undefined

  return {
    ...base,
    xAxisLabel: String(base.xAxisLabel || 'Category').trim() || 'Category',
    yAxisLabel: String(base.yAxisLabel || 'Value').trim() || 'Value',
    data_points: Array.isArray(base.data_points)
      ? base.data_points.map((item) => String(item).trim()).filter(Boolean)
      : fallbackLabels,
    series,
    referenceBands,
    callouts,
    panels,
  }
}

function defaultTextCompositionProps(scene: Scene): Record<string, unknown> {
  const lines = (scene.on_screen_text ?? []).filter((line) => String(line || '').trim())
  return {
    headline: lines[0] || scene.title || 'Motion beat',
    body: lines.slice(1, 3).join(' ') || scene.narration?.slice(0, 180) || '',
    kicker: scene.title || 'Cathode',
    bullets: lines.slice(0, 4),
    accent: '',
  }
}

function defaultSurrealCompositionProps(scene: Scene, currentProps: Record<string, unknown>): Record<string, unknown> {
  const layoutVariant = String(currentProps.layoutVariant || inferSurrealLayoutVariant(scene))
  const paletteWords = Array.isArray(currentProps.paletteWords)
    ? currentProps.paletteWords.map((item) => String(item)).filter(Boolean)
    : typeof currentProps.paletteWords === 'string'
      ? String(currentProps.paletteWords).split(',').map((item) => item.trim()).filter(Boolean)
      : ['deep indigo', 'warm amber', 'ivory', 'brass']
  return {
    layoutVariant,
    heroObject: String(currentProps.heroObject || scene.title || 'central hero object'),
    secondaryObject: String(currentProps.secondaryObject || 'symbolic counterform'),
    orbitingObject: String(currentProps.orbitingObject || (layoutVariant === 'orbit_tableau' ? 'orbiting forms' : '')),
    orbitCount: Number(currentProps.orbitCount ?? (layoutVariant === 'orbit_tableau' ? 6 : 0)),
    environmentBackdrop: String(currentProps.environmentBackdrop || scene.staging_notes || 'dreamlike cinematic chamber'),
    ambientDetails: String(currentProps.ambientDetails || ''),
    paletteWords,
    cameraMove: String(currentProps.cameraMove || (layoutVariant === 'orbit_tableau' ? 'slow circular camera orbit' : 'slow deliberate drift')),
    copyTreatment: String(currentProps.copyTreatment || 'none'),
    motionNotes: String(currentProps.motionNotes || scene.staging_notes || ''),
  }
}

function defaultThreeDataStageProps(scene: Scene, currentProps: Record<string, unknown>): Record<string, unknown> {
  return {
    headline: String(currentProps.headline || scene.title || 'Data stage'),
    kicker: String(currentProps.kicker || scene.title || 'Data stage'),
    layoutVariant: String(currentProps.layoutVariant || inferThreeDataStageLayoutVariant(scene)),
    palette: String(currentProps.palette || 'teal_on_navy'),
  }
}

function propsForCompositionFamily(scene: Scene, family: string, currentProps: Record<string, unknown>): Record<string, unknown> {
  if (isThreeDataStageFamily(family)) {
    return defaultThreeDataStageProps(scene, currentProps)
  }
  if (isSurrealTableauFamily(family)) {
    return defaultSurrealCompositionProps(scene, currentProps)
  }
  return {
    ...defaultTextCompositionProps(scene),
    ...currentProps,
  }
}

function resolveMotionState(currentScene: Scene) {
  const compositionProps = typeof currentScene.composition?.props === 'object' && currentScene.composition?.props
    ? currentScene.composition.props
    : {}
  const motionProps = typeof currentScene.motion?.props === 'object' && currentScene.motion?.props
    ? currentScene.motion.props
    : compositionProps
  return {
    template_id: String(currentScene.composition?.family || currentScene.motion?.template_id || 'kinetic_title'),
    props: compositionProps && Object.keys(compositionProps).length > 0 ? compositionProps : motionProps,
    render_path: currentScene.composition?.render_path ?? currentScene.motion?.render_path ?? null,
    preview_path: currentScene.composition?.preview_path ?? currentScene.motion?.preview_path ?? null,
    rationale: String(currentScene.composition?.rationale || currentScene.motion?.rationale || ''),
  }
}

function resolveCompositionState(currentScene: Scene) {
  const motionState = resolveMotionState(currentScene)
  return {
    family: String(currentScene.composition?.family || (currentScene.scene_type === 'motion' ? motionState.template_id : 'static_media')),
    mode: String(currentScene.composition?.mode || (currentScene.scene_type === 'motion' ? 'native' : 'none')),
    transition_after: currentScene.composition?.transition_after ?? null,
    props: typeof currentScene.composition?.props === 'object' && currentScene.composition?.props ? currentScene.composition.props : {},
    data: currentScene.composition?.data ?? {},
    render_path: currentScene.composition?.render_path ?? null,
    preview_path: currentScene.composition?.preview_path ?? null,
    rationale: String(currentScene.composition?.rationale || ''),
  }
}

export function SceneInspector({
  scene,
  project,
  sceneIndex,
  actions,
  onSceneChange,
  onUploadImage,
  onUploadVideo,
  uploadPending,
  uploadError,
  imageEditModel,
  imageEditModels = [],
  onImageEditModelChange,
  imageGenerationProvider,
  imageGenerationModel,
  requestPreview,
  actionTrace,
  imageActionHistory = [],
  onEditImage,
  imageEditPending,
  imageEditError,
  onGenerateImage,
  videoGenerationProvider,
  videoGenerationModel,
  videoModelSelectionMode: videoModelSelectionModeProp,
  videoQualityMode,
  videoGenerateAudio,
  videoProviders = [],
  onVideoProfileChange,
  onGenerateVideo,
  videoGeneratePending,
  videoGenerateError,
  onGenerateAudio,
  ttsProfile,
  ttsProviders = {},
  ttsVoiceOptions = {},
  onGenerateAllAssets,
  generateAllPending,
  onRenderVideo,
  renderPending,
  renderDisabled,
  renderWorkspaceHref,
  projectVideoPath,
  projectVideoExists,
  renderReadinessCopy,
  onRunAgentDemo,
  onRunAgentDemoPass,
  agentDemoPending,
  agentDemoJob,
  agentDemoLog,
  onRefinePrompt,
  onRefineNarration,
  onGeneratePreview,
  saving,
  assetProgress,
  visualProgress,
  audioProgress,
  previewProgress,
}: SceneInspectorProps) {
  const [promptFeedbackOpen, setPromptFeedbackOpen] = useState(false)
  const [narrationFeedbackOpen, setNarrationFeedbackOpen] = useState(false)
  const [imageEditOpen, setImageEditOpen] = useState(false)
  const [promptFeedback, setPromptFeedback] = useState('')
  const [narrationFeedback, setNarrationFeedback] = useState('')
  const [imageEditFeedback, setImageEditFeedback] = useState('')
  const [localUploadError, setLocalUploadError] = useState<string | null>(null)
  const [replicateCustomModelOpen, setReplicateCustomModelOpen] = useState(false)
  const sceneDraftRef = useRef(scene)
  const [sectionOpen, setSectionOpen] = useState({
    visual: true,
    narration: true,
    prompt: true,
    text: true,
    audio: true,
    preview: false,
    operator: false,
  })
  const replicateModelPreset = getReplicateVideoModelPreset(videoGenerationModel)

  useEffect(() => {
    if (videoGenerationProvider !== 'replicate') {
      setReplicateCustomModelOpen(false)
      return
    }
    setReplicateCustomModelOpen(replicateModelPreset === CUSTOM_REPLICATE_VIDEO_MODEL)
  }, [replicateModelPreset, videoGenerationProvider])

  useEffect(() => {
    sceneDraftRef.current = scene
  }, [scene])

  if (!scene) {
    return (
      <GlassPanel
        variant="default"
        padding="lg"
        className="flex h-full items-center justify-center"
      >
        <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-sm)' }}>
          Select a scene to inspect
        </span>
      </GlassPanel>
    )
  }

  const update = (patch: Partial<Scene>) => {
    const nextScene = { ...(sceneDraftRef.current ?? scene), ...patch }
    sceneDraftRef.current = nextScene
    onSceneChange(nextScene)
  }

  const toggleSection = (key: keyof typeof sectionOpen) => {
    setSectionOpen((current) => ({ ...current, [key]: !current[key] }))
  }
  const activeUploadError = uploadError ?? localUploadError
  const activeImageEditError = imageEditError ?? null
  const latestProjectVideoUrl = projectVideoExists === false
    ? null
    : projectVideoPath && projectVideoPath !== '' && projectVideoPath != null
    ? projectMediaUrl(project, projectVideoPath)
    : null
  const latestProjectVideoFilename = resolveRenderOutputFilename({
    videoPath: projectVideoPath,
    projectId: project,
  })

  const submitPromptFeedback = () => {
    const value = promptFeedback.trim()
    if (!value) return
    onRefinePrompt(value)
    setPromptFeedback('')
    setPromptFeedbackOpen(false)
  }

  const submitNarrationFeedback = () => {
    const value = narrationFeedback.trim()
    if (!value) return
    onRefineNarration(value)
    setNarrationFeedback('')
    setNarrationFeedbackOpen(false)
  }

  const submitImageEdit = () => {
    const value = imageEditFeedback.trim()
    if (!value) return
    onEditImage(value)
    setImageEditFeedback('')
    setImageEditOpen(false)
  }

  const motionState = resolveMotionState(scene)
  const compositionState = resolveCompositionState(scene)
  const updateComposition = (patch: Partial<NonNullable<Scene['composition']>>) => {
    const currentScene = sceneDraftRef.current ?? scene
    const currentComposition = resolveCompositionState(currentScene)
    const requestedFamily = String(patch.family || currentComposition.family || '').trim() || currentComposition.family
    const currentProps = typeof currentComposition.props === 'object' && currentComposition.props
      ? currentComposition.props
      : {}
    const currentData = currentComposition.data
    const patchProps = (patch.props as Record<string, unknown> | undefined) ?? {}
    const familyChanged = requestedFamily !== currentComposition.family
    const nextProps = familyChanged
      ? {
          ...propsForCompositionFamily(currentScene, requestedFamily, currentProps),
          ...patchProps,
        }
      : {
          ...currentProps,
          ...patchProps,
        }
    const nextData = (() => {
      if (isThreeDataStageFamily(requestedFamily)) {
        const normalized = normalizeThreeDataStageData(currentScene, currentData)
        const patchData = patch.data && typeof patch.data === 'object' && !Array.isArray(patch.data)
          ? patch.data as Record<string, unknown>
          : {}
        return normalizeThreeDataStageData(currentScene, {
          ...normalized,
          ...patchData,
        })
      }
      if (patch.data !== undefined) {
        return patch.data
      }
      return currentData
    })()
    const nextComposition = {
      ...currentComposition,
      ...patch,
      family: requestedFamily,
      props: nextProps,
      data: nextData,
    }
    const forceMotionScene = familyRequiresMotionScene(requestedFamily, String(nextComposition.mode || ''))
    const nextSceneType = forceMotionScene ? 'motion' : currentScene.scene_type
    const currentMotion = resolveMotionState(currentScene)
    const nextScene = {
      ...currentScene,
      scene_type: nextSceneType,
      image_path: forceMotionScene ? null : currentScene.image_path,
      video_path: forceMotionScene ? null : currentScene.video_path,
      preview_path: forceMotionScene ? null : currentScene.preview_path,
      composition: nextComposition,
      motion: nextComposition.mode === 'native' || nextSceneType === 'motion'
        ? {
            ...currentMotion,
            template_id: String(nextComposition.family || currentMotion.template_id || 'kinetic_title'),
            props: nextComposition.props,
            render_path: nextComposition.render_path ?? null,
            preview_path: nextComposition.preview_path ?? null,
            rationale: String(nextComposition.rationale || ''),
          }
        : currentScene.motion,
    }
    sceneDraftRef.current = nextScene
    onSceneChange(nextScene)
  }

  const wordCount = scene.narration ? scene.narration.trim().split(/\s+/).filter(Boolean).length : 0
  const sceneType = scene.scene_type ?? 'image'
  const isVideoScene = sceneType === 'video'
  const isMotionScene = sceneType === 'motion'
  const isThreeDataStage = isThreeDataStageFamily(compositionState.family)
  const isClinicalTemplate = isClinicalTemplateFamily(compositionState.family)
  const threeDataStageData = isThreeDataStage
    ? normalizeThreeDataStageData(scene, compositionState.data)
    : null
  const threeDataStageHasNumericValues = Boolean(
    threeDataStageData?.series?.some((entry) => entry.points?.some((point) => point.y !== null))
    || threeDataStageData?.panels?.some((panel) => panel.series.some((entry) => entry.points?.some((point) => point.y !== null))),
  )
  const recentSceneImageHistory = imageActionHistory
    .filter((entry) => entry.scene_uid === scene.uid)
    .slice(0, 3)
  const promptSectionTitle = isMotionScene ? 'Motion Direction' : isVideoScene ? 'Clip Notes / Shot Direction' : 'Visual Prompt'
  const promptPlaceholder = isMotionScene
    ? 'Describe the motion behavior, information hierarchy, and what should animate on this scene...'
    : isVideoScene
    ? 'Describe the exact clip moment, camera move, and pacing you want for this scene...'
    : 'Visual prompt for image generation...'
  const promptFeedbackLabel = isMotionScene ? 'Refine Motion Notes' : isVideoScene ? 'Refine Notes' : 'Refine Prompt'
  const promptFeedbackPlaceholder = isMotionScene
    ? 'How should the motion direction change?'
    : isVideoScene ? 'How should the clip notes change?' : 'How should the prompt change?'
  const visualMeta = isMotionScene
    ? (
        scene.motion?.preview_exists || scene.preview_exists
          ? 'Preview ready'
          : motionState.template_id
            ? 'Template ready'
            : 'Template needed'
      )
    : isVideoScene
    ? ((typeof scene.video_exists === 'boolean' ? scene.video_exists : Boolean(scene.video_path)) ? 'Clip ready' : 'Clip needed')
    : ((typeof scene.image_exists === 'boolean' ? scene.image_exists : Boolean(scene.image_path)) ? 'Attached' : 'Empty')
  const useClipUntilEnd = scene.video_trim_end == null
  const clipStart = Number(scene.video_trim_start ?? 0)
  const clipSpeed = Number(scene.video_playback_speed ?? 1)
  const clipEnd = scene.video_trim_end == null ? '' : String(scene.video_trim_end)
  const holdLastFrame = Boolean(scene.video_hold_last_frame ?? true)
  const videoAudioSource = String(scene.video_audio_source || 'narration')
  const compositionTransitionKind = String(scene.composition?.transition_after?.kind || '')
  const projectTtsProvider = String(ttsProfile?.provider || 'kokoro')
  const projectTtsVoice = String(ttsProfile?.voice || '')
  const projectTtsSpeed = typeof ttsProfile?.speed === 'number' ? ttsProfile.speed : 1.1
  const sceneTtsOverrideEnabled = Boolean(scene.tts_override_enabled)
  const sceneTtsProviderOptions = Object.entries(ttsProviders).map(([value, label]) => ({ value, label }))
  const sceneTtsProvider = String(
    scene.tts_provider
      || projectTtsProvider
      || sceneTtsProviderOptions[0]?.value
      || 'kokoro',
  )
  const providerVoiceOptions = (ttsVoiceOptions[sceneTtsProvider] ?? []).map((item) => ({
    value: item.value,
    label: item.description ? `${item.label} - ${item.description}` : item.label,
  }))
  const sceneTtsVoice = String(scene.tts_voice || projectTtsVoice || providerVoiceOptions[0]?.value || '')
  const sceneTtsSpeed = typeof scene.tts_speed === 'number' ? scene.tts_speed : Number(projectTtsSpeed || 1.1)
  const rawVideoSceneKind = String(scene.video_scene_kind || '').trim().toLowerCase()
  const videoSceneKind = rawVideoSceneKind === 'cinematic' || rawVideoSceneKind === 'speaking'
    ? rawVideoSceneKind
    : 'auto'
  const videoModelSelectionMode = String(videoModelSelectionModeProp || 'automatic').trim().toLowerCase() === 'advanced'
    ? 'advanced'
    : 'automatic'
  const resolvedReplicateVideoRoute = videoGenerationProvider === 'replicate'
    ? resolveReplicateVideoRoute({
        modelSelectionMode: videoModelSelectionMode,
        generationModel: videoGenerationModel,
        generateAudio: videoGenerateAudio,
        sceneKind: rawVideoSceneKind,
      })
    : null
  const hasSceneImage = typeof scene.image_exists === 'boolean' ? scene.image_exists : Boolean(scene.image_path)
  const hasSceneVideo = typeof scene.video_exists === 'boolean' ? scene.video_exists : Boolean(scene.video_path)
  const hasNarrationAudio = typeof scene.audio_exists === 'boolean' ? scene.audio_exists : Boolean(scene.audio_path)
  const hasSceneAudio = sceneHasRenderableAudio(project, scene)
  const hasScenePreview = typeof scene.preview_exists === 'boolean' ? scene.preview_exists : Boolean(scene.preview_path)
  const hasMotionPreview = Boolean(scene.motion?.preview_exists || motionState.preview_path || scene.preview_path)
  const updateThreeDataStageData = (patch: Partial<ThreeDataStageCompositionData>) => {
    if (!threeDataStageData) return
    updateComposition({
      data: {
        ...threeDataStageData,
        ...patch,
      },
    })
  }
  const updateThreeDataStageProps = (patch: Record<string, unknown>) => {
    updateComposition({ props: patch })
  }
  const renderThreeDataStageEditor = () => {
    if (!threeDataStageData) {
      return null
    }

    const dataPanels = threeDataStageData.panels
    if (dataPanels && dataPanels.length > 0) {
      const updatePanels = (nextPanels: ThreeDataStagePanel[]) => {
        updateThreeDataStageData({ panels: nextPanels })
      }
      const updatePanelSeries = (panelIndex: number, nextSeries: ThreeDataStageSeries[]) => {
        updatePanels(dataPanels.map((panel, idx) => (
          idx === panelIndex ? { ...panel, series: nextSeries } : panel
        )))
      }
      const updatePanelBands = (panelIndex: number, nextBands: ThreeDataStageReferenceBand[]) => {
        updatePanels(dataPanels.map((panel, idx) => (
          idx === panelIndex ? { ...panel, referenceBands: nextBands } : panel
        )))
      }

      return (
        <div className="flex flex-col gap-[var(--space-3)]">
          {!threeDataStageHasNumericValues && (
            <GlassPanel variant="inset" padding="sm" rounded="lg">
              <p className="m-0 text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', lineHeight: 1.5 }}>
                This chart family needs numeric series values to draw real bars or lines.
              </p>
            </GlassPanel>
          )}
          <GlassPanel variant="inset" padding="sm" rounded="lg">
            <p className="m-0 text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', lineHeight: 1.5 }}>
              This scene uses a dual-panel layout because the data spans incompatible measurement scales. Each panel has its own Y axis and reference bands.
            </p>
          </GlassPanel>
          <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
            <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
              <span>Headline</span>
              <input
                type="text"
                value={String(compositionState.props.headline || '')}
                onChange={(event) => updateThreeDataStageProps({ headline: event.target.value })}
                className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                aria-label="Chart headline"
              />
            </label>
            <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
              <span>Kicker</span>
              <input
                type="text"
                value={String(compositionState.props.kicker || '')}
                onChange={(event) => updateThreeDataStageProps({ kicker: event.target.value })}
                className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                aria-label="Chart kicker"
              />
            </label>
            <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
              <span>Layout variant</span>
              <select
                value={String(compositionState.props.layoutVariant || inferThreeDataStageLayoutVariant(scene))}
                onChange={(event) => updateThreeDataStageProps({ layoutVariant: event.target.value })}
                className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                aria-label="Chart layout variant"
              >
                {THREE_DATA_STAGE_LAYOUT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
              <span>Palette</span>
              <select
                value={String(compositionState.props.palette || 'teal_on_navy')}
                onChange={(event) => updateThreeDataStageProps({ palette: event.target.value })}
                className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                aria-label="Chart palette"
              >
                {THREE_DATA_STAGE_PALETTE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
          </div>

          {dataPanels.map((panel, panelIndex) => {
            const panelSeries = panel.series ?? []
            const panelBands = panel.referenceBands ?? []
            return (
              <GlassPanel key={panel.id} variant="inset" padding="sm" className="flex flex-col gap-[var(--space-3)]">
                <SectionLabel title={panel.title || `Panel ${panelIndex + 1}`} meta={panel.yAxisLabel || ''} />
                <div className="grid gap-[var(--space-2)] xl:grid-cols-2">
                  <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    <span>Panel title</span>
                    <input
                      type="text"
                      value={panel.title || ''}
                      onChange={(event) => updatePanels(dataPanels.map((p, idx) => (
                        idx === panelIndex ? { ...p, title: event.target.value } : p
                      )))}
                      className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                      aria-label={`Panel ${panelIndex + 1} title`}
                    />
                  </label>
                  <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    <span>Y axis label</span>
                    <input
                      type="text"
                      value={panel.yAxisLabel || ''}
                      onChange={(event) => updatePanels(dataPanels.map((p, idx) => (
                        idx === panelIndex ? { ...p, yAxisLabel: event.target.value } : p
                      )))}
                      className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                      aria-label={`Panel ${panelIndex + 1} Y axis label`}
                    />
                  </label>
                </div>

                {panelSeries.map((entry, seriesIndex) => (
                  <div key={entry.id || `series-${seriesIndex}`} className="flex flex-col gap-[var(--space-2)] rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] p-[var(--space-3)]">
                    <div className="grid gap-[var(--space-2)] xl:grid-cols-[minmax(0,1.3fr)_180px_auto]">
                      <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                        <span>Series label</span>
                        <input
                          type="text"
                          value={String(entry.label || '')}
                          onChange={(event) => updatePanelSeries(panelIndex, panelSeries.map((s, idx) => (
                            idx === seriesIndex ? { ...s, label: event.target.value } : s
                          )))}
                          className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                          aria-label={`Panel ${panelIndex + 1} series ${seriesIndex + 1} label`}
                        />
                      </label>
                      <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                        <span>Series type</span>
                        <select
                          value={String(entry.type || 'bar')}
                          onChange={(event) => updatePanelSeries(panelIndex, panelSeries.map((s, idx) => (
                            idx === seriesIndex ? { ...s, type: event.target.value } : s
                          )))}
                          className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                          aria-label={`Panel ${panelIndex + 1} series ${seriesIndex + 1} type`}
                        >
                          <option value="bar">Bar</option>
                          <option value="line">Line</option>
                        </select>
                      </label>
                      <div className="flex items-end">
                        <ActionButton
                          onClick={() => updatePanelSeries(panelIndex, panelSeries.filter((_, idx) => idx !== seriesIndex))}
                          disabled={panelSeries.length <= 1}
                        >
                          Remove series
                        </ActionButton>
                      </div>
                    </div>

                    {(entry.points ?? []).map((point, pointIndex) => (
                      <div key={`${entry.id || seriesIndex}-${pointIndex}`} className="grid gap-[var(--space-2)] xl:grid-cols-[minmax(0,1fr)_140px_minmax(0,1fr)_auto]">
                        <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                          <span>X label</span>
                          <input
                            type="text"
                            value={String(point.x || '')}
                            onChange={(event) => updatePanelSeries(panelIndex, panelSeries.map((s, idx) => (
                              idx === seriesIndex
                                ? { ...s, points: (s.points ?? []).map((p, pIdx) => (pIdx === pointIndex ? { ...p, x: event.target.value } : p)) }
                                : s
                            )))}
                            className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                            aria-label={`Panel ${panelIndex + 1} point ${pointIndex + 1} x label`}
                          />
                        </label>
                        <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                          <span>Y value</span>
                          <input
                            type="number"
                            value={numberInputValue(point.y)}
                            onChange={(event) => updatePanelSeries(panelIndex, panelSeries.map((s, idx) => (
                              idx === seriesIndex
                                ? { ...s, points: (s.points ?? []).map((p, pIdx) => (pIdx === pointIndex ? { ...p, y: parseOptionalNumber(event.target.value) } : p)) }
                                : s
                            )))}
                            className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                            aria-label={`Panel ${panelIndex + 1} point ${pointIndex + 1} y value`}
                          />
                        </label>
                        <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                          <span>Point note</span>
                          <input
                            type="text"
                            value={String(point.label || '')}
                            onChange={(event) => updatePanelSeries(panelIndex, panelSeries.map((s, idx) => (
                              idx === seriesIndex
                                ? { ...s, points: (s.points ?? []).map((p, pIdx) => (pIdx === pointIndex ? { ...p, label: event.target.value || undefined } : p)) }
                                : s
                            )))}
                            className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                            aria-label={`Panel ${panelIndex + 1} point ${pointIndex + 1} note`}
                          />
                        </label>
                        <div className="flex items-end">
                          <ActionButton
                            onClick={() => updatePanelSeries(panelIndex, panelSeries.map((s, idx) => (
                              idx === seriesIndex
                                ? { ...s, points: (s.points ?? []).filter((_, pIdx) => pIdx !== pointIndex) }
                                : s
                            )))}
                            disabled={(entry.points?.length ?? 0) <= 1}
                          >
                            Remove
                          </ActionButton>
                        </div>
                      </div>
                    ))}

                    <div className="flex justify-start">
                      <ActionButton
                        onClick={() => updatePanelSeries(panelIndex, panelSeries.map((s, idx) => (
                          idx === seriesIndex
                            ? { ...s, points: [...(s.points ?? []), { x: `Point ${(s.points?.length ?? 0) + 1}`, y: null, label: undefined } as ThreeDataStagePoint] }
                            : s
                        )))}
                      >
                        Add point
                      </ActionButton>
                    </div>
                  </div>
                ))}

                <div className="flex justify-start">
                  <ActionButton
                    onClick={() => updatePanelSeries(panelIndex, [
                      ...panelSeries,
                      { id: `series_${panelSeries.length + 1}`, label: `Series ${panelSeries.length + 1}`, type: 'bar', points: [{ x: 'Point 1', y: null }] },
                    ])}
                  >
                    Add series
                  </ActionButton>
                </div>

                {panelBands.length > 0 && (
                  <>
                    <SectionLabel title="Reference Bands" meta={`${panelBands.length} bands`} />
                    {panelBands.map((band, bandIndex) => (
                      <div key={band.id || `band-${bandIndex}`} className="grid gap-[var(--space-2)] xl:grid-cols-[minmax(0,1.1fr)_140px_140px_auto] rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] p-[var(--space-3)]">
                        <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                          <span>Label</span>
                          <input
                            type="text"
                            value={String(band.label || '')}
                            onChange={(event) => updatePanelBands(panelIndex, panelBands.map((b, idx) => (idx === bandIndex ? { ...b, label: event.target.value } : b)))}
                            className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                            aria-label={`Panel ${panelIndex + 1} band ${bandIndex + 1} label`}
                          />
                        </label>
                        <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                          <span>Y min</span>
                          <input
                            type="number"
                            value={numberInputValue(band.yMin)}
                            onChange={(event) => updatePanelBands(panelIndex, panelBands.map((b, idx) => (idx === bandIndex ? { ...b, yMin: parseOptionalNumber(event.target.value) } : b)))}
                            className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                            aria-label={`Panel ${panelIndex + 1} band ${bandIndex + 1} minimum`}
                          />
                        </label>
                        <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                          <span>Y max</span>
                          <input
                            type="number"
                            value={numberInputValue(band.yMax)}
                            onChange={(event) => updatePanelBands(panelIndex, panelBands.map((b, idx) => (idx === bandIndex ? { ...b, yMax: parseOptionalNumber(event.target.value) } : b)))}
                            className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                            aria-label={`Panel ${panelIndex + 1} band ${bandIndex + 1} maximum`}
                          />
                        </label>
                        <div className="flex items-end">
                          <ActionButton onClick={() => updatePanelBands(panelIndex, panelBands.filter((_, idx) => idx !== bandIndex))}>
                            Remove
                          </ActionButton>
                        </div>
                      </div>
                    ))}
                  </>
                )}
                <div className="flex justify-start">
                  <ActionButton
                    onClick={() => updatePanelBands(panelIndex, [
                      ...panelBands,
                      { id: `band_${panelBands.length + 1}`, label: 'Reference range', yMin: null, yMax: null },
                    ])}
                  >
                    Add band
                  </ActionButton>
                </div>
              </GlassPanel>
            )
          })}
        </div>
      )
    }

    const series = threeDataStageData.series ?? []
    const referenceBands = threeDataStageData.referenceBands ?? []
    const callouts = threeDataStageData.callouts ?? []
    const updateSeries = (nextSeries: ThreeDataStageSeries[]) => {
      updateThreeDataStageData({
        series: nextSeries,
        data_points: nextSeries[0]?.points?.map((point) => String(point.x || '').trim()).filter(Boolean) ?? threeDataStageData.data_points,
      })
    }
    const updateReferenceBands = (nextReferenceBands: ThreeDataStageReferenceBand[]) => {
      updateThreeDataStageData({ referenceBands: nextReferenceBands })
    }
    const updateCallouts = (nextCallouts: ThreeDataStageCallout[]) => {
      updateThreeDataStageData({ callouts: nextCallouts })
    }

    return (
      <div className="flex flex-col gap-[var(--space-3)]">
        {!threeDataStageHasNumericValues && (
          <GlassPanel variant="inset" padding="sm" rounded="lg">
            <p className="m-0 text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', lineHeight: 1.5 }}>
              This chart family needs numeric series values to draw real bars or lines. Labels-only points are valid as placeholders, but the Remotion preview will stay visually empty until at least one series has numeric <code>y</code> values.
            </p>
          </GlassPanel>
        )}
        <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
          <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
            <span>Headline</span>
            <input
              type="text"
              value={String(compositionState.props.headline || '')}
              onChange={(event) => updateThreeDataStageProps({ headline: event.target.value })}
              className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
              aria-label="Chart headline"
            />
          </label>
          <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
            <span>Kicker</span>
            <input
              type="text"
              value={String(compositionState.props.kicker || '')}
              onChange={(event) => updateThreeDataStageProps({ kicker: event.target.value })}
              className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
              aria-label="Chart kicker"
            />
          </label>
          <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
            <span>Layout variant</span>
            <select
              value={String(compositionState.props.layoutVariant || inferThreeDataStageLayoutVariant(scene))}
              onChange={(event) => updateThreeDataStageProps({ layoutVariant: event.target.value })}
              className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
              aria-label="Chart layout variant"
            >
              {THREE_DATA_STAGE_LAYOUT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
            <span>Palette</span>
            <select
              value={String(compositionState.props.palette || 'teal_on_navy')}
              onChange={(event) => updateThreeDataStageProps({ palette: event.target.value })}
              className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
              aria-label="Chart palette"
            >
              {THREE_DATA_STAGE_PALETTE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
            <span>X axis label</span>
            <input
              type="text"
              value={threeDataStageData.xAxisLabel || ''}
              onChange={(event) => updateThreeDataStageData({ xAxisLabel: event.target.value })}
              className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
              aria-label="X axis label"
            />
          </label>
          <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
            <span>Y axis label</span>
            <input
              type="text"
              value={threeDataStageData.yAxisLabel || ''}
              onChange={(event) => updateThreeDataStageData({ yAxisLabel: event.target.value })}
              className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
              aria-label="Y axis label"
            />
          </label>
        </div>

        <GlassPanel variant="inset" padding="sm" className="flex flex-col gap-[var(--space-3)]">
          <SectionLabel title="Chart Series" meta={`${series.length} series`} />
          {series.map((entry, seriesIndex) => (
            <div key={entry.id || `series-${seriesIndex}`} className="flex flex-col gap-[var(--space-2)] rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] p-[var(--space-3)]">
              <div className="grid gap-[var(--space-2)] xl:grid-cols-[minmax(0,1.3fr)_180px_auto]">
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Series label</span>
                  <input
                    type="text"
                    value={String(entry.label || '')}
                    onChange={(event) => updateSeries(series.map((seriesEntry, index) => (
                      index === seriesIndex
                        ? { ...seriesEntry, label: event.target.value }
                        : seriesEntry
                    )))}
                    className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label={`Series ${seriesIndex + 1} label`}
                  />
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Series type</span>
                  <select
                    value={String(entry.type || 'bar')}
                    onChange={(event) => updateSeries(series.map((seriesEntry, index) => (
                      index === seriesIndex
                        ? { ...seriesEntry, type: event.target.value }
                        : seriesEntry
                    )))}
                    className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label={`Series ${seriesIndex + 1} type`}
                  >
                    <option value="bar">Bar</option>
                    <option value="line">Line</option>
                  </select>
                </label>
                <div className="flex items-end">
                  <ActionButton
                    onClick={() => updateSeries(series.filter((_, index) => index !== seriesIndex))}
                    disabled={series.length <= 1}
                  >
                    Remove series
                  </ActionButton>
                </div>
              </div>

              {(entry.points ?? []).map((point, pointIndex) => (
                <div key={`${entry.id || seriesIndex}-${pointIndex}`} className="grid gap-[var(--space-2)] xl:grid-cols-[minmax(0,1fr)_140px_minmax(0,1fr)_auto]">
                  <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    <span>X label</span>
                    <input
                      type="text"
                      value={String(point.x || '')}
                      onChange={(event) => updateSeries(series.map((seriesEntry, index) => (
                        index === seriesIndex
                          ? {
                              ...seriesEntry,
                              points: (seriesEntry.points ?? []).map((seriesPoint, innerIndex) => (
                                innerIndex === pointIndex
                                  ? { ...seriesPoint, x: event.target.value }
                                  : seriesPoint
                              )),
                            }
                          : seriesEntry
                      )))}
                      className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                      aria-label={`Series ${seriesIndex + 1} point ${pointIndex + 1} x label`}
                    />
                  </label>
                  <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    <span>Y value</span>
                    <input
                      type="number"
                      value={numberInputValue(point.y)}
                      onChange={(event) => updateSeries(series.map((seriesEntry, index) => (
                        index === seriesIndex
                          ? {
                              ...seriesEntry,
                              points: (seriesEntry.points ?? []).map((seriesPoint, innerIndex) => (
                                innerIndex === pointIndex
                                  ? { ...seriesPoint, y: parseOptionalNumber(event.target.value) }
                                  : seriesPoint
                              )),
                            }
                          : seriesEntry
                      )))}
                      className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                      aria-label={`Series ${seriesIndex + 1} point ${pointIndex + 1} y value`}
                    />
                  </label>
                  <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    <span>Point note</span>
                    <input
                      type="text"
                      value={String(point.label || '')}
                      onChange={(event) => updateSeries(series.map((seriesEntry, index) => (
                        index === seriesIndex
                          ? {
                              ...seriesEntry,
                              points: (seriesEntry.points ?? []).map((seriesPoint, innerIndex) => (
                                innerIndex === pointIndex
                                  ? { ...seriesPoint, label: event.target.value || undefined }
                                  : seriesPoint
                              )),
                            }
                          : seriesEntry
                      )))}
                      className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                      aria-label={`Series ${seriesIndex + 1} point ${pointIndex + 1} note`}
                    />
                  </label>
                  <div className="flex items-end">
                    <ActionButton
                      onClick={() => updateSeries(series.map((seriesEntry, index) => (
                        index === seriesIndex
                          ? { ...seriesEntry, points: (seriesEntry.points ?? []).filter((_, innerIndex) => innerIndex !== pointIndex) }
                          : seriesEntry
                      )))}
                      disabled={(entry.points?.length ?? 0) <= 1}
                    >
                      Remove
                    </ActionButton>
                  </div>
                </div>
              ))}

              <div className="flex justify-start">
                <ActionButton
                  onClick={() => updateSeries(series.map((seriesEntry, index) => (
                    index === seriesIndex
                      ? {
                          ...seriesEntry,
                          points: [
                            ...(seriesEntry.points ?? []),
                            {
                              x: `Point ${(seriesEntry.points?.length ?? 0) + 1}`,
                              y: null,
                              label: undefined,
                            } as ThreeDataStagePoint,
                          ],
                        }
                      : seriesEntry
                  )))}
                >
                  Add point
                </ActionButton>
              </div>
            </div>
          ))}
          <div className="flex justify-start">
            <ActionButton
              onClick={() => updateSeries([
                ...series,
                {
                  id: `series_${series.length + 1}`,
                  label: `Series ${series.length + 1}`,
                  type: 'bar',
                  points: [{ x: 'Point 1', y: null }],
                },
              ])}
            >
              Add series
            </ActionButton>
          </div>
        </GlassPanel>

        <GlassPanel variant="inset" padding="sm" className="flex flex-col gap-[var(--space-3)]">
          <SectionLabel title="Reference Bands" meta={`${referenceBands.length} bands`} />
          {referenceBands.map((band, bandIndex) => (
            <div key={band.id || `band-${bandIndex}`} className="grid gap-[var(--space-2)] xl:grid-cols-[minmax(0,1.1fr)_140px_140px_minmax(0,1fr)_minmax(0,1fr)_auto] rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] p-[var(--space-3)]">
              <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <span>Label</span>
                <input
                  type="text"
                  value={String(band.label || '')}
                  onChange={(event) => updateReferenceBands(referenceBands.map((entry, index) => (
                    index === bandIndex ? { ...entry, label: event.target.value } : entry
                  )))}
                  className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  aria-label={`Reference band ${bandIndex + 1} label`}
                />
              </label>
              <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <span>Y min</span>
                <input
                  type="number"
                  value={numberInputValue(band.yMin)}
                  onChange={(event) => updateReferenceBands(referenceBands.map((entry, index) => (
                    index === bandIndex ? { ...entry, yMin: parseOptionalNumber(event.target.value) } : entry
                  )))}
                  className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  aria-label={`Reference band ${bandIndex + 1} minimum`}
                />
              </label>
              <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <span>Y max</span>
                <input
                  type="number"
                  value={numberInputValue(band.yMax)}
                  onChange={(event) => updateReferenceBands(referenceBands.map((entry, index) => (
                    index === bandIndex ? { ...entry, yMax: parseOptionalNumber(event.target.value) } : entry
                  )))}
                  className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  aria-label={`Reference band ${bandIndex + 1} maximum`}
                />
              </label>
              <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <span>From X</span>
                <input
                  type="text"
                  value={String(band.xRange?.[0] || '')}
                  onChange={(event) => updateReferenceBands(referenceBands.map((entry, index) => (
                    index === bandIndex
                      ? {
                          ...entry,
                          xRange: [event.target.value, String(entry.xRange?.[1] || '')],
                        }
                      : entry
                  )))}
                  className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  aria-label={`Reference band ${bandIndex + 1} start`}
                />
              </label>
              <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <span>To X</span>
                <input
                  type="text"
                  value={String(band.xRange?.[1] || '')}
                  onChange={(event) => updateReferenceBands(referenceBands.map((entry, index) => (
                    index === bandIndex
                      ? {
                          ...entry,
                          xRange: [String(entry.xRange?.[0] || ''), event.target.value],
                        }
                      : entry
                  )))}
                  className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  aria-label={`Reference band ${bandIndex + 1} end`}
                />
              </label>
              <div className="flex items-end">
                <ActionButton onClick={() => updateReferenceBands(referenceBands.filter((_, index) => index !== bandIndex))}>
                  Remove
                </ActionButton>
              </div>
            </div>
          ))}
          <div className="flex justify-start">
            <ActionButton
              onClick={() => updateReferenceBands([
                ...referenceBands,
                {
                  id: `band_${referenceBands.length + 1}`,
                  label: 'Reference range',
                  yMin: null,
                  yMax: null,
                },
              ])}
            >
              Add band
            </ActionButton>
          </div>
        </GlassPanel>

        <GlassPanel variant="inset" padding="sm" className="flex flex-col gap-[var(--space-3)]">
          <SectionLabel title="Callouts" meta={`${callouts.length} callouts`} />
          {callouts.map((callout, calloutIndex) => {
            const calloutMode = callout.fromX || callout.toX ? 'delta' : 'point'
            const lastSeriesPoint = series[0]?.points && series[0].points.length > 0
              ? series[0].points[series[0].points.length - 1]
              : undefined
            return (
              <div key={callout.id || `callout-${calloutIndex}`} className="grid gap-[var(--space-2)] xl:grid-cols-[140px_minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)_140px_auto] rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] p-[var(--space-3)]">
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Type</span>
                  <select
                    value={calloutMode}
                    onChange={(event) => updateCallouts(callouts.map((entry, index) => (
                      index === calloutIndex
                        ? event.target.value === 'delta'
                          ? { ...entry, x: undefined, y: null, fromX: entry.fromX || series[0]?.points?.[0]?.x || '', toX: entry.toX || lastSeriesPoint?.x || '' }
                          : { ...entry, fromX: undefined, toX: undefined, x: entry.x || series[0]?.points?.[0]?.x || '', y: entry.y ?? null }
                        : entry
                    )))}
                    className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label={`Callout ${calloutIndex + 1} type`}
                  >
                    <option value="point">Point</option>
                    <option value="delta">Delta</option>
                  </select>
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Label</span>
                  <input
                    type="text"
                    value={String(callout.label || '')}
                    onChange={(event) => updateCallouts(callouts.map((entry, index) => (
                      index === calloutIndex ? { ...entry, label: event.target.value } : entry
                    )))}
                    className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label={`Callout ${calloutIndex + 1} label`}
                  />
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>{calloutMode === 'delta' ? 'From X' : 'X label'}</span>
                  <input
                    type="text"
                    value={String(calloutMode === 'delta' ? callout.fromX || '' : callout.x || '')}
                    onChange={(event) => updateCallouts(callouts.map((entry, index) => (
                      index === calloutIndex
                        ? calloutMode === 'delta'
                          ? { ...entry, fromX: event.target.value }
                          : { ...entry, x: event.target.value }
                        : entry
                    )))}
                    className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label={`Callout ${calloutIndex + 1} primary anchor`}
                  />
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>{calloutMode === 'delta' ? 'To X' : 'Y value'}</span>
                  <input
                    type={calloutMode === 'delta' ? 'text' : 'number'}
                    value={calloutMode === 'delta' ? String(callout.toX || '') : numberInputValue(callout.y)}
                    onChange={(event) => updateCallouts(callouts.map((entry, index) => (
                      index === calloutIndex
                        ? calloutMode === 'delta'
                          ? { ...entry, toX: event.target.value }
                          : { ...entry, y: parseOptionalNumber(event.target.value) }
                        : entry
                    )))}
                    className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label={`Callout ${calloutIndex + 1} secondary anchor`}
                  />
                </label>
                <div />
                <div className="flex items-end">
                  <ActionButton onClick={() => updateCallouts(callouts.filter((_, index) => index !== calloutIndex))}>
                    Remove
                  </ActionButton>
                </div>
              </div>
            )
          })}
          <div className="flex justify-start">
            <ActionButton
              onClick={() => updateCallouts([
                ...callouts,
                {
                  id: `callout_${callouts.length + 1}`,
                  label: 'Callout',
                  x: series[0]?.points?.[0]?.x || '',
                  y: null,
                },
              ])}
            >
              Add callout
            </ActionButton>
          </div>
        </GlassPanel>
      </div>
    )
  }

  // ── Clinical template family editors ──────────────────────────────────

  const clinicalProps = compositionState.props as Record<string, unknown>

  const updateClinicalProp = (key: string, value: unknown) => {
    updateComposition({ props: { [key]: value } })
  }

  const updateClinicalArrayItem = (key: string, index: number, value: string) => {
    const arr = Array.isArray(clinicalProps[key]) ? [...(clinicalProps[key] as string[])] : []
    arr[index] = value
    updateClinicalProp(key, arr)
  }

  const removeClinicalArrayItem = (key: string, index: number) => {
    const arr = Array.isArray(clinicalProps[key]) ? [...(clinicalProps[key] as string[])] : []
    arr.splice(index, 1)
    updateClinicalProp(key, arr)
  }

  const addClinicalArrayItem = (key: string) => {
    const arr = Array.isArray(clinicalProps[key]) ? [...(clinicalProps[key] as string[])] : []
    arr.push('')
    updateClinicalProp(key, arr)
  }

  const clinicalInputClass = 'rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]'
  const clinicalLabelClass = 'flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]'

  const renderStringArrayEditor = (key: string, label: string, itemLabel: string) => {
    const items: string[] = Array.isArray(clinicalProps[key]) ? (clinicalProps[key] as string[]) : []
    return (
      <div className="flex flex-col gap-[var(--space-2)]">
        <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}>
          {label}
        </span>
        {items.map((item, i) => (
          <div key={i} className="flex min-w-0 items-center gap-[var(--space-2)]">
            <input
              type="text"
              value={item}
              onChange={(e) => updateClinicalArrayItem(key, i, e.target.value)}
              className={`min-w-0 flex-1 ${clinicalInputClass}`}
              style={{ fontSize: 'var(--text-sm)' }}
              aria-label={`${itemLabel} ${i + 1}`}
            />
            <button
              onClick={() => removeClinicalArrayItem(key, i)}
              className="rounded-[var(--radius-sm)] p-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--signal-danger)]"
              aria-label={`Remove ${itemLabel} ${i + 1}`}
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M3 3L11 11M3 11L11 3" />
              </svg>
            </button>
          </div>
        ))}
        <button
          onClick={() => addClinicalArrayItem(key)}
          className="self-start rounded-[var(--radius-sm)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--text-secondary)]"
          style={{ fontSize: 'var(--text-xs)' }}
        >
          + Add {itemLabel.toLowerCase()}
        </button>
      </div>
    )
  }

  const renderClinicalTemplateEditor = () => {
    const family = compositionState.family

    // ── cover_hook: headline, subtitle, kicker ──
    if (family === 'cover_hook') {
      return (
        <>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Headline</span>
            <input
              type="text"
              value={String(clinicalProps.headline || '')}
              onChange={(e) => updateClinicalProp('headline', e.target.value)}
              className={clinicalInputClass}
              aria-label="Cover headline"
            />
          </label>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Subtitle</span>
            <textarea
              value={String(clinicalProps.subtitle || '')}
              onChange={(e) => updateClinicalProp('subtitle', e.target.value)}
              rows={2}
              className={`w-full resize-y ${clinicalInputClass}`}
              aria-label="Cover subtitle"
            />
          </label>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Kicker</span>
            <input
              type="text"
              value={String(clinicalProps.kicker || '')}
              onChange={(e) => updateClinicalProp('kicker', e.target.value)}
              className={clinicalInputClass}
              aria-label="Cover kicker"
            />
          </label>
        </>
      )
    }

    // ── orientation: headline, items[] ──
    if (family === 'orientation') {
      return (
        <>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Headline</span>
            <input
              type="text"
              value={String(clinicalProps.headline || '')}
              onChange={(e) => updateClinicalProp('headline', e.target.value)}
              className={clinicalInputClass}
              aria-label="Orientation headline"
            />
          </label>
          {renderStringArrayEditor('items', 'Roadmap items', 'Item')}
        </>
      )
    }

    // ── synthesis_summary: headline, columns[{title, accent, items}] ──
    if (family === 'synthesis_summary') {
      const columns = Array.isArray(clinicalProps.columns)
        ? (clinicalProps.columns as Array<{ title?: string; accent?: string; items?: Array<{ label?: string; icon?: string } | string> }>)
        : []
      const updateColumn = (ci: number, patch: Record<string, unknown>) => {
        const next = columns.map((col, i) => (i === ci ? { ...col, ...patch } : col))
        updateClinicalProp('columns', next)
      }
      const addColumn = () => {
        updateClinicalProp('columns', [...columns, { title: '', accent: 'teal', items: [] }])
      }
      const removeColumn = (ci: number) => {
        updateClinicalProp('columns', columns.filter((_, i) => i !== ci))
      }
      return (
        <>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Headline</span>
            <input
              type="text"
              value={String(clinicalProps.headline || '')}
              onChange={(e) => updateClinicalProp('headline', e.target.value)}
              className={clinicalInputClass}
              aria-label="Synthesis headline"
            />
          </label>
          <div className="flex flex-col gap-[var(--space-3)]">
            <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}>
              Columns ({columns.length})
            </span>
            {columns.map((col, ci) => {
              const colItems = (col.items || []).map((it) =>
                typeof it === 'string' ? it : (it.label || '')
              )
              return (
                <GlassPanel key={ci} variant="inset" padding="sm" rounded="md">
                  <div className="flex flex-col gap-[var(--space-2)]">
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}>
                        Column {ci + 1}
                      </span>
                      <button
                        onClick={() => removeColumn(ci)}
                        className="rounded-[var(--radius-sm)] p-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--signal-danger)]"
                        aria-label={`Remove column ${ci + 1}`}
                      >
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                          <path d="M3 3L11 11M3 11L11 3" />
                        </svg>
                      </button>
                    </div>
                    <div className="grid gap-[var(--space-2)] xl:grid-cols-2">
                      <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
                        <span>Title</span>
                        <input
                          type="text"
                          value={col.title || ''}
                          onChange={(e) => updateColumn(ci, { title: e.target.value })}
                          className={clinicalInputClass}
                          aria-label={`Column ${ci + 1} title`}
                        />
                      </label>
                      <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
                        <span>Accent</span>
                        <select
                          value={col.accent || 'teal'}
                          onChange={(e) => updateColumn(ci, { accent: e.target.value })}
                          className={clinicalInputClass}
                          aria-label={`Column ${ci + 1} accent`}
                        >
                          <option value="teal">Teal</option>
                          <option value="amber">Amber</option>
                          <option value="blue">Blue</option>
                          <option value="green">Green</option>
                        </select>
                      </label>
                    </div>
                    <div className="flex flex-col gap-[var(--space-1)]">
                      <span className="text-[var(--text-tertiary)]" style={{ fontSize: '10px' }}>Items</span>
                      {colItems.map((item, ii) => (
                        <div key={ii} className="flex min-w-0 items-center gap-[var(--space-2)]">
                          <input
                            type="text"
                            value={item}
                            onChange={(e) => {
                              const nextItems = [...colItems]
                              nextItems[ii] = e.target.value
                              updateColumn(ci, { items: nextItems.map((it) => ({ label: it })) })
                            }}
                            className={`min-w-0 flex-1 ${clinicalInputClass}`}
                            style={{ fontSize: 'var(--text-sm)' }}
                            aria-label={`Column ${ci + 1} item ${ii + 1}`}
                          />
                          <button
                            onClick={() => {
                              const nextItems = colItems.filter((_, j) => j !== ii)
                              updateColumn(ci, { items: nextItems.map((it) => ({ label: it })) })
                            }}
                            className="rounded-[var(--radius-sm)] p-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--signal-danger)]"
                            aria-label={`Remove column ${ci + 1} item ${ii + 1}`}
                          >
                            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                              <path d="M3 3L11 11M3 11L11 3" />
                            </svg>
                          </button>
                        </div>
                      ))}
                      <button
                        onClick={() => {
                          updateColumn(ci, { items: [...colItems.map((it) => ({ label: it })), { label: '' }] })
                        }}
                        className="self-start rounded-[var(--radius-sm)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--text-secondary)]"
                        style={{ fontSize: 'var(--text-xs)' }}
                      >
                        + Add item
                      </button>
                    </div>
                  </div>
                </GlassPanel>
              )
            })}
            <button
              onClick={addColumn}
              className="self-start rounded-[var(--radius-sm)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--text-secondary)]"
              style={{ fontSize: 'var(--text-xs)' }}
            >
              + Add column
            </button>
          </div>
        </>
      )
    }

    // ── closing_cta: headline, bullets[], kicker, caption ──
    if (family === 'closing_cta') {
      return (
        <>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Headline</span>
            <input
              type="text"
              value={String(clinicalProps.headline || '')}
              onChange={(e) => updateClinicalProp('headline', e.target.value)}
              className={clinicalInputClass}
              aria-label="CTA headline"
            />
          </label>
          {renderStringArrayEditor('bullets', 'Bullets', 'Bullet')}
          <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
            <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
              <span>Kicker</span>
              <input
                type="text"
                value={String(clinicalProps.kicker || '')}
                onChange={(e) => updateClinicalProp('kicker', e.target.value)}
                className={clinicalInputClass}
                aria-label="CTA kicker"
              />
            </label>
            <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
              <span>Caption</span>
              <input
                type="text"
                value={String(clinicalProps.caption || '')}
                onChange={(e) => updateClinicalProp('caption', e.target.value)}
                className={clinicalInputClass}
                aria-label="CTA caption"
              />
            </label>
          </div>
        </>
      )
    }

    // ── clinical_explanation: headline, body, caption, labels[{text, region}] ──
    if (family === 'clinical_explanation') {
      const labels = Array.isArray(clinicalProps.labels)
        ? (clinicalProps.labels as Array<{ text?: string; region?: string }>)
        : []
      const updateLabel = (li: number, patch: Record<string, string>) => {
        const next = labels.map((lbl, i) => (i === li ? { ...lbl, ...patch } : lbl))
        updateClinicalProp('labels', next)
      }
      return (
        <>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Headline</span>
            <input
              type="text"
              value={String(clinicalProps.headline || '')}
              onChange={(e) => updateClinicalProp('headline', e.target.value)}
              className={clinicalInputClass}
              aria-label="Explanation headline"
            />
          </label>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Body</span>
            <textarea
              value={String(clinicalProps.body || '')}
              onChange={(e) => updateClinicalProp('body', e.target.value)}
              rows={3}
              className={`w-full resize-y ${clinicalInputClass}`}
              aria-label="Explanation body"
            />
          </label>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Caption</span>
            <input
              type="text"
              value={String(clinicalProps.caption || '')}
              onChange={(e) => updateClinicalProp('caption', e.target.value)}
              className={clinicalInputClass}
              aria-label="Explanation caption"
            />
          </label>
          <div className="flex flex-col gap-[var(--space-2)]">
            <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}>
              Floating labels ({labels.length})
            </span>
            {labels.map((lbl, li) => (
              <div key={li} className="flex min-w-0 items-center gap-[var(--space-2)]">
                <input
                  type="text"
                  value={lbl.text || ''}
                  onChange={(e) => updateLabel(li, { text: e.target.value })}
                  placeholder="Label text"
                  className={`min-w-0 flex-1 ${clinicalInputClass}`}
                  style={{ fontSize: 'var(--text-sm)' }}
                  aria-label={`Label ${li + 1} text`}
                />
                <select
                  value={lbl.region || 'center'}
                  onChange={(e) => updateLabel(li, { region: e.target.value })}
                  className={clinicalInputClass}
                  style={{ fontSize: 'var(--text-xs)', width: 'auto' }}
                  aria-label={`Label ${li + 1} region`}
                >
                  <option value="top-left">Top left</option>
                  <option value="top-center">Top center</option>
                  <option value="top-right">Top right</option>
                  <option value="center-left">Center left</option>
                  <option value="center">Center</option>
                  <option value="center-right">Center right</option>
                  <option value="bottom-left">Bottom left</option>
                  <option value="bottom-center">Bottom center</option>
                  <option value="bottom-right">Bottom right</option>
                </select>
                <button
                  onClick={() => updateClinicalProp('labels', labels.filter((_, i) => i !== li))}
                  className="rounded-[var(--radius-sm)] p-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--signal-danger)]"
                  aria-label={`Remove label ${li + 1}`}
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M3 3L11 11M3 11L11 3" />
                  </svg>
                </button>
              </div>
            ))}
            <button
              onClick={() => updateClinicalProp('labels', [...labels, { text: '', region: 'center' }])}
              className="self-start rounded-[var(--radius-sm)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--text-secondary)]"
              style={{ fontSize: 'var(--text-xs)' }}
            >
              + Add label
            </button>
          </div>
        </>
      )
    }

    // ── metric_improvement: headline, metric_name, before/after {value, label}, delta, caption, direction ──
    if (family === 'metric_improvement') {
      const before = (clinicalProps.before ?? {}) as { value?: string; label?: string }
      const after = (clinicalProps.after ?? {}) as { value?: string; label?: string }
      return (
        <>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Headline</span>
            <input
              type="text"
              value={String(clinicalProps.headline || '')}
              onChange={(e) => updateClinicalProp('headline', e.target.value)}
              className={clinicalInputClass}
              aria-label="Metric headline"
            />
          </label>
          <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
            <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
              <span>Metric name</span>
              <input
                type="text"
                value={String(clinicalProps.metric_name || '')}
                onChange={(e) => updateClinicalProp('metric_name', e.target.value)}
                className={clinicalInputClass}
                aria-label="Metric name"
              />
            </label>
            <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
              <span>Direction</span>
              <select
                value={String(clinicalProps.direction || 'improvement')}
                onChange={(e) => updateClinicalProp('direction', e.target.value)}
                className={clinicalInputClass}
                aria-label="Direction"
              >
                <option value="improvement">Improvement</option>
                <option value="decline">Decline</option>
                <option value="neutral">Neutral</option>
              </select>
            </label>
          </div>
          <GlassPanel variant="inset" padding="sm" rounded="md">
            <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}>
              Before
            </span>
            <div className="mt-[var(--space-1)] grid gap-[var(--space-2)] xl:grid-cols-2">
              <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
                <span>Value</span>
                <input
                  type="text"
                  value={before.value || ''}
                  onChange={(e) => updateClinicalProp('before', { ...before, value: e.target.value })}
                  className={clinicalInputClass}
                  aria-label="Before value"
                />
              </label>
              <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
                <span>Label</span>
                <input
                  type="text"
                  value={before.label || ''}
                  onChange={(e) => updateClinicalProp('before', { ...before, label: e.target.value })}
                  className={clinicalInputClass}
                  aria-label="Before label"
                />
              </label>
            </div>
          </GlassPanel>
          <GlassPanel variant="inset" padding="sm" rounded="md">
            <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}>
              After
            </span>
            <div className="mt-[var(--space-1)] grid gap-[var(--space-2)] xl:grid-cols-2">
              <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
                <span>Value</span>
                <input
                  type="text"
                  value={after.value || ''}
                  onChange={(e) => updateClinicalProp('after', { ...after, value: e.target.value })}
                  className={clinicalInputClass}
                  aria-label="After value"
                />
              </label>
              <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
                <span>Label</span>
                <input
                  type="text"
                  value={after.label || ''}
                  onChange={(e) => updateClinicalProp('after', { ...after, label: e.target.value })}
                  className={clinicalInputClass}
                  aria-label="After label"
                />
              </label>
            </div>
          </GlassPanel>
          <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
            <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
              <span>Delta</span>
              <input
                type="text"
                value={String(clinicalProps.delta || '')}
                onChange={(e) => updateClinicalProp('delta', e.target.value)}
                className={clinicalInputClass}
                aria-label="Delta"
                placeholder="e.g. +18%"
              />
            </label>
            <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
              <span>Caption</span>
              <input
                type="text"
                value={String(clinicalProps.caption || '')}
                onChange={(e) => updateClinicalProp('caption', e.target.value)}
                className={clinicalInputClass}
                aria-label="Metric caption"
              />
            </label>
          </div>
        </>
      )
    }

    // ── brain_region_focus: headline, regions[{name, value, status}], caption, view ──
    if (family === 'brain_region_focus') {
      const regions = Array.isArray(clinicalProps.regions)
        ? (clinicalProps.regions as Array<{ name?: string; value?: string; status?: string }>)
        : []
      const updateRegion = (ri: number, patch: Record<string, string>) => {
        const next = regions.map((reg, i) => (i === ri ? { ...reg, ...patch } : reg))
        updateClinicalProp('regions', next)
      }
      return (
        <>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Headline</span>
            <input
              type="text"
              value={String(clinicalProps.headline || '')}
              onChange={(e) => updateClinicalProp('headline', e.target.value)}
              className={clinicalInputClass}
              aria-label="Brain region headline"
            />
          </label>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Caption</span>
            <input
              type="text"
              value={String(clinicalProps.caption || '')}
              onChange={(e) => updateClinicalProp('caption', e.target.value)}
              className={clinicalInputClass}
              aria-label="Brain region caption"
            />
          </label>
          <div className="flex flex-col gap-[var(--space-2)]">
            <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}>
              Regions ({regions.length})
            </span>
            {regions.map((reg, ri) => (
              <div key={ri} className="flex min-w-0 flex-wrap items-center gap-[var(--space-2)]">
                <input
                  type="text"
                  value={reg.name || ''}
                  onChange={(e) => updateRegion(ri, { name: e.target.value })}
                  placeholder="Name (e.g. frontal)"
                  className={`min-w-0 flex-1 basis-[8rem] ${clinicalInputClass}`}
                  style={{ fontSize: 'var(--text-sm)' }}
                  aria-label={`Region ${ri + 1} name`}
                />
                <input
                  type="text"
                  value={reg.value || ''}
                  onChange={(e) => updateRegion(ri, { value: e.target.value })}
                  placeholder="Value"
                  className={`min-w-0 basis-[5rem] ${clinicalInputClass}`}
                  style={{ fontSize: 'var(--text-sm)' }}
                  aria-label={`Region ${ri + 1} value`}
                />
                <select
                  value={reg.status || 'stable'}
                  onChange={(e) => updateRegion(ri, { status: e.target.value })}
                  className={clinicalInputClass}
                  style={{ fontSize: 'var(--text-xs)', width: 'auto' }}
                  aria-label={`Region ${ri + 1} status`}
                >
                  <option value="improved">Improved</option>
                  <option value="stable">Stable</option>
                  <option value="declined">Declined</option>
                  <option value="flagged">Flagged</option>
                </select>
                <button
                  onClick={() => updateClinicalProp('regions', regions.filter((_, i) => i !== ri))}
                  className="rounded-[var(--radius-sm)] p-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--signal-danger)]"
                  aria-label={`Remove region ${ri + 1}`}
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M3 3L11 11M3 11L11 3" />
                  </svg>
                </button>
              </div>
            ))}
            <button
              onClick={() => updateClinicalProp('regions', [...regions, { name: '', value: '', status: 'stable' }])}
              className="self-start rounded-[var(--radius-sm)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--text-secondary)]"
              style={{ fontSize: 'var(--text-xs)' }}
            >
              + Add region
            </button>
          </div>
        </>
      )
    }

    // ── metric_comparison: headline, left/right {title, accent, items[]}, caption ──
    if (family === 'metric_comparison') {
      const left = (clinicalProps.left ?? {}) as { title?: string; accent?: string; items?: string[] }
      const right = (clinicalProps.right ?? {}) as { title?: string; accent?: string; items?: string[] }
      const renderComparisonSide = (sideKey: 'left' | 'right', side: typeof left, sideLabel: string) => {
        const sideItems = side.items || []
        return (
          <GlassPanel variant="inset" padding="sm" rounded="md">
            <div className="flex flex-col gap-[var(--space-2)]">
              <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}>
                {sideLabel}
              </span>
              <div className="grid gap-[var(--space-2)] xl:grid-cols-2">
                <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Title</span>
                  <input
                    type="text"
                    value={side.title || ''}
                    onChange={(e) => updateClinicalProp(sideKey, { ...side, title: e.target.value })}
                    className={clinicalInputClass}
                    aria-label={`${sideLabel} title`}
                  />
                </label>
                <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Accent</span>
                  <select
                    value={side.accent || (sideKey === 'left' ? 'amber' : 'teal')}
                    onChange={(e) => updateClinicalProp(sideKey, { ...side, accent: e.target.value })}
                    className={clinicalInputClass}
                    aria-label={`${sideLabel} accent`}
                  >
                    <option value="teal">Teal</option>
                    <option value="amber">Amber</option>
                    <option value="blue">Blue</option>
                    <option value="green">Green</option>
                  </select>
                </label>
              </div>
              {sideItems.map((item, ii) => (
                <div key={ii} className="flex min-w-0 items-center gap-[var(--space-2)]">
                  <input
                    type="text"
                    value={item}
                    onChange={(e) => {
                      const nextItems = [...sideItems]
                      nextItems[ii] = e.target.value
                      updateClinicalProp(sideKey, { ...side, items: nextItems })
                    }}
                    className={`min-w-0 flex-1 ${clinicalInputClass}`}
                    style={{ fontSize: 'var(--text-sm)' }}
                    aria-label={`${sideLabel} item ${ii + 1}`}
                  />
                  <button
                    onClick={() => {
                      const nextItems = sideItems.filter((_, j) => j !== ii)
                      updateClinicalProp(sideKey, { ...side, items: nextItems })
                    }}
                    className="rounded-[var(--radius-sm)] p-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--signal-danger)]"
                    aria-label={`Remove ${sideLabel} item ${ii + 1}`}
                  >
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M3 3L11 11M3 11L11 3" />
                    </svg>
                  </button>
                </div>
              ))}
              <button
                onClick={() => updateClinicalProp(sideKey, { ...side, items: [...sideItems, ''] })}
                className="self-start rounded-[var(--radius-sm)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--text-secondary)]"
                style={{ fontSize: 'var(--text-xs)' }}
              >
                + Add item
              </button>
            </div>
          </GlassPanel>
        )
      }
      return (
        <>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Headline</span>
            <input
              type="text"
              value={String(clinicalProps.headline || '')}
              onChange={(e) => updateClinicalProp('headline', e.target.value)}
              className={clinicalInputClass}
              aria-label="Comparison headline"
            />
          </label>
          {renderComparisonSide('left', left, 'Left panel')}
          {renderComparisonSide('right', right, 'Right panel')}
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Caption</span>
            <input
              type="text"
              value={String(clinicalProps.caption || '')}
              onChange={(e) => updateClinicalProp('caption', e.target.value)}
              className={clinicalInputClass}
              aria-label="Comparison caption"
            />
          </label>
        </>
      )
    }

    // ── timeline_progression: headline, span_label, markers[{label, date, annotation, status}], caption ──
    if (family === 'timeline_progression') {
      const markers = Array.isArray(clinicalProps.markers)
        ? (clinicalProps.markers as Array<{ label?: string; date?: string; annotation?: string; status?: string }>)
        : []
      const updateMarker = (mi: number, patch: Record<string, string>) => {
        const next = markers.map((m, i) => (i === mi ? { ...m, ...patch } : m))
        updateClinicalProp('markers', next)
      }
      return (
        <>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Headline</span>
            <input
              type="text"
              value={String(clinicalProps.headline || '')}
              onChange={(e) => updateClinicalProp('headline', e.target.value)}
              className={clinicalInputClass}
              aria-label="Timeline headline"
            />
          </label>
          <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
            <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
              <span>Span label</span>
              <input
                type="text"
                value={String(clinicalProps.span_label || '')}
                onChange={(e) => updateClinicalProp('span_label', e.target.value)}
                className={clinicalInputClass}
                aria-label="Span label"
                placeholder="e.g. 6-month treatment window"
              />
            </label>
            <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
              <span>Caption</span>
              <input
                type="text"
                value={String(clinicalProps.caption || '')}
                onChange={(e) => updateClinicalProp('caption', e.target.value)}
                className={clinicalInputClass}
                aria-label="Timeline caption"
              />
            </label>
          </div>
          <div className="flex flex-col gap-[var(--space-2)]">
            <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}>
              Markers ({markers.length})
            </span>
            {markers.map((m, mi) => (
              <GlassPanel key={mi} variant="inset" padding="sm" rounded="md">
                <div className="flex items-center justify-between">
                  <span className="text-[var(--text-tertiary)]" style={{ fontSize: '10px' }}>Marker {mi + 1}</span>
                  <button
                    onClick={() => updateClinicalProp('markers', markers.filter((_, i) => i !== mi))}
                    className="rounded-[var(--radius-sm)] p-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--signal-danger)]"
                    aria-label={`Remove marker ${mi + 1}`}
                  >
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M3 3L11 11M3 11L11 3" />
                    </svg>
                  </button>
                </div>
                <div className="mt-[var(--space-1)] grid gap-[var(--space-2)] xl:grid-cols-2">
                  <input
                    type="text"
                    value={m.label || ''}
                    onChange={(e) => updateMarker(mi, { label: e.target.value })}
                    placeholder="Label"
                    className={clinicalInputClass}
                    style={{ fontSize: 'var(--text-sm)' }}
                    aria-label={`Marker ${mi + 1} label`}
                  />
                  <input
                    type="text"
                    value={m.date || ''}
                    onChange={(e) => updateMarker(mi, { date: e.target.value })}
                    placeholder="Date"
                    className={clinicalInputClass}
                    style={{ fontSize: 'var(--text-sm)' }}
                    aria-label={`Marker ${mi + 1} date`}
                  />
                  <input
                    type="text"
                    value={m.annotation || ''}
                    onChange={(e) => updateMarker(mi, { annotation: e.target.value })}
                    placeholder="Annotation"
                    className={clinicalInputClass}
                    style={{ fontSize: 'var(--text-sm)' }}
                    aria-label={`Marker ${mi + 1} annotation`}
                  />
                  <select
                    value={m.status || 'completed'}
                    onChange={(e) => updateMarker(mi, { status: e.target.value })}
                    className={clinicalInputClass}
                    style={{ fontSize: 'var(--text-xs)' }}
                    aria-label={`Marker ${mi + 1} status`}
                  >
                    <option value="completed">Completed</option>
                    <option value="active">Active</option>
                    <option value="flagged">Flagged</option>
                    <option value="upcoming">Upcoming</option>
                  </select>
                </div>
              </GlassPanel>
            ))}
            <button
              onClick={() => updateClinicalProp('markers', [...markers, { label: '', date: '', annotation: '', status: 'completed' }])}
              className="self-start rounded-[var(--radius-sm)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--text-secondary)]"
              style={{ fontSize: 'var(--text-xs)' }}
            >
              + Add marker
            </button>
          </div>
        </>
      )
    }

    // ── analogy_metaphor: headline, left/right {title, accent, items[], direction, summary}, caption ──
    if (family === 'analogy_metaphor') {
      const left = (clinicalProps.left ?? {}) as {
        title?: string; items?: string[]; accent?: string; direction?: string; summary?: string
      }
      const right = (clinicalProps.right ?? {}) as {
        title?: string; items?: string[]; accent?: string; direction?: string; summary?: string
      }
      const renderAnalogyPanel = (sideKey: 'left' | 'right', side: typeof left, sideLabel: string) => {
        const sideItems = side.items || []
        return (
          <GlassPanel variant="inset" padding="sm" rounded="md">
            <div className="flex flex-col gap-[var(--space-2)]">
              <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}>
                {sideLabel}
              </span>
              <div className="grid gap-[var(--space-2)] xl:grid-cols-3">
                <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Title</span>
                  <input
                    type="text"
                    value={side.title || ''}
                    onChange={(e) => updateClinicalProp(sideKey, { ...side, title: e.target.value })}
                    className={clinicalInputClass}
                    aria-label={`${sideLabel} title`}
                  />
                </label>
                <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Accent</span>
                  <select
                    value={side.accent || 'teal'}
                    onChange={(e) => updateClinicalProp(sideKey, { ...side, accent: e.target.value })}
                    className={clinicalInputClass}
                    aria-label={`${sideLabel} accent`}
                  >
                    <option value="teal">Teal</option>
                    <option value="amber">Amber</option>
                    <option value="blue">Blue</option>
                    <option value="green">Green</option>
                  </select>
                </label>
                <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Direction</span>
                  <select
                    value={side.direction || ''}
                    onChange={(e) => updateClinicalProp(sideKey, { ...side, direction: e.target.value })}
                    className={clinicalInputClass}
                    aria-label={`${sideLabel} direction`}
                  >
                    <option value="">None</option>
                    <option value="up">Up</option>
                    <option value="down">Down</option>
                  </select>
                </label>
              </div>
              {sideItems.map((item, ii) => (
                <div key={ii} className="flex min-w-0 items-center gap-[var(--space-2)]">
                  <input
                    type="text"
                    value={item}
                    onChange={(e) => {
                      const nextItems = [...sideItems]
                      nextItems[ii] = e.target.value
                      updateClinicalProp(sideKey, { ...side, items: nextItems })
                    }}
                    className={`min-w-0 flex-1 ${clinicalInputClass}`}
                    style={{ fontSize: 'var(--text-sm)' }}
                    aria-label={`${sideLabel} item ${ii + 1}`}
                  />
                  <button
                    onClick={() => {
                      const nextItems = sideItems.filter((_, j) => j !== ii)
                      updateClinicalProp(sideKey, { ...side, items: nextItems })
                    }}
                    className="rounded-[var(--radius-sm)] p-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--signal-danger)]"
                    aria-label={`Remove ${sideLabel} item ${ii + 1}`}
                  >
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M3 3L11 11M3 11L11 3" />
                    </svg>
                  </button>
                </div>
              ))}
              <button
                onClick={() => updateClinicalProp(sideKey, { ...side, items: [...sideItems, ''] })}
                className="self-start rounded-[var(--radius-sm)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--text-secondary)]"
                style={{ fontSize: 'var(--text-xs)' }}
              >
                + Add item
              </button>
              <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
                <span>Summary badge</span>
                <input
                  type="text"
                  value={side.summary || ''}
                  onChange={(e) => updateClinicalProp(sideKey, { ...side, summary: e.target.value })}
                  className={clinicalInputClass}
                  aria-label={`${sideLabel} summary`}
                />
              </label>
            </div>
          </GlassPanel>
        )
      }
      return (
        <>
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Headline</span>
            <input
              type="text"
              value={String(clinicalProps.headline || '')}
              onChange={(e) => updateClinicalProp('headline', e.target.value)}
              className={clinicalInputClass}
              aria-label="Analogy headline"
            />
          </label>
          {renderAnalogyPanel('left', left, 'Left panel')}
          {renderAnalogyPanel('right', right, 'Right panel')}
          <label className={clinicalLabelClass} style={{ fontSize: 'var(--text-xs)' }}>
            <span>Caption</span>
            <input
              type="text"
              value={String(clinicalProps.caption || '')}
              onChange={(e) => updateClinicalProp('caption', e.target.value)}
              className={clinicalInputClass}
              aria-label="Analogy caption"
            />
          </label>
        </>
      )
    }

    return null
  }

  return (
    <GlassPanel
      variant="default"
      padding="sm"
      rounded="xl"
      className="scene-inspector flex h-full min-h-0 flex-col overflow-hidden"
    >
      <div className="scene-inspector__header flex flex-wrap items-start gap-[var(--space-3)] px-[var(--space-2)] pb-[var(--space-2)]">
        <div className="scene-inspector__header-copy min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-[var(--space-2)]">
            <div
              className="text-[var(--text-primary)]"
              style={{
                fontSize: 'var(--text-sm)',
                fontWeight: 'var(--weight-medium)',
                fontFamily: 'var(--font-display)',
              }}
            >
              Scene controls
            </div>
            <span
              className="rounded-full border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-secondary)]"
              style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
            >
              Scene {sceneIndex + 1}
            </span>
            <span
              className={clsx(
                'font-[family-name:var(--font-mono)]',
                saving ? 'text-[var(--signal-active)]' : 'text-[var(--text-tertiary)]',
              )}
              style={{ fontSize: 'var(--text-xs)' }}
            >
              {saving ? 'Saving...' : 'Saved'}
            </span>
          </div>
          <div
            className="text-[var(--text-tertiary)]"
            style={{
              fontSize: 'var(--text-xs)',
              fontFamily: 'var(--font-mono)',
              marginTop: 'var(--space-1)',
            }}
          >
            Stretch this panel, collapse sections, and tune details without leaving the stage.
          </div>
        </div>
        {actions ? (
          <div className="scene-inspector__header-actions ml-auto flex shrink-0 items-center gap-[var(--space-2)] self-start">
            {actions}
          </div>
        ) : null}
      </div>

      <div
        className="scene-inspector__body flex min-h-0 flex-1 flex-col gap-[var(--space-3)] overflow-y-auto px-[var(--space-1)]"
        role="region"
        aria-label="Scene inspector"
      >
        <GlassPanel variant="inset" padding="sm">
          <div className="scene-inspector__identity flex flex-wrap items-center gap-[var(--space-3)]">
            <input
              type="text"
              value={scene.title ?? ''}
              onChange={(e) => update({ title: e.target.value })}
              placeholder="Scene title"
              className="scene-inspector__title-input min-w-0 flex-1 basis-[12rem] rounded-[var(--radius-sm)] border-none bg-transparent text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
              style={{
                fontSize: 'var(--text-sm)',
                fontFamily: 'var(--font-display)',
                fontWeight: 'var(--weight-medium)',
                padding: `var(--space-1) var(--space-2)`,
              }}
              aria-label="Scene title"
            />
            <select
              value={scene.scene_type ?? 'image'}
              onChange={(e) => {
                const nextType = e.target.value as Scene['scene_type']
                const nextFamily = nextType === 'motion'
                  ? (
                      compositionState.family && defaultCompositionModeForFamily(compositionState.family) === 'native'
                        ? compositionState.family
                        : 'kinetic_statements'
                    )
                  : String(scene.composition?.family || 'static_media')
                update({
                  scene_type: nextType,
                  composition: nextType === 'motion'
                    ? {
                        ...(scene.composition ?? {}),
                        family: nextFamily,
                        mode: 'native',
                        props: propsForCompositionFamily(
                          scene,
                          nextFamily,
                          (scene.composition?.props as Record<string, unknown> | undefined) ?? motionState.props,
                        ),
                        transition_after: scene.composition?.transition_after ?? null,
                        data: scene.composition?.data ?? {},
                        render_path: scene.composition?.render_path ?? null,
                        preview_path: scene.composition?.preview_path ?? null,
                        rationale: scene.composition?.rationale || motionState.rationale,
                      }
                    : {
                        ...(scene.composition ?? {}),
                        family: String(scene.composition?.family || 'static_media'),
                        mode: 'none',
                        props: (scene.composition?.props as Record<string, unknown> | undefined) ?? {},
                        transition_after: scene.composition?.transition_after ?? null,
                        data: scene.composition?.data ?? {},
                        render_path: scene.composition?.render_path ?? null,
                        preview_path: scene.composition?.preview_path ?? null,
                        rationale: scene.composition?.rationale || '',
                      },
                  motion: nextType === 'motion'
                    ? {
                        ...motionState,
                        template_id: nextFamily,
                        props: propsForCompositionFamily(
                          scene,
                          nextFamily,
                          (scene.composition?.props as Record<string, unknown> | undefined) ?? motionState.props,
                        ),
                      }
                    : null,
                })
              }}
              className="scene-inspector__type-select rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] text-[var(--text-secondary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
              style={{ fontSize: 'var(--text-xs)', padding: '4px 8px' }}
              aria-label="Scene type"
            >
              <option value="image">Image</option>
              <option value="video">Video</option>
              <option value="motion">Motion</option>
            </select>
          </div>
        </GlassPanel>

        {onGenerateAllAssets && (
          <GlassPanel variant="inset" padding="sm">
            <div className="flex flex-wrap items-center justify-between gap-[var(--space-3)]">
              <div className="min-w-0">
                <div className="text-[var(--text-primary)]" style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)' }}>
                  Project actions
                </div>
                <div className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  Run the whole asset pass or kick off the heavier agent-demo pass from the same control stack where you manage scene media.
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-[var(--space-2)]">
                {renderWorkspaceHref && (
                  <ActionLink href={renderWorkspaceHref}>
                    Render Workspace
                  </ActionLink>
                )}
                {onRunAgentDemoPass && (
                  <ActionButton onClick={onRunAgentDemoPass} disabled={agentDemoPending}>
                    {agentDemoPending ? 'Agent Demo Running…' : 'Agent Demo Pass'}
                  </ActionButton>
                )}
                {onRenderVideo && (
                  <ActionButton onClick={onRenderVideo} variant="primary" disabled={renderDisabled}>
                    {renderPending ? 'Rendering…' : latestProjectVideoUrl ? 'Render Again' : 'Render Video'}
                  </ActionButton>
                )}
                <ActionButton onClick={onGenerateAllAssets} disabled={generateAllPending}>
                  {generateAllPending ? 'Generating…' : 'Generate All Assets'}
                </ActionButton>
              </div>
            </div>
            {(renderReadinessCopy || latestProjectVideoUrl) && (
              <div className="flex flex-wrap items-center gap-[var(--space-2)] text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                {renderReadinessCopy && <span>{renderReadinessCopy}</span>}
                {latestProjectVideoUrl && (
                  <a
                    href={latestProjectVideoUrl}
                    className="text-[var(--accent-primary)] no-underline hover:underline outline-none focus-visible:shadow-[var(--focus-ring)] rounded-[var(--radius-sm)]"
                  >
                    Open latest render ({latestProjectVideoFilename})
                  </a>
                )}
              </div>
            )}
            {assetProgress && (
              <InlineProgress
                label={assetProgress.label}
                detail={assetProgress.detail}
                progress={assetProgress.progress}
                indeterminate={assetProgress.indeterminate}
              />
            )}
          </GlassPanel>
        )}

        <InspectorSection
          id="scene-visual"
          title="Visual"
          meta={visualMeta}
          open={sectionOpen.visual}
          onToggle={() => toggleSection('visual')}
        >
          {isMotionScene ? (
            <div className="flex flex-col gap-[var(--space-3)]">
              <div className="scene-inspector__action-row scene-inspector__action-row--compact">
                <ActionButton onClick={onGeneratePreview} variant="primary">
                  {hasMotionPreview ? 'Regenerate Motion Preview' : 'Generate Motion Preview'}
                </ActionButton>
              </div>

              <div className="grid gap-[var(--space-3)] xl:grid-cols-3">
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Composition family</span>
                  <select
                    value={compositionState.family}
                    onChange={(event) => updateComposition({
                      family: event.target.value,
                      mode: 'native',
                    })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Composition family"
                  >
                    {COMPOSITION_FAMILY_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value} disabled={!option.motionAllowed}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Transition after</span>
                  <select
                    value={compositionTransitionKind}
                    onChange={(event) => updateComposition({
                      transition_after: event.target.value
                        ? { kind: event.target.value, duration_in_frames: 20 }
                        : null,
                    })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Transition after"
                  >
                    <option value="">None</option>
                    <option value="fade">Fade</option>
                    <option value="wipe">Wipe</option>
                  </select>
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Composition mode</span>
                  <input
                    type="text"
                    value="native"
                    readOnly
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-tertiary)] outline-none"
                    aria-label="Composition mode"
                  />
                </label>
              </div>

              {isThreeDataStage ? (
                renderThreeDataStageEditor()
              ) : isClinicalTemplate ? (
                renderClinicalTemplateEditor()
              ) : isSurrealTableauFamily(compositionState.family) ? (
                <>
                  <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Layout variant</span>
                      <select
                        value={String(compositionState.props.layoutVariant || inferSurrealLayoutVariant(scene))}
                        onChange={(event) => {
                          const nextVariant = event.target.value
                          updateComposition({
                            props: {
                              layoutVariant: nextVariant,
                              orbitCount: nextVariant === 'orbit_tableau'
                                ? Number(compositionState.props.orbitCount ?? 6)
                                : 0,
                              cameraMove: nextVariant === 'orbit_tableau'
                                ? String(compositionState.props.cameraMove || 'slow circular camera orbit')
                                : String(compositionState.props.cameraMove || 'slow deliberate drift'),
                            },
                          })
                        }}
                        className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Layout variant"
                      >
                        <option value="orbit_tableau">Orbit tableau</option>
                        <option value="symbolic_duet">Symbolic duet</option>
                      </select>
                    </label>
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Copy treatment</span>
                      <select
                        value={String(compositionState.props.copyTreatment || 'none')}
                        onChange={(event) => updateComposition({ props: { copyTreatment: event.target.value } })}
                        className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Copy treatment"
                      >
                        {SURREAL_COPY_TREATMENT_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Hero object</span>
                      <input
                        type="text"
                        value={String(compositionState.props.heroObject || '')}
                        onChange={(event) => updateComposition({ props: { heroObject: event.target.value } })}
                        className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Hero object"
                      />
                    </label>
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Secondary object</span>
                      <input
                        type="text"
                        value={String(compositionState.props.secondaryObject || '')}
                        onChange={(event) => updateComposition({ props: { secondaryObject: event.target.value } })}
                        className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Secondary object"
                      />
                    </label>
                  </div>

                  <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Orbiting object</span>
                      <input
                        type="text"
                        value={String(compositionState.props.orbitingObject || '')}
                        onChange={(event) => updateComposition({ props: { orbitingObject: event.target.value } })}
                        className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Orbiting object"
                      />
                    </label>
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Orbit count</span>
                      <input
                        type="number"
                        min={0}
                        max={12}
                        value={String(compositionState.props.orbitCount ?? 0)}
                        onChange={(event) => updateComposition({ props: { orbitCount: Number(event.target.value || 0) } })}
                        className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Orbit count"
                      />
                    </label>
                  </div>

                  <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    <span>Environment backdrop</span>
                    <textarea
                      value={String(compositionState.props.environmentBackdrop || '')}
                      onChange={(event) => updateComposition({ props: { environmentBackdrop: event.target.value } })}
                      rows={2}
                      className="w-full resize-y rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                      aria-label="Environment backdrop"
                    />
                  </label>

                  <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Ambient details</span>
                      <textarea
                        value={String(compositionState.props.ambientDetails || '')}
                        onChange={(event) => updateComposition({ props: { ambientDetails: event.target.value } })}
                        rows={2}
                        className="w-full resize-y rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Ambient details"
                      />
                    </label>
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Palette words</span>
                      <input
                        type="text"
                        value={Array.isArray(compositionState.props.paletteWords) ? compositionState.props.paletteWords.map((item) => String(item)).join(', ') : String(compositionState.props.paletteWords || '')}
                        onChange={(event) => updateComposition({
                          props: {
                            paletteWords: event.target.value.split(',').map((item) => item.trim()).filter(Boolean),
                          },
                        })}
                        className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Palette words"
                      />
                    </label>
                  </div>

                  <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    <span>Camera move</span>
                    <input
                      type="text"
                      value={String(compositionState.props.cameraMove || '')}
                      onChange={(event) => updateComposition({ props: { cameraMove: event.target.value } })}
                      className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                      aria-label="Camera move"
                    />
                  </label>
                </>
              ) : (
                <>
                  <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    <span>Headline</span>
                    <input
                      type="text"
                      value={String(compositionState.props.headline || '')}
                      onChange={(event) => updateComposition({ props: { headline: event.target.value } })}
                      className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                      aria-label="Motion headline"
                    />
                  </label>

                  <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    <span>Support copy</span>
                    <textarea
                      value={String(compositionState.props.body || '')}
                      onChange={(event) => updateComposition({ props: { body: event.target.value } })}
                      rows={3}
                      className="w-full resize-y rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                      aria-label="Support copy"
                    />
                  </label>

                  <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Kicker</span>
                      <input
                        type="text"
                        value={String(compositionState.props.kicker || '')}
                        onChange={(event) => updateComposition({ props: { kicker: event.target.value } })}
                        className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Kicker"
                      />
                    </label>
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Bullets</span>
                      <textarea
                        value={Array.isArray(compositionState.props.bullets) ? compositionState.props.bullets.map((item) => String(item)).join('\n') : ''}
                        onChange={(event) => updateComposition({
                          props: {
                            bullets: event.target.value.split('\n').map((item) => item.trim()).filter(Boolean),
                          },
                        })}
                        rows={3}
                        className="w-full resize-y rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Bullets"
                      />
                    </label>
                  </div>
                </>
              )}

              <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <span>Composition rationale</span>
                <textarea
                  value={compositionState.rationale}
                  onChange={(event) => updateComposition({ rationale: event.target.value })}
                  rows={2}
                  className="w-full resize-y rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  aria-label="Composition rationale"
                />
              </label>

              <p className="m-0 text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                Motion scenes now author the canonical composition contract directly. Preview here before the final render so the family, staging, and timing all stay aligned.
              </p>
            </div>
          ) : isVideoScene ? (
            <div className="flex flex-col gap-[var(--space-3)]">
              <div className="scene-inspector__action-row scene-inspector__action-row--compact">
                <FileTriggerButton
                  accept="video/*"
                  disabled={uploadPending}
                  onFiles={(files) => onUploadVideo(files[0])}
                  onError={setLocalUploadError}
                >
                  Upload Video
                </FileTriggerButton>
                <ActionButton
                  onClick={onGenerateVideo}
                  variant="primary"
                  disabled={uploadPending || videoGeneratePending || videoGenerationProvider === 'manual'}
                >
                  {hasSceneVideo ? 'Regenerate Video' : 'Generate Video'}
                </ActionButton>
                {onRunAgentDemo && (
                  <ActionButton onClick={onRunAgentDemo} disabled={agentDemoPending}>
                    {agentDemoPending ? 'Agent Demo Running…' : 'Agent Demo Scene'}
                  </ActionButton>
                )}
              </div>

              <div className="grid gap-[var(--space-3)] xl:grid-cols-3">
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Composition family</span>
                  <select
                    value={compositionState.family}
                    onChange={(event) => updateComposition({
                      family: event.target.value,
                      mode: defaultCompositionModeForFamily(event.target.value),
                    })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Composition family"
                  >
                    {COMPOSITION_FAMILY_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Composition mode</span>
                  <select
                    value={compositionState.mode}
                    onChange={(event) => updateComposition({ mode: event.target.value as NonNullable<Scene['composition']>['mode'] })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Composition mode"
                  >
                    <option value="none">None</option>
                    <option value="overlay">Overlay</option>
                    <option value="native">Native</option>
                  </select>
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Transition after</span>
                  <select
                    value={compositionTransitionKind}
                    onChange={(event) => updateComposition({
                      transition_after: event.target.value
                        ? { kind: event.target.value, duration_in_frames: 20 }
                        : null,
                    })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Transition after"
                  >
                    <option value="">None</option>
                    <option value="fade">Fade</option>
                    <option value="wipe">Wipe</option>
                  </select>
                </label>
              </div>
              <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <span>Composition rationale</span>
                <textarea
                  value={compositionState.rationale}
                  onChange={(event) => updateComposition({ rationale: event.target.value })}
                  rows={2}
                  className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  aria-label="Composition rationale"
                />
              </label>
              {isThreeDataStage ? renderThreeDataStageEditor() : isClinicalTemplate ? renderClinicalTemplateEditor() : null}

              <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Video provider</span>
                  <select
                    value={videoGenerationProvider ?? 'manual'}
                    onChange={(event) => onVideoProfileChange?.({ provider: event.target.value })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Video provider"
                  >
                    {videoProviders.map((provider) => (
                      <option key={provider} value={provider}>
                        {provider}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Clip style</span>
                  <select
                    value={videoSceneKind}
                    onChange={(event) => update({ video_scene_kind: event.target.value === 'auto' ? null : event.target.value })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Clip style"
                  >
                    <option value="auto">Auto</option>
                    <option value="cinematic">Cinematic</option>
                    <option value="speaking">Speaking</option>
                  </select>
                </label>
              </div>

              {videoGenerationProvider === 'replicate' && (
                <>
                  <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Model selection</span>
                      <select
                        value={videoModelSelectionMode}
                        onChange={(event) => {
                          const nextMode = event.target.value
                          if (nextMode === 'automatic') {
                            onVideoProfileChange?.({
                              model_selection_mode: 'automatic',
                              generation_model: '',
                            })
                            return
                          }
                          onVideoProfileChange?.({
                            model_selection_mode: 'advanced',
                            generation_model: videoGenerationModel || DEFAULT_REPLICATE_CINEMATIC_VIDEO_MODEL,
                          })
                        }}
                        className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Model selection"
                      >
                        <option value="automatic">Automatic</option>
                        <option value="advanced">Advanced</option>
                      </select>
                    </label>
                    {videoModelSelectionMode === 'advanced' ? (
                      <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                        <span>Video model</span>
                        <select
                          value={replicateCustomModelOpen ? CUSTOM_REPLICATE_VIDEO_MODEL : replicateModelPreset}
                          onChange={(event) => {
                            const nextValue = event.target.value
                            if (nextValue === CUSTOM_REPLICATE_VIDEO_MODEL) {
                              setReplicateCustomModelOpen(true)
                              return
                            }
                            setReplicateCustomModelOpen(false)
                            onVideoProfileChange?.({ generation_model: nextValue })
                          }}
                          className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                          aria-label="Video model"
                        >
                          {REPLICATE_VIDEO_MODEL_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                          <option value={CUSTOM_REPLICATE_VIDEO_MODEL}>Custom slug</option>
                        </select>
                      </label>
                    ) : (
                      <div className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                        <span>Resolved model</span>
                        <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)]">
                          {resolvedReplicateVideoRoute?.resolvedModel ?? DEFAULT_REPLICATE_CINEMATIC_VIDEO_MODEL}
                        </div>
                      </div>
                    )}
                  </div>

                  {videoModelSelectionMode === 'advanced' && replicateCustomModelOpen && (
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Custom video model</span>
                      <input
                        type="text"
                        value={videoGenerationModel ?? ''}
                        onChange={(event) => onVideoProfileChange?.({ generation_model: event.target.value })}
                        className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Custom video model"
                      />
                    </label>
                  )}

                  <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Generation quality</span>
                      <select
                        value={videoQualityMode ?? 'standard'}
                        onChange={(event) => onVideoProfileChange?.({ quality_mode: event.target.value })}
                        className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Generation quality"
                      >
                        <option value="standard">standard</option>
                        <option value="pro">pro</option>
                      </select>
                    </label>
                    <label className="flex items-center gap-[var(--space-2)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', alignSelf: 'end' }}>
                      <input
                        type="checkbox"
                        checked={Boolean(videoGenerateAudio ?? true)}
                        onChange={(event) => onVideoProfileChange?.({ generate_audio: event.target.checked })}
                        aria-label="Generate clip audio"
                      />
                      <span>Generate clip audio</span>
                    </label>
                  </div>

                  {resolvedReplicateVideoRoute && (
                    <p className="m-0 text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      Resolved route: {resolvedReplicateVideoRoute.resolvedModel} ({resolvedReplicateVideoRoute.reason})
                    </p>
                  )}
                </>
              )}

              <p className="m-0 text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                {videoGenerationProvider === 'local'
                  ? 'Local video generation uses clip notes plus narration context. Generate audio first if you want exact duration matching.'
                  : videoGenerationProvider === 'replicate'
                  ? 'Cloud video generation creates a real scene clip from your shot direction. Automatic mode picks the cinematic or speaking lane based on clip audio plus the scene clip style. Use the scene audio source control below to choose between clip audio and separate narration.'
                  : 'Manual video mode is upload-first. Use Agent Demo when you want Cathode to run the heavier capture and review workflow in the background.'}
              </p>

              <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Scene audio source</span>
                  <select
                    value={videoAudioSource}
                    onChange={(event) => update({ video_audio_source: event.target.value })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Scene audio source"
                  >
                    <option value="narration">Narration track</option>
                    <option value="clip">Clip audio</option>
                  </select>
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Clip Start (seconds)</span>
                  <input
                    type="number"
                    min="0"
                    step="0.25"
                    value={clipStart}
                    onChange={(event) => update({ video_trim_start: Number(event.target.value) || 0 })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Clip Start (seconds)"
                  />
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Playback Speed</span>
                  <input
                    type="number"
                    min="0.25"
                    max="4"
                    step="0.05"
                    value={clipSpeed}
                    onChange={(event) => update({ video_playback_speed: Number(event.target.value) || 1 })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Playback Speed"
                  />
                </label>
              </div>

              <label className="flex items-center gap-[var(--space-2)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <input
                  type="checkbox"
                  checked={useClipUntilEnd}
                  onChange={(event) => update({ video_trim_end: event.target.checked ? null : clipStart + 1 })}
                />
                Use clip until source ends
              </label>

              {!useClipUntilEnd && (
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Clip End (seconds)</span>
                  <input
                    type="number"
                    min="0"
                    step="0.25"
                    value={clipEnd}
                    onChange={(event) => update({ video_trim_end: event.target.value === '' ? null : Number(event.target.value) })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Clip End (seconds)"
                  />
                </label>
              )}

              <label className="flex items-center gap-[var(--space-2)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <input
                  type="checkbox"
                  checked={holdLastFrame}
                  onChange={(event) => update({ video_hold_last_frame: event.target.checked })}
                />
                Freeze last frame if narration is longer
              </label>
            </div>
          ) : (
            <>
              <div className="scene-inspector__action-row scene-inspector__action-row--compact">
                <FileTriggerButton
                  accept="image/*"
                  disabled={uploadPending}
                  onFiles={(files) => onUploadImage(files[0])}
                  onError={setLocalUploadError}
                >
                  Upload Image
                </FileTriggerButton>
                <FileTriggerButton
                  accept="video/*"
                  disabled={uploadPending}
                  onFiles={(files) => onUploadVideo(files[0])}
                  onError={setLocalUploadError}
                >
                  Upload Video
                </FileTriggerButton>
                <ActionButton
                  onClick={onGenerateImage}
                  variant="primary"
                  disabled={uploadPending || imageGenerationProvider === 'manual'}
                >
                  {hasSceneImage ? 'Regenerate Image' : 'Generate Image'}
                </ActionButton>
                <ActionButton
                  onClick={() => setImageEditOpen((value) => !value)}
                  disabled={!scene.image_path || imageEditPending}
                >
                  Edit Image
                </ActionButton>
              </div>
              <div className="grid gap-[var(--space-3)] xl:grid-cols-3">
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Composition family</span>
                  <select
                    value={compositionState.family}
                    onChange={(event) => updateComposition({
                      family: event.target.value,
                      mode: defaultCompositionModeForFamily(event.target.value),
                    })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Composition family"
                  >
                    {COMPOSITION_FAMILY_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Composition mode</span>
                  <select
                    value={compositionState.mode}
                    onChange={(event) => updateComposition({ mode: event.target.value as NonNullable<Scene['composition']>['mode'] })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Composition mode"
                  >
                    <option value="none">None</option>
                    <option value="overlay">Overlay</option>
                    <option value="native">Native</option>
                  </select>
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Transition after</span>
                  <select
                    value={compositionTransitionKind}
                    onChange={(event) => updateComposition({
                      transition_after: event.target.value
                        ? { kind: event.target.value, duration_in_frames: 20 }
                        : null,
                    })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Transition after"
                  >
                    <option value="">None</option>
                    <option value="fade">Fade</option>
                    <option value="wipe">Wipe</option>
                  </select>
                </label>
              </div>
              <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <span>Composition rationale</span>
                <textarea
                  value={compositionState.rationale}
                  onChange={(event) => updateComposition({ rationale: event.target.value })}
                  rows={2}
                  className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  aria-label="Composition rationale"
                />
              </label>
              {isThreeDataStage ? renderThreeDataStageEditor() : isClinicalTemplate ? renderClinicalTemplateEditor() : null}
              {imageGenerationProvider === 'manual' && (
                <p className="m-0 text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)', marginTop: 'var(--space-2)' }}>
                  Manual image mode is upload-first. Upload a still here or switch the project image provider in Settings before generating.
                </p>
              )}
              {imageEditModel && (
                <p className="m-0 text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)', marginTop: 'var(--space-2)' }}>
                  Editor: {imageEditModel}
                </p>
              )}
              {imageEditModels.length > 0 && onImageEditModelChange && (
                <label className="mt-[var(--space-3)] flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Image editor</span>
                  <select
                    value={imageEditModel ?? ''}
                    onChange={(event) => onImageEditModelChange(event.target.value)}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Image editor"
                  >
                    {imageEditModels.map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {imageEditOpen && (
                <div className="mt-[var(--space-3)] flex flex-col gap-[var(--space-2)]">
                  <input
                    type="text"
                    value={imageEditFeedback}
                    onChange={(event) => setImageEditFeedback(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault()
                        submitImageEdit()
                      }
                    }}
                    placeholder="How should the image change?"
                    className="w-full rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    style={{
                      fontSize: 'var(--text-sm)',
                      fontFamily: 'var(--font-body)',
                      padding: `var(--space-2) var(--space-3)`,
                    }}
                    aria-label="Image edit feedback"
                  />
                  <div className="scene-inspector__action-row scene-inspector__action-row--compact">
                    <ActionButton onClick={submitImageEdit} variant="primary" disabled={!imageEditFeedback.trim() || imageEditPending}>
                      Submit Edit
                    </ActionButton>
                    <ActionButton onClick={() => {
                      setImageEditFeedback('')
                      setImageEditOpen(false)
                    }}>
                      Cancel
                    </ActionButton>
                  </div>
                </div>
              )}
            </>
          )}
          {visualProgress && (
            <InlineProgress
              label={visualProgress.label}
              detail={visualProgress.detail}
              progress={visualProgress.progress}
              indeterminate={visualProgress.indeterminate}
            />
          )}
          {activeUploadError && (
            <p
              className="m-0 text-[var(--signal-danger)]"
              style={{ fontSize: 'var(--text-xs)', marginTop: 'var(--space-2)' }}
              role="alert"
            >
              {activeUploadError}
            </p>
          )}
          {activeImageEditError && (
            <p
              className="m-0 text-[var(--signal-danger)]"
              style={{ fontSize: 'var(--text-xs)', marginTop: 'var(--space-2)' }}
              role="alert"
            >
              {activeImageEditError}
            </p>
          )}
          {videoGenerateError && (
            <p
              className="m-0 text-[var(--signal-danger)]"
              style={{ fontSize: 'var(--text-xs)', marginTop: 'var(--space-2)' }}
              role="alert"
            >
              {videoGenerateError}
            </p>
          )}
        </InspectorSection>

        <InspectorSection
          id="scene-narration"
          title="Narration"
          meta={`${wordCount} words`}
          open={sectionOpen.narration}
          onToggle={() => toggleSection('narration')}
        >
          <div className="flex flex-col gap-[var(--space-2)]">
            <textarea
              value={scene.narration ?? ''}
              onChange={(e) => update({ narration: e.target.value })}
              rows={5}
              className="w-full resize-y rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
              style={{
                fontSize: 'var(--text-sm)',
                fontFamily: 'var(--font-body)',
                padding: `var(--space-2) var(--space-3)`,
              }}
              placeholder="Narration text for this scene..."
              aria-label="Narration text"
            />
            <div className="scene-inspector__action-row">
              <ActionButton onClick={() => setNarrationFeedbackOpen((value) => !value)}>
                Refine Narration
              </ActionButton>
            </div>
            {narrationFeedbackOpen && (
              <div className="flex flex-col gap-[var(--space-2)]">
                <input
                  type="text"
                  value={narrationFeedback}
                  onChange={(e) => setNarrationFeedback(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      submitNarrationFeedback()
                    }
                  }}
                  placeholder="How should the narration change?"
                  className="w-full rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  style={{
                    fontSize: 'var(--text-sm)',
                    fontFamily: 'var(--font-body)',
                    padding: `var(--space-2) var(--space-3)`,
                  }}
                  aria-label="Narration refine feedback"
                />
                <div className="scene-inspector__action-row scene-inspector__action-row--compact">
                  <ActionButton onClick={submitNarrationFeedback} variant="primary" disabled={!narrationFeedback.trim()}>
                    Submit
                  </ActionButton>
                  <ActionButton onClick={() => {
                    setNarrationFeedback('')
                    setNarrationFeedbackOpen(false)
                  }}>
                    Cancel
                  </ActionButton>
                </div>
              </div>
            )}
          </div>
        </InspectorSection>

        <InspectorSection
          id="scene-prompt"
          title={promptSectionTitle}
          open={sectionOpen.prompt}
          onToggle={() => toggleSection('prompt')}
        >
          <div className="flex flex-col gap-[var(--space-2)]">
            <textarea
              value={scene.visual_prompt ?? ''}
              onChange={(e) => update({ visual_prompt: e.target.value })}
              rows={4}
              className="w-full resize-y rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
              style={{
                fontSize: 'var(--text-sm)',
                fontFamily: 'var(--font-body)',
                padding: `var(--space-2) var(--space-3)`,
              }}
              placeholder={promptPlaceholder}
              aria-label={isMotionScene ? 'Motion direction' : isVideoScene ? 'Clip notes / shot direction' : 'Visual prompt'}
            />
            <div className="scene-inspector__action-row">
              <ActionButton onClick={() => setPromptFeedbackOpen((value) => !value)}>{promptFeedbackLabel}</ActionButton>
            </div>
            {promptFeedbackOpen && (
              <div className="flex flex-col gap-[var(--space-2)]">
                <input
                  type="text"
                  value={promptFeedback}
                  onChange={(e) => setPromptFeedback(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      submitPromptFeedback()
                    }
                  }}
                  placeholder={promptFeedbackPlaceholder}
                  className="w-full rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  style={{
                    fontSize: 'var(--text-sm)',
                    fontFamily: 'var(--font-body)',
                    padding: `var(--space-2) var(--space-3)`,
                  }}
                  aria-label={isMotionScene ? 'Motion refine feedback' : isVideoScene ? 'Clip notes refine feedback' : 'Prompt refine feedback'}
                />
                <div className="scene-inspector__action-row scene-inspector__action-row--compact">
                  <ActionButton onClick={submitPromptFeedback} variant="primary" disabled={!promptFeedback.trim()}>
                    Submit
                  </ActionButton>
                  <ActionButton onClick={() => {
                    setPromptFeedback('')
                    setPromptFeedbackOpen(false)
                  }}>
                    Cancel
                  </ActionButton>
                </div>
              </div>
            )}
          </div>
        </InspectorSection>

        <InspectorSection
          id="scene-text"
          title="On-Screen Text"
          meta={`${(scene.on_screen_text ?? []).length} lines`}
          open={sectionOpen.text}
          onToggle={() => toggleSection('text')}
        >
          <div className="flex flex-col gap-[var(--space-2)]">
            {(scene.on_screen_text ?? []).map((text, i) => (
              <div key={i} className="scene-inspector__text-row flex min-w-0 items-center gap-[var(--space-2)]">
                <input
                  type="text"
                  value={text}
                  onChange={(e) => {
                    const next = [...(scene.on_screen_text ?? [])]
                    next[i] = e.target.value
                    update({ on_screen_text: next })
                  }}
                  className="scene-inspector__text-input min-w-0 flex-1 rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  style={{
                    fontSize: 'var(--text-sm)',
                    padding: `var(--space-1) var(--space-2)`,
                  }}
                  aria-label={`On-screen text ${i + 1}`}
                />
                <button
                  onClick={() => {
                    const next = (scene.on_screen_text ?? []).filter((_, j) => j !== i)
                    update({ on_screen_text: next })
                  }}
                  className="rounded-[var(--radius-sm)] p-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--signal-danger)]"
                  aria-label={`Remove text ${i + 1}`}
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M3 3L11 11M3 11L11 3" />
                  </svg>
                </button>
              </div>
            ))}
            <button
              onClick={() => update({ on_screen_text: [...(scene.on_screen_text ?? []), ''] })}
              className="self-start rounded-[var(--radius-sm)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)] hover:text-[var(--text-secondary)]"
              style={{ fontSize: 'var(--text-xs)' }}
            >
              + Add text
            </button>
          </div>
        </InspectorSection>

        <InspectorSection
          id="scene-audio"
          title="Audio"
          meta={isVideoScene && videoAudioSource === 'clip' ? (hasSceneAudio ? 'Clip audio' : 'Missing') : hasSceneAudio ? 'Attached' : 'Missing'}
          open={sectionOpen.audio}
          onToggle={() => toggleSection('audio')}
        >
          <div className="flex flex-col gap-[var(--space-2)]">
            <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
              <span>Speaker / Character</span>
              <input
                type="text"
                value={String(scene.speaker_name || '')}
                onChange={(event) => onSceneChange({ ...scene, speaker_name: event.target.value })}
                className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                aria-label="Speaker / Character"
                placeholder="Optional speaker label"
              />
            </label>
            {isVideoScene && videoAudioSource === 'clip' && (
              <div className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                Render uses the clip&apos;s embedded audio for this scene. Generate a narration track only if you want to switch this scene back to narration.
              </div>
            )}
            <label className="flex items-center gap-[var(--space-2)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
              <input
                type="checkbox"
                checked={sceneTtsOverrideEnabled}
                onChange={(event) => update({ tts_override_enabled: event.target.checked })}
                aria-label="Override project narrator for this scene"
              />
              Override project narrator for this scene
            </label>
            {sceneTtsOverrideEnabled && (
              <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Scene TTS Provider</span>
                  <select
                    value={sceneTtsProvider}
                      onChange={(event) => {
                        const nextProvider = event.target.value
                        const nextVoiceOptions = ttsVoiceOptions[nextProvider] ?? []
                        const currentVoice = String(scene.tts_voice || '')
                        const nextVoice = nextVoiceOptions.some((option) => option.value === currentVoice)
                          ? currentVoice
                          : (nextVoiceOptions[0]?.value || '')
                      update({
                        tts_override_enabled: true,
                        tts_provider: nextProvider,
                        tts_voice: nextVoice || null,
                      })
                    }}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Scene TTS Provider"
                  >
                    {sceneTtsProviderOptions.map((provider) => (
                      <option key={provider.value} value={provider.value}>
                        {provider.label}
                      </option>
                    ))}
                  </select>
                </label>
                {providerVoiceOptions.length > 0 ? (
                  <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    <span>Scene Voice</span>
                    <select
                      value={sceneTtsVoice}
                      onChange={(event) => update({ tts_voice: event.target.value })}
                      className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                      aria-label="Scene Voice"
                    >
                      {providerVoiceOptions.map((voiceOption) => (
                        <option key={voiceOption.value} value={voiceOption.value}>
                          {voiceOption.label}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    <span>Scene Voice</span>
                    <input
                      type="text"
                      value={sceneTtsVoice}
                      onChange={(event) => update({ tts_voice: event.target.value })}
                      className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                      aria-label="Scene Voice"
                    />
                  </label>
                )}
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Scene Voice Speed</span>
                  <input
                    type="number"
                    min={0.7}
                    max={1.4}
                    step={0.05}
                    value={Number.isFinite(sceneTtsSpeed) ? sceneTtsSpeed : 1.1}
                    onChange={(event) => update({ tts_speed: Number(event.target.value) })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Scene Voice Speed"
                  />
                </label>
              </div>
            )}
            <div className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
              Project default: {projectTtsProvider}{projectTtsVoice ? ` / ${projectTtsVoice}` : ''}
            </div>
            <div className="scene-inspector__action-row">
              <ActionButton onClick={onGenerateAudio} variant="primary">
                {hasNarrationAudio ? 'Regenerate Audio' : 'Generate Audio'}
              </ActionButton>
            </div>
            {audioProgress && (
              <InlineProgress
                label={audioProgress.label}
                detail={audioProgress.detail}
                progress={audioProgress.progress}
                indeterminate={audioProgress.indeterminate}
              />
            )}
            {hasNarrationAudio && (
              <audio
                controls
                src={projectMediaUrl(project, scene.audio_path) ?? undefined}
                className="w-full"
                style={{ height: 36 }}
              />
            )}
          </div>
        </InspectorSection>

        <InspectorSection
          id="scene-preview"
          title="Preview"
          meta={hasScenePreview ? 'Ready' : 'Missing'}
          open={sectionOpen.preview}
          onToggle={() => toggleSection('preview')}
        >
          <div className="flex flex-col gap-[var(--space-2)]">
            <div className="scene-inspector__action-row">
              <ActionButton onClick={onGeneratePreview} variant="primary">
                Generate Preview
              </ActionButton>
            </div>
            {previewProgress && (
              <InlineProgress
                label={previewProgress.label}
                detail={previewProgress.detail}
                progress={previewProgress.progress}
                indeterminate={previewProgress.indeterminate}
              />
            )}
            {hasScenePreview && (
              <video
                controls
                src={projectMediaUrl(project, scene.preview_path) ?? undefined}
                className="w-full rounded-[var(--radius-md)]"
                style={{ maxHeight: 220 }}
              />
            )}
          </div>
        </InspectorSection>

        <InspectorSection
          id="scene-operator"
          title="Operator"
          meta={actionTrace?.status ?? 'idle'}
          open={sectionOpen.operator}
          onToggle={() => toggleSection('operator')}
        >
          <div className="flex flex-col gap-[var(--space-3)]">
            <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-3)] py-[var(--space-2)]">
              <div className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                {isMotionScene ? 'Render motion preview' : isVideoScene ? 'Generate video clip' : 'Generate image'}
              </div>
              <div className="mt-[var(--space-1)] text-[var(--text-primary)]" style={{ fontSize: 'var(--text-sm)', fontFamily: 'var(--font-mono)' }}>
                {isMotionScene
                  ? `remotion / ${compositionState.family || 'kinetic_title'}`
                  : isVideoScene
                  ? `${videoGenerationProvider || 'manual'} / ${videoGenerationModel || 'default'}`
                  : `${imageGenerationProvider || 'manual'} / ${imageGenerationModel || 'default'}`}
              </div>
            </div>
            {requestPreview && (
              <pre
                className="m-0 overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] p-[var(--space-3)] text-[var(--text-tertiary)]"
                style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
              >
                {JSON.stringify(requestPreview, null, 2)}
              </pre>
            )}
            {actionTrace && (
              <div className="flex flex-col gap-[var(--space-2)] rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] p-[var(--space-3)]">
                <div className="flex items-center justify-between gap-[var(--space-3)]">
                  <div className="text-[var(--text-primary)]" style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)' }}>
                    {actionTrace.title}
                  </div>
                  <span className={clsx(
                    'rounded-full border px-[var(--space-2)] py-[2px] font-[family-name:var(--font-mono)] text-[10px]',
                    actionTrace.status === 'error'
                      ? 'border-[rgba(200,90,90,0.25)] text-[var(--signal-danger)]'
                      : actionTrace.status === 'succeeded'
                        ? 'border-[rgba(74,179,117,0.25)] text-[var(--signal-success)]'
                        : actionTrace.status === 'running'
                          ? 'border-[rgba(74,155,205,0.25)] text-[var(--signal-active)]'
                          : 'border-[var(--border-subtle)] text-[var(--text-tertiary)]',
                  )}>
                    {actionTrace.status}
                  </span>
                </div>
                <div className="text-[var(--text-tertiary)]" style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
                  {actionTrace.endpoint}
                </div>
                <pre
                  className="m-0 overflow-x-auto rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-void)] p-[var(--space-2)] text-[var(--text-tertiary)]"
                  style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
                >
                  {JSON.stringify(actionTrace.request, null, 2)}
                </pre>
                {actionTrace.error && (
                  <div className="text-[var(--signal-danger)]" role="alert" style={{ fontSize: 'var(--text-xs)' }}>
                    {actionTrace.error}
                  </div>
                )}
              </div>
            )}
            {agentDemoJob && (
              <div className="flex flex-col gap-[var(--space-2)] rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] p-[var(--space-3)]">
                <div className="flex items-center justify-between gap-[var(--space-3)]">
                  <div className="text-[var(--text-primary)]" style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)' }}>
                    Agent demo
                  </div>
                  <span className={clsx(
                    'rounded-full border px-[var(--space-2)] py-[2px] font-[family-name:var(--font-mono)] text-[10px]',
                    agentDemoJob.status === 'failed'
                      ? 'border-[rgba(200,90,90,0.25)] text-[var(--signal-danger)]'
                      : agentDemoJob.status === 'succeeded'
                        ? 'border-[rgba(74,179,117,0.25)] text-[var(--signal-success)]'
                        : 'border-[rgba(74,155,205,0.25)] text-[var(--signal-active)]',
                  )}>
                    {agentDemoJob.status}
                  </span>
                </div>
                <div className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  {agentDemoJob.progress_label || 'Background agent demo run'}
                </div>
                {agentDemoJob.progress_detail && (
                  <div className="text-[var(--text-tertiary)]" style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
                    {agentDemoJob.progress_detail}
                  </div>
                )}
                {agentDemoLog && (
                  <pre
                    className="m-0 max-h-[16rem] overflow-auto rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-void)] p-[var(--space-2)] text-[var(--text-tertiary)]"
                    style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
                  >
                    {agentDemoLog}
                  </pre>
                )}
                {agentDemoJob.suggestion && (
                  <div className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    {agentDemoJob.suggestion}
                  </div>
                )}
              </div>
            )}
            {!isVideoScene && (
              <div className="flex flex-col gap-[var(--space-2)]">
                <div className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  Recent image activity
                </div>
                {recentSceneImageHistory.length === 0 ? (
                  <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    No persisted image actions for this scene yet.
                  </div>
                ) : (
                  recentSceneImageHistory.map((entry, index) => (
                    <div
                      key={`${entry.happened_at ?? 'image-action'}-${index}`}
                      className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] p-[var(--space-3)]"
                    >
                      <div className="flex items-start justify-between gap-[var(--space-3)]">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-[var(--space-2)]">
                            <div className="text-[var(--text-primary)]" style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)' }}>
                              {formatImageActionLabel(entry.action)}
                            </div>
                            <span
                              className={`rounded-full border px-[var(--space-2)] py-[2px] font-[family-name:var(--font-mono)] text-[10px] ${imageActionStatusClass(entry.status)}`}
                            >
                              {entry.status || 'unknown'}
                            </span>
                          </div>
                          <div className="mt-[var(--space-1)] text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                            {formatImageActionSummary(entry)}
                          </div>
                        </div>
                        <div className="text-right text-[var(--text-tertiary)]" style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
                          {formatImageActionTime(entry.happened_at)}
                        </div>
                      </div>
                      {entry.error && (
                        <div className="mt-[var(--space-2)] text-[var(--signal-danger)]" role="alert" style={{ fontSize: 'var(--text-xs)' }}>
                          {entry.error}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </InspectorSection>
      </div>
    </GlassPanel>
  )
}
