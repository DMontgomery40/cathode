import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { FileTriggerButton } from '../../components/primitives/FileTriggerButton.tsx'
import { useReducedMotion, transitions } from '../../design-system/motion'
import { formatImageActionLabel, formatImageActionSummary, formatImageActionTime, imageActionStatusClass } from '../../lib/image-action-history.ts'
import type { ImageActionHistoryEntry, Scene } from '../../lib/schemas/plan.ts'
import { projectMediaUrl } from '../../lib/media-url.ts'
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

  useEffect(() => {
    sceneDraftRef.current = scene
  }, [scene])

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
  const latestProjectVideoFilename = projectVideoPath?.split('/').pop() ?? 'final_video.mp4'

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

  const motionState = {
    template_id: String(scene.motion?.template_id || scene.composition?.family || 'kinetic_title'),
    props: typeof scene.motion?.props === 'object' && scene.motion?.props
      ? scene.motion.props
      : typeof scene.composition?.props === 'object' && scene.composition?.props
        ? scene.composition.props
        : {},
    render_path: scene.motion?.render_path ?? scene.composition?.render_path ?? null,
    preview_path: scene.motion?.preview_path ?? scene.composition?.preview_path ?? null,
    rationale: String(scene.motion?.rationale || scene.composition?.rationale || ''),
  }
  const compositionState = {
    family: String(scene.composition?.family || (scene.scene_type === 'motion' ? motionState.template_id : 'static_media')),
    mode: String(scene.composition?.mode || (scene.scene_type === 'motion' ? 'native' : 'none')),
    transition_after: scene.composition?.transition_after ?? null,
    props: typeof scene.composition?.props === 'object' && scene.composition?.props ? scene.composition.props : {},
    data: scene.composition?.data ?? {},
    render_path: scene.composition?.render_path ?? null,
    preview_path: scene.composition?.preview_path ?? null,
    rationale: String(scene.composition?.rationale || ''),
  }
  const updateComposition = (patch: Partial<NonNullable<Scene['composition']>>) => {
    const currentScene = sceneDraftRef.current ?? scene
    const nextComposition = {
      ...compositionState,
      ...patch,
      props: {
        ...compositionState.props,
        ...((patch.props as Record<string, unknown> | undefined) ?? {}),
      },
    }
    const nextScene = {
      ...currentScene,
      composition: nextComposition,
      motion: nextComposition.mode === 'native' || currentScene.scene_type === 'motion'
        ? {
            ...motionState,
            template_id: String(nextComposition.family || motionState.template_id || 'kinetic_title'),
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
  const updateMotion = (patch: Partial<NonNullable<Scene['motion']>>) => {
    const currentScene = sceneDraftRef.current ?? scene
    const nextMotion = {
      ...motionState,
      ...patch,
      props: {
        ...motionState.props,
        ...(patch.props ?? {}),
      },
    }
    const nextScene = {
      ...currentScene,
      composition: {
        ...(currentScene.composition ?? {
          family: 'kinetic_title',
          mode: 'native',
          props: {},
          transition_after: null,
          data: {},
          render_path: null,
          preview_path: null,
          rationale: '',
        }),
        family: String(nextMotion.template_id || 'kinetic_title'),
        mode: 'native',
        props: nextMotion.props ?? {},
        render_path: nextMotion.render_path ?? null,
        preview_path: nextMotion.preview_path ?? null,
        rationale: nextMotion.rationale ?? '',
      },
      motion: {
        ...nextMotion,
      },
    }
    sceneDraftRef.current = nextScene
    onSceneChange(nextScene)
  }

  const wordCount = scene.narration ? scene.narration.trim().split(/\s+/).filter(Boolean).length : 0
  const sceneType = scene.scene_type ?? 'image'
  const isVideoScene = sceneType === 'video'
  const isMotionScene = sceneType === 'motion'
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

  return (
    <GlassPanel
      variant="default"
      padding="sm"
      rounded="xl"
      className="scene-inspector flex h-full min-h-0 flex-col overflow-hidden"
    >
      <div className="scene-inspector__header flex items-start justify-between gap-[var(--space-3)] px-[var(--space-2)] pb-[var(--space-3)]">
        <div className="scene-inspector__header-copy min-w-0">
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
          <div
            className="text-[var(--text-tertiary)]"
            style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)' }}
          >
            Stretch this panel, collapse sections, and tune details without leaving the stage.
          </div>
        </div>
        <div className="scene-inspector__header-status flex flex-col items-end gap-[var(--space-2)]">
          {actions ? <div className="flex items-center gap-[var(--space-2)]">{actions}</div> : null}
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
                update({
                  scene_type: nextType,
                  composition: nextType === 'motion'
                    ? {
                        ...(scene.composition ?? {}),
                        family: String(scene.composition?.family || motionState.template_id || 'kinetic_title'),
                        mode: 'native',
                        props: (scene.composition?.props as Record<string, unknown> | undefined) ?? motionState.props,
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
                        template_id: motionState.template_id || 'kinetic_title',
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

              <div className="grid gap-[var(--space-3)] xl:grid-cols-2">
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Motion template</span>
                  <select
                    value={motionState.template_id}
                    onChange={(event) => updateMotion({ template_id: event.target.value })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Motion template"
                  >
                    <option value="kinetic_title">Kinetic Title</option>
                    <option value="bullet_stack">Bullet Stack</option>
                    <option value="quote_focus">Quote Focus</option>
                  </select>
                </label>
                <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  <span>Accent label</span>
                  <input
                    type="text"
                    value={String(motionState.props.accent || '')}
                    onChange={(event) => updateMotion({ props: { accent: event.target.value } })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Accent label"
                  />
                </label>
              </div>

              <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <span>Headline</span>
                <input
                  type="text"
                  value={String(motionState.props.headline || '')}
                  onChange={(event) => updateMotion({ props: { headline: event.target.value } })}
                  className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  aria-label="Motion headline"
                />
              </label>

              <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <span>Support copy</span>
                <textarea
                  value={String(motionState.props.body || '')}
                  onChange={(event) => updateMotion({ props: { body: event.target.value } })}
                  rows={3}
                  className="w-full resize-y rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  aria-label="Support copy"
                />
              </label>

              <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                <span>Motion rationale</span>
                <textarea
                  value={motionState.rationale}
                  onChange={(event) => updateMotion({ rationale: event.target.value })}
                  rows={2}
                  className="w-full resize-y rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                  aria-label="Motion rationale"
                />
              </label>

              <p className="m-0 text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                Motion scenes render through Remotion using the current narration timing. Use the template to structure the beat, then preview it before the final render.
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
                    onChange={(event) => updateComposition({ family: event.target.value })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Composition family"
                  >
                    <option value="static_media">Static media</option>
                    <option value="software_demo_focus">Software demo focus</option>
                    <option value="media_pan">Media pan</option>
                    <option value="kinetic_statements">Kinetic statements</option>
                    <option value="three_data_stage">Three data stage</option>
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
                    onChange={(event) => updateComposition({ family: event.target.value })}
                    className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    aria-label="Composition family"
                  >
                    <option value="static_media">Static media</option>
                    <option value="media_pan">Media pan</option>
                    <option value="software_demo_focus">Software demo focus</option>
                    <option value="kinetic_statements">Kinetic statements</option>
                    <option value="three_data_stage">Three data stage</option>
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
                  ? `remotion / ${motionState.template_id || 'kinetic_title'}`
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
