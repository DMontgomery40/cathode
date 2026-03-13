import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader.tsx'
import { ProjectWorkspaceNav } from '../components/composed/ProjectWorkspaceNav.tsx'
import { TimelineStrip } from '../features/scenes/TimelineStrip.tsx'
import { MediaStage } from '../features/scenes/MediaStage.tsx'
import { SceneInspector } from '../features/scenes/SceneInspector.tsx'
import { useUIStore } from '../stores/ui.ts'
import { useBootstrap, usePlan, useRebuildStoryboard } from '../lib/api/hooks.ts'
import {
  useSavePlan,
  useUploadSceneImage,
  useUploadSceneVideo,
  useEditSceneImage,
  useGenerateSceneImage,
  useGenerateSceneVideo,
  useGenerateSceneAudio,
  useGenerateAssets,
  useStartRender,
  useJobLog,
  useProjectJobs,
  useRefinePrompt,
  useRefineNarration,
  useGenerateScenePreview,
  useRunAgentDemo,
} from '../lib/api/scene-hooks.ts'
import { LiveRegion } from '../design-system/a11y/index.ts'
import type { ImageActionHistoryEntry, Scene, Plan } from '../lib/schemas/plan.ts'
import { ResizeHandle, workspaceLayout } from '../design-system/layout'
import { getApiErrorMessage } from '../lib/api/errors.ts'
import { hasProjectMediaPath } from '../lib/media-url.ts'
import { useInvalidateProjectOnJobCompletion } from '../lib/api/project-job-sync.ts'
import { sceneHasRenderableVisual } from '../lib/scene-media.ts'

interface SceneActionTrace {
  title: string
  endpoint: string
  request: Record<string, unknown>
  status: 'idle' | 'running' | 'succeeded' | 'error'
  happenedAt: string
  error?: string | null
}

export function SceneTimeline() {
  const { projectId = '' } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const {
    selectedSceneId,
    setSelectedScene,
    sceneTimelineHeight,
    setSceneTimelineHeight,
    resetSceneTimelineHeight,
    expandSceneTimeline,
    sceneInspectorWidth,
    setSceneInspectorWidth,
    resetSceneInspectorWidth,
    sceneInspectorCollapsed,
    toggleSceneInspectorCollapsed,
    openSceneInspector,
  } = useUIStore()
  const { data: bootstrap } = useBootstrap()
  const { data: plan, isLoading, error } = usePlan(projectId)
  const savePlan = useSavePlan(projectId)
  const rebuildStoryboard = useRebuildStoryboard(projectId)
  const uploadImage = useUploadSceneImage(projectId)
  const uploadVideo = useUploadSceneVideo(projectId)
  const editImage = useEditSceneImage(projectId)
  const genImage = useGenerateSceneImage(projectId)
  const genVideo = useGenerateSceneVideo(projectId)
  const genAudio = useGenerateSceneAudio(projectId)
  const genAssets = useGenerateAssets(projectId)
  const startRender = useStartRender(projectId)
  const runAgentDemo = useRunAgentDemo(projectId)
  const { data: jobs } = useProjectJobs(projectId, { refetchInterval: 2000 })
  const refineP = useRefinePrompt(projectId)
  const refineN = useRefineNarration(projectId)
  const genPreview = useGenerateScenePreview(projectId)

  const [liveMsg, setLiveMsg] = useState('')
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [saving, setSaving] = useState(false)
  const [actionTrace, setActionTrace] = useState<SceneActionTrace | null>(null)

  // Auto-select first scene on load
  useEffect(() => {
    if (plan && plan.scenes.length > 0 && !selectedSceneId) {
      setSelectedScene(plan.scenes[0].uid)
    }
  }, [plan, selectedSceneId, setSelectedScene])

  const scenes = plan?.scenes ?? []
  const selectedScene = scenes.find((s) => s.uid === selectedSceneId) ?? null
  const selectedIndex = scenes.findIndex((s) => s.uid === selectedSceneId)
  const renderWorkspacePath = `/projects/${encodeURIComponent(projectId)}/render`

  const debouncedSave = useCallback(
    (updatedPlan: Plan) => {
      if (saveTimer.current) clearTimeout(saveTimer.current)
      setSaving(true)
      saveTimer.current = setTimeout(() => {
        savePlan.mutate(updatedPlan, {
          onSettled: () => setSaving(false),
        })
      }, 500)
    },
    [savePlan],
  )

  const handleReorder = useCallback(
    (reordered: Scene[]) => {
      if (!plan) return
      const updated: Plan = {
        ...plan,
        scenes: reordered.map((s, i) => ({ ...s, id: i + 1 })),
      }
      debouncedSave(updated)
      setLiveMsg('Scenes reordered')
    },
    [plan, debouncedSave],
  )

  const handleAddScene = useCallback(() => {
    if (!plan) return
    const compositionMode = typeof plan.meta?.brief === 'object' && plan.meta?.brief
      ? String((plan.meta.brief as Record<string, unknown>).composition_mode || 'classic')
      : 'classic'
    const sceneType: Scene['scene_type'] = compositionMode === 'motion_only' ? 'motion' : 'image'
    const uid = `scene_${Date.now()}`
    const newScene: Scene = {
      uid,
      id: scenes.length + 1,
      title: '',
      narration: '',
      visual_prompt: '',
      scene_type: sceneType,
      on_screen_text: [],
      image_path: null,
      video_path: null,
      audio_path: null,
      preview_path: null,
      motion: sceneType === 'motion'
        ? {
            template_id: 'kinetic_title',
            props: {},
            render_path: null,
            preview_path: null,
            rationale: '',
          }
        : null,
    }
    const updated: Plan = { ...plan, scenes: [...scenes, newScene] }
    debouncedSave(updated)
    setSelectedScene(uid)
    setLiveMsg('Scene added')
  }, [plan, scenes, debouncedSave, setSelectedScene])

  const handleDeleteScene = useCallback(
    (uid: string) => {
      if (!plan) return
      if (!window.confirm('Delete this scene?')) return
      const updated: Plan = {
        ...plan,
        scenes: plan.scenes.filter((s) => s.uid !== uid).map((s, i) => ({ ...s, id: i + 1 })),
      }
      debouncedSave(updated)
      if (selectedSceneId === uid) {
        setSelectedScene(updated.scenes[0]?.uid ?? null)
      }
      setLiveMsg('Scene deleted')
    },
    [plan, debouncedSave, selectedSceneId, setSelectedScene],
  )

  const handleSceneChange = useCallback(
    (updated: Scene) => {
      if (!plan) return
      const updatedPlan: Plan = {
        ...plan,
        scenes: plan.scenes.map((s) => (s.uid === updated.uid ? updated : s)),
      }
      debouncedSave(updatedPlan)
    },
    [plan, debouncedSave],
  )

  const handleStageUpload = useCallback(
    (file: File) => {
      if (!selectedScene) return
      const isVideo = file.type.startsWith('video/')
      setActionTrace({
        title: isVideo ? 'Upload scene video' : 'Upload scene image',
        endpoint: `/api/projects/${projectId}/scenes/${selectedScene.uid}/${isVideo ? 'video-upload' : 'image-upload'}`,
        request: {
          filename: file.name,
          size: file.size,
          content_type: file.type || 'unknown',
        },
        status: 'running',
        happenedAt: new Date().toISOString(),
        error: null,
      })
      if (file.type.startsWith('video/')) {
        uploadVideo.mutate(
          { sceneUid: selectedScene.uid, file },
          {
            onSuccess: () => {
              setLiveMsg('Scene video uploaded')
              setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
            },
            onError: (mutationError) => {
              const message = getApiErrorMessage(mutationError, 'Video upload failed.')
              setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
            },
          },
        )
      } else {
        uploadImage.mutate(
          { sceneUid: selectedScene.uid, file },
          {
            onSuccess: () => {
              setLiveMsg('Scene image uploaded')
              setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
            },
            onError: (mutationError) => {
              const message = getApiErrorMessage(mutationError, 'Image upload failed.')
              setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
            },
          },
        )
      }
    },
    [projectId, selectedScene, uploadImage, uploadVideo],
  )

  const hasRenderActivity = startRender.isPending || Boolean((jobs ?? []).find((job) => (job.requested_stage === 'render' || job.current_stage === 'render') && (job.status === 'queued' || job.status === 'running')))
  const hasSceneGenerationActivity = savePlan.isPending || genImage.isPending || genVideo.isPending || genAudio.isPending || genPreview.isPending || editImage.isPending || genAssets.isPending || runAgentDemo.isPending || Boolean((jobs ?? []).find((job) => job.kind === 'agent_demo' && (job.status === 'queued' || job.status === 'running')))
  const status = hasRenderActivity
    ? 'rendering' as const
    : hasSceneGenerationActivity
      ? 'generating' as const
      : error || actionTrace?.status === 'error'
        ? 'error' as const
        : 'idle' as const
  const sceneUploadPending = uploadImage.isPending || uploadVideo.isPending
  const sceneUploadError = uploadImage.error
    ? getApiErrorMessage(uploadImage.error, 'Image upload failed.')
    : uploadVideo.error
      ? getApiErrorMessage(uploadVideo.error, 'Video upload failed.')
      : null
  const timelineLayoutMode = sceneTimelineHeight >= 210 ? 'grid' : 'rail'
  const compactTimelineActions = timelineLayoutMode === 'rail' && sceneTimelineHeight <= 170
  const timelineDensityLabel = timelineLayoutMode === 'grid' ? 'Compact Rail' : 'Board View'
  const compactStageActions = !sceneInspectorCollapsed
  const imageEditModel = typeof plan?.meta?.image_profile === 'object' && plan?.meta?.image_profile
    ? String((plan.meta.image_profile as Record<string, unknown>).edit_model || '')
    : ''
  const imageProfile = typeof plan?.meta?.image_profile === 'object' && plan?.meta?.image_profile
    ? plan.meta.image_profile as Record<string, unknown>
    : {}
  const imageActionHistory = Array.isArray(plan?.meta?.image_action_history)
    ? (plan?.meta?.image_action_history as ImageActionHistoryEntry[]).filter((entry): entry is ImageActionHistoryEntry => Boolean(entry && typeof entry === 'object'))
    : []
  const imageGenerationProvider = String(imageProfile.provider || 'manual')
  const imageGenerationModel = String(imageProfile.generation_model || '')
  const videoProfile = typeof plan?.meta?.video_profile === 'object' && plan?.meta?.video_profile
    ? plan.meta.video_profile as Record<string, unknown>
    : {}
  const videoGenerationProvider = String(videoProfile.provider || 'manual')
  const videoGenerationModel = String(videoProfile.generation_model || '')
  const videoProviders = bootstrap?.providers?.video_providers ?? []
  const renderProfile = typeof plan?.meta?.render_profile === 'object' && plan?.meta?.render_profile
    ? plan.meta.render_profile as Record<string, unknown>
    : {}
  const renderBackend = String(renderProfile.render_backend || 'ffmpeg')
  const imageEditModels = bootstrap?.providers?.image_edit_models ?? []
  const imageEditError = editImage.error
    ? getApiErrorMessage(editImage.error, 'Image edit failed.')
    : null
  const videoGenerateError = genVideo.error
    ? getApiErrorMessage(genVideo.error, 'Video generation failed.')
    : null
  const videoSceneUids = scenes
    .filter((scene) => String(scene.scene_type || 'image') === 'video')
    .map((scene) => scene.uid)
  const activeAssetJob = (jobs ?? []).find(
    (job) => (job.requested_stage === 'assets' || job.current_stage === 'assets') && (job.status === 'queued' || job.status === 'running'),
  )
  const activeRenderJob = (jobs ?? []).find(
    (job) => (job.requested_stage === 'render' || job.current_stage === 'render') && (job.status === 'queued' || job.status === 'running'),
  )
  const scenesWithVisual = scenes.filter((scene) => sceneHasRenderableVisual(projectId, scene, renderBackend))
  const scenesWithAudio = scenes.filter((scene) => hasProjectMediaPath(projectId, scene.audio_path))
  const allReadyToRender = scenes.length > 0 && scenesWithVisual.length === scenes.length && scenesWithAudio.length === scenes.length
  const projectVideoPath = typeof plan?.meta?.video_path === 'string' ? plan.meta.video_path : null
  const renderOutputFilename = projectVideoPath?.split('/').pop() ?? 'final_video.mp4'
  const renderReadinessCopy = allReadyToRender
    ? (projectVideoPath ? 'Ready to re-render from the current storyboard.' : 'All visuals and audio are in place. Ready to render.')
    : `${scenesWithVisual.length}/${scenes.length} visuals and ${scenesWithAudio.length}/${scenes.length} audio ready for render.`

  useInvalidateProjectOnJobCompletion(projectId, jobs, ['assets', 'render'])

  const selectedSceneAgentJobs = [...(jobs ?? [])]
    .filter((job) => job.kind === 'agent_demo')
    .filter((job) => {
      if (!selectedScene || selectedScene.scene_type !== 'video') {
        return false
      }
      const request = job.request ?? {}
      const sceneUids = Array.isArray(request.scene_uids)
        ? request.scene_uids.map((value) => String(value))
        : []
      return sceneUids.length === 0 || sceneUids.includes(selectedScene.uid)
    })
    .sort((left, right) => {
      const leftTime = left.updated_utc ? new Date(left.updated_utc).valueOf() : 0
      const rightTime = right.updated_utc ? new Date(right.updated_utc).valueOf() : 0
      return rightTime - leftTime
    })
  const latestSelectedSceneAgentJob = selectedSceneAgentJobs[0] ?? null
  const activeSelectedSceneAgentJob = selectedSceneAgentJobs.find((job) => job.status === 'queued' || job.status === 'running') ?? null
  const { data: agentDemoLog } = useJobLog(projectId, latestSelectedSceneAgentJob?.job_id ?? null, {
    enabled: Boolean(latestSelectedSceneAgentJob),
    tailLines: 120,
  })
  const selectedSceneLabel = selectedScene
    ? `Scene ${selectedIndex + 1}${selectedScene.title ? ` - ${selectedScene.title}` : ''}`
    : 'Selected scene'
  const visualProgress = genVideo.isPending
    ? {
        label: selectedScene?.video_path ? 'Regenerating video clip' : 'Generating video clip',
        detail: selectedSceneLabel,
        progress: 0.18,
        indeterminate: true,
      }
    : genImage.isPending
    ? {
        label: selectedScene?.image_path ? 'Regenerating image' : 'Generating image',
        detail: selectedSceneLabel,
        progress: 0.18,
        indeterminate: true,
      }
    : null
  const audioProgress = genAudio.isPending
    ? {
        label: selectedScene?.audio_path ? 'Regenerating audio' : 'Generating audio',
        detail: selectedSceneLabel,
        progress: 0.18,
        indeterminate: true,
      }
    : null
  const previewProgress = genPreview.isPending
    ? {
        label: 'Generating preview',
        detail: selectedSceneLabel,
        progress: 0.18,
        indeterminate: true,
      }
    : null
  const assetProgress = activeAssetJob
    ? {
        label: activeAssetJob.progress_label || 'Generating assets',
        detail: activeAssetJob.progress_detail || `${scenes.length} scenes in current project`,
        progress: activeAssetJob.progress ?? 0.08,
        indeterminate: activeAssetJob.progress == null,
      }
    : genAssets.isPending
      ? {
          label: 'Starting asset pass',
          detail: `${scenes.length} scenes queued for generation`,
          progress: 0.08,
          indeterminate: true,
        }
      : null
  const currentImageRequestPreview = {
    generate: {
      provider: imageGenerationProvider,
      model: imageGenerationModel,
    },
    edit: {
      model: imageEditModel || null,
      dashscope_edit_n: imageProfile.dashscope_edit_n ?? null,
      dashscope_edit_seed: imageProfile.dashscope_edit_seed || null,
      dashscope_edit_negative_prompt: imageProfile.dashscope_edit_negative_prompt || null,
      dashscope_edit_prompt_extend: imageProfile.dashscope_edit_prompt_extend ?? null,
    },
    video: {
      provider: videoGenerationProvider,
      model: videoGenerationModel || null,
    },
    motion: {
      template_id: selectedScene?.motion?.template_id || null,
      props: selectedScene?.motion?.props || null,
      rationale: selectedScene?.motion?.rationale || null,
    },
    render: {
      backend: renderBackend,
      composition_mode: typeof plan?.meta?.brief === 'object' && plan?.meta?.brief
        ? (plan.meta.brief as Record<string, unknown>).composition_mode || 'classic'
        : 'classic',
    },
  }

  const handleResetWorkspace = useCallback(() => {
    resetSceneTimelineHeight()
    resetSceneInspectorWidth()
    openSceneInspector()
    setLiveMsg('Workspace layout reset')
  }, [openSceneInspector, resetSceneInspectorWidth, resetSceneTimelineHeight])

  const handleFocusStage = useCallback(() => {
    setSceneTimelineHeight(workspaceLayout.timeline.min)
    if (!sceneInspectorCollapsed) {
      toggleSceneInspectorCollapsed()
    }
    setLiveMsg('Media stage focused')
  }, [sceneInspectorCollapsed, setSceneTimelineHeight, toggleSceneInspectorCollapsed])

  const handleToggleTimelineDensity = useCallback(() => {
    if (timelineLayoutMode === 'grid') {
      resetSceneTimelineHeight()
      setLiveMsg('Timeline compacted')
      return
    }
    expandSceneTimeline()
    setLiveMsg('Timeline expanded')
  }, [expandSceneTimeline, resetSceneTimelineHeight, timelineLayoutMode])

  const handleToggleInspector = useCallback(() => {
    toggleSceneInspectorCollapsed()
    setLiveMsg(sceneInspectorCollapsed ? 'Inspector opened' : 'Inspector hidden')
  }, [sceneInspectorCollapsed, toggleSceneInspectorCollapsed])

  const handleImageProfileChange = useCallback((patch: Record<string, unknown>) => {
    if (!plan) return
    const nextPlan: Plan = {
      ...plan,
      meta: {
        ...plan.meta,
        image_profile: {
          ...(typeof plan.meta.image_profile === 'object' && plan.meta.image_profile ? plan.meta.image_profile : {}),
          ...patch,
        },
      },
    }
    debouncedSave(nextPlan)
    setLiveMsg('Image profile updated')
  }, [debouncedSave, plan])

  const handleVideoProfileChange = useCallback((patch: Record<string, unknown>) => {
    if (!plan) return
    const nextPlan: Plan = {
      ...plan,
      meta: {
        ...plan.meta,
        video_profile: {
          ...(typeof plan.meta.video_profile === 'object' && plan.meta.video_profile ? plan.meta.video_profile : {}),
          ...patch,
        },
      },
    }
    debouncedSave(nextPlan)
    setLiveMsg('Video profile updated')
  }, [debouncedSave, plan])

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <WorkspaceHeader
          title="Scenes"
          breadcrumbs={[
            { label: 'Projects', href: '/projects' },
            { label: projectId },
          ]}
        />
        <div className="flex-1 flex items-center justify-center">
          <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-sm)' }}>
            Loading plan...
          </span>
        </div>
      </div>
    )
  }

  if (!plan || scenes.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <WorkspaceHeader
          title="Scenes"
          breadcrumbs={[
            { label: 'Projects', href: '/projects' },
            { label: projectId },
          ]}
        />
        <div className="flex-1 flex flex-col items-center justify-center gap-[var(--space-4)]">
          <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-lg)' }}>
            No scenes yet
          </span>
          <button
            onClick={() => rebuildStoryboard.mutate(undefined)}
            disabled={rebuildStoryboard.isPending}
            className="rounded-[var(--radius-md)] border border-[var(--border-accent)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/20 cursor-pointer outline-none focus-visible:shadow-[var(--focus-ring)] disabled:opacity-40"
            style={{
              padding: `var(--space-3) var(--space-6)`,
              fontSize: 'var(--text-sm)',
              fontWeight: 'var(--weight-medium)',
            }}
          >
            {rebuildStoryboard.isPending ? 'Generating...' : 'Generate Storyboard'}
          </button>
        </div>
      </div>
    )
  }

  const workspaceStyle = {
    ['--scene-timeline-height' as string]: `${sceneTimelineHeight}px`,
    ['--scene-inspector-width' as string]: `${sceneInspectorWidth}px`,
  } as CSSProperties

  return (
    <div className="flex h-full min-h-0 flex-col">
      <LiveRegion message={liveMsg} />
      <WorkspaceHeader
        title="Scenes"
        subtitle={`${scenes.length} scenes`}
        breadcrumbs={[
          { label: 'Projects', href: '/projects' },
          { label: projectId, href: `/projects/${projectId}/brief` },
          { label: 'Scenes' },
        ]}
        status={status}
      />
      <ProjectWorkspaceNav projectId={projectId} />

      <div
        className="scene-workspace"
        style={workspaceStyle}
      >
        <div className="scene-workspace__timeline-shell" id="scene-timeline-panel">
          <TimelineStrip
            scenes={scenes}
            project={projectId}
            renderBackend={renderBackend}
            panelHeight={sceneTimelineHeight}
            layoutMode={timelineLayoutMode}
            actions={
              <>
                <button
                  type="button"
                  onClick={handleToggleTimelineDensity}
                  className={compactTimelineActions ? 'scene-workspace__floating-button scene-workspace__floating-button--icon' : 'scene-workspace__floating-button'}
                  aria-pressed={timelineLayoutMode === 'grid'}
                  aria-label={timelineDensityLabel}
                  title={timelineDensityLabel}
                >
                  {compactTimelineActions ? (
                    <>
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.2" aria-hidden="true">
                        <rect x="1.5" y="1.5" width="4" height="4" rx="0.75" />
                        <rect x="8.5" y="1.5" width="4" height="4" rx="0.75" />
                        <rect x="1.5" y="8.5" width="4" height="4" rx="0.75" />
                        <rect x="8.5" y="8.5" width="4" height="4" rx="0.75" />
                      </svg>
                      <span className="sr-only">{timelineDensityLabel}</span>
                    </>
                  ) : (
                    timelineDensityLabel
                  )}
                </button>
                <button
                  type="button"
                  onClick={handleResetWorkspace}
                  className={compactTimelineActions ? 'scene-workspace__floating-button scene-workspace__floating-button--icon' : 'scene-workspace__floating-button'}
                  aria-label="Reset Layout"
                  title="Reset Layout"
                >
                  {compactTimelineActions ? (
                    <>
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M11.5 4.5V1.75H8.75" />
                        <path d="M11.25 6.25A4.75 4.75 0 1 1 7 2.25c1.2 0 2.3.42 3.15 1.13" />
                      </svg>
                      <span className="sr-only">Reset Layout</span>
                    </>
                  ) : (
                    'Reset Layout'
                  )}
                </button>
              </>
            }
            onReorder={handleReorder}
            onAddScene={handleAddScene}
            onDeleteScene={handleDeleteScene}
          />
        </div>

        <ResizeHandle
          orientation="horizontal"
          label="Resize scene timeline"
          value={sceneTimelineHeight}
          min={workspaceLayout.timeline.min}
          max={workspaceLayout.timeline.max}
          onChange={setSceneTimelineHeight}
          onReset={resetSceneTimelineHeight}
          controls="scene-timeline-panel scene-workspace-body"
        />

        <div
          className="scene-workspace__body"
          id="scene-workspace-body"
          style={sceneInspectorCollapsed ? { gridTemplateColumns: 'minmax(0, 1fr)' } : undefined}
        >
          <div className="scene-workspace__stage-shell" id="scene-media-stage">
            <MediaStage
              scene={selectedScene}
              project={projectId}
              actions={
                <>
                  <button
                    type="button"
                    onClick={handleFocusStage}
                    className="scene-workspace__floating-button scene-workspace__floating-button--icon"
                    aria-label="Focus Canvas"
                    title="Focus Canvas"
                  >
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M4.25 2H2v2.25" />
                      <path d="M9.75 2H12v2.25" />
                      <path d="M12 9.75V12H9.75" />
                      <path d="M4.25 12H2V9.75" />
                    </svg>
                    <span className="sr-only">Focus Canvas</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleToggleInspector}
                    className="scene-workspace__floating-button scene-workspace__floating-button--icon"
                    aria-expanded={!sceneInspectorCollapsed}
                    aria-controls="scene-inspector-panel"
                    aria-label={sceneInspectorCollapsed ? 'Show Inspector' : 'Hide Inspector'}
                    title={sceneInspectorCollapsed ? 'Show Inspector' : 'Hide Inspector'}
                  >
                    {sceneInspectorCollapsed ? (
                      <>
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <rect x="2" y="2.5" width="10" height="9" rx="1.5" />
                          <path d="M8.25 3v8" />
                        </svg>
                        <span className="sr-only">Show Inspector</span>
                      </>
                    ) : (
                      <>
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <rect x="2" y="2.5" width="10" height="9" rx="1.5" />
                          <path d="M8.25 3v8" />
                          <path d="M5.25 7H11.5" />
                        </svg>
                        <span className="sr-only">Hide Inspector</span>
                      </>
                    )}
                  </button>
                </>
              }
              onUpload={handleStageUpload}
              uploadPending={sceneUploadPending}
              uploadError={sceneUploadError}
              compactActions={compactStageActions}
            />
          </div>

          {!sceneInspectorCollapsed && (
            <>
              <ResizeHandle
                orientation="vertical"
                label="Resize scene inspector"
                value={sceneInspectorWidth}
                min={workspaceLayout.inspector.min}
                max={workspaceLayout.inspector.max}
                onChange={setSceneInspectorWidth}
                onReset={resetSceneInspectorWidth}
                direction={-1}
                controls="scene-media-stage scene-inspector-panel"
              />

              <div className="scene-workspace__inspector-shell" id="scene-inspector-panel">
                <SceneInspector
                  scene={selectedScene}
                  project={projectId}
                  sceneIndex={selectedIndex}
                  saving={saving || savePlan.isPending}
                  actions={
                    <button
                      type="button"
                      onClick={handleToggleInspector}
                      className="scene-workspace__floating-button"
                    >
                      Collapse Panel
                    </button>
                  }
                  onSceneChange={handleSceneChange}
                  onUploadImage={handleStageUpload}
                  onUploadVideo={handleStageUpload}
                  uploadPending={sceneUploadPending}
                  uploadError={sceneUploadError}
                  imageEditModel={imageEditModel}
                  imageEditModels={imageEditModels}
                  onImageEditModelChange={(model) => handleImageProfileChange({ edit_model: model })}
                  imageGenerationProvider={imageGenerationProvider}
                  imageGenerationModel={imageGenerationModel}
                  requestPreview={currentImageRequestPreview}
                  actionTrace={actionTrace}
                  imageActionHistory={imageActionHistory}
                  onEditImage={(feedback) => {
                    if (!selectedScene) return
                    setActionTrace({
                      title: 'Edit scene image',
                      endpoint: `/api/projects/${projectId}/scenes/${selectedScene.uid}/image-edit`,
                      request: {
                        feedback,
                        model: imageEditModel || null,
                        dashscope_edit_n: imageProfile.dashscope_edit_n ?? null,
                        dashscope_edit_seed: imageProfile.dashscope_edit_seed || null,
                        dashscope_edit_negative_prompt: imageProfile.dashscope_edit_negative_prompt || null,
                        dashscope_edit_prompt_extend: imageProfile.dashscope_edit_prompt_extend ?? null,
                      },
                      status: 'running',
                      happenedAt: new Date().toISOString(),
                      error: null,
                    })
                    editImage.mutate(
                      { sceneUid: selectedScene.uid, feedback, opts: imageEditModel ? { model: imageEditModel } : undefined },
                      {
                        onSuccess: () => {
                          setLiveMsg('Image edit completed')
                          setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
                        },
                        onError: (mutationError) => {
                          const message = getApiErrorMessage(mutationError, 'Image edit failed.')
                          setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
                        },
                      },
                    )
                  }}
                  imageEditPending={editImage.isPending}
                  imageEditError={imageEditError}
                  onGenerateImage={() => {
                    if (!selectedScene) return
                    setActionTrace({
                      title: 'Generate scene image',
                      endpoint: `/api/projects/${projectId}/scenes/${selectedScene.uid}/image-generate`,
                      request: {
                        provider: imageGenerationProvider,
                        model: imageGenerationModel,
                      },
                      status: 'running',
                      happenedAt: new Date().toISOString(),
                      error: null,
                    })
                    genImage.mutate({ sceneUid: selectedScene.uid, opts: { provider: imageGenerationProvider, model: imageGenerationModel } }, {
                      onSuccess: () => {
                        setLiveMsg('Scene image generated')
                        setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
                      },
                      onError: (mutationError) => {
                        const message = getApiErrorMessage(mutationError, 'Image generation failed.')
                        setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
                      },
                    })
                  }}
                  videoGenerationProvider={videoGenerationProvider}
                  videoGenerationModel={videoGenerationModel}
                  videoProviders={videoProviders}
                  onVideoProfileChange={handleVideoProfileChange}
                  onGenerateVideo={() => {
                    if (!selectedScene) return
                    setActionTrace({
                      title: 'Generate scene video',
                      endpoint: `/api/projects/${projectId}/scenes/${selectedScene.uid}/video-generate`,
                      request: {
                        provider: videoGenerationProvider,
                        model: videoGenerationModel || null,
                      },
                      status: 'running',
                      happenedAt: new Date().toISOString(),
                      error: null,
                    })
                    genVideo.mutate(
                      {
                        sceneUid: selectedScene.uid,
                        opts: { provider: videoGenerationProvider, model: videoGenerationModel || undefined },
                      },
                      {
                        onSuccess: () => {
                          setLiveMsg('Scene video generated')
                          setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
                        },
                        onError: (mutationError) => {
                          const message = getApiErrorMessage(mutationError, 'Video generation failed.')
                          setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
                        },
                      },
                    )
                  }}
                  videoGeneratePending={genVideo.isPending}
                  videoGenerateError={videoGenerateError}
                  onGenerateAudio={() => {
                    if (!selectedScene) return
                    setActionTrace({
                      title: 'Generate scene audio',
                      endpoint: `/api/projects/${projectId}/scenes/${selectedScene.uid}/audio-generate`,
                      request: {},
                      status: 'running',
                      happenedAt: new Date().toISOString(),
                      error: null,
                    })
                    genAudio.mutate(
                      { sceneUid: selectedScene.uid },
                      {
                        onSuccess: () => {
                          setLiveMsg('Scene audio generated')
                          setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
                        },
                        onError: (mutationError) => {
                          const message = getApiErrorMessage(mutationError, 'Audio generation failed.')
                          setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
                        },
                      },
                    )
                  }}
                  onGenerateAllAssets={() => {
                    setActionTrace({
                      title: 'Generate all assets',
                      endpoint: `/api/projects/${projectId}/assets`,
                      request: { stage: 'assets', project: projectId },
                      status: 'running',
                      happenedAt: new Date().toISOString(),
                      error: null,
                    })
                    genAssets.mutate(undefined, {
                      onSuccess: () => {
                        setLiveMsg('Asset generation started')
                        setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
                      },
                      onError: (mutationError) => {
                        const message = getApiErrorMessage(mutationError, 'Asset generation failed.')
                        setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
                      },
                    })
                  }}
                  generateAllPending={genAssets.isPending || Boolean(activeAssetJob)}
                  onRenderVideo={() => {
                    setActionTrace({
                      title: 'Render project video',
                      endpoint: `/api/projects/${projectId}/render`,
                      request: { output_filename: renderOutputFilename },
                      status: 'running',
                      happenedAt: new Date().toISOString(),
                      error: null,
                    })
                    startRender.mutate(
                      { output_filename: renderOutputFilename },
                      {
                        onSuccess: () => {
                          setLiveMsg('Render started')
                          setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
                          navigate(renderWorkspacePath)
                        },
                        onError: (mutationError) => {
                          const message = getApiErrorMessage(mutationError, 'Render failed to start.')
                          setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
                        },
                      },
                    )
                  }}
                  renderPending={startRender.isPending || Boolean(activeRenderJob)}
                  renderDisabled={!allReadyToRender || startRender.isPending || Boolean(activeRenderJob) || Boolean(activeAssetJob)}
                  renderWorkspaceHref={renderWorkspacePath}
                  projectVideoPath={projectVideoPath}
                  renderReadinessCopy={renderReadinessCopy}
                  onRunAgentDemo={() => {
                    if (!selectedScene) return
                    setActionTrace({
                      title: 'Run agent demo for scene',
                      endpoint: `/api/projects/${projectId}/agent-demo`,
                      request: {
                        scene_uids: [selectedScene.uid],
                        run_until: 'assets',
                      },
                      status: 'running',
                      happenedAt: new Date().toISOString(),
                      error: null,
                    })
                    runAgentDemo.mutate(
                      { scene_uids: [selectedScene.uid], run_until: 'assets' },
                      {
                        onSuccess: () => {
                          setLiveMsg('Agent demo job started')
                          setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
                        },
                        onError: (mutationError) => {
                          const message = getApiErrorMessage(mutationError, 'Agent demo failed to start.')
                          setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
                        },
                      },
                    )
                  }}
                  onRunAgentDemoPass={videoSceneUids.length > 0 ? () => {
                    setActionTrace({
                      title: 'Run agent demo pass',
                      endpoint: `/api/projects/${projectId}/agent-demo`,
                      request: {
                        scene_uids: videoSceneUids,
                        run_until: 'assets',
                      },
                      status: 'running',
                      happenedAt: new Date().toISOString(),
                      error: null,
                    })
                    runAgentDemo.mutate(
                      { scene_uids: videoSceneUids, run_until: 'assets' },
                      {
                        onSuccess: () => {
                          setLiveMsg('Agent demo pass started')
                          setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
                        },
                        onError: (mutationError) => {
                          const message = getApiErrorMessage(mutationError, 'Agent demo pass failed to start.')
                          setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
                        },
                      },
                    )
                  } : undefined}
                  agentDemoPending={runAgentDemo.isPending || Boolean(activeSelectedSceneAgentJob)}
                  agentDemoJob={latestSelectedSceneAgentJob}
                  agentDemoLog={agentDemoLog?.content ?? null}
                  onRefinePrompt={(feedback) => {
                    if (!selectedScene) return
                    setActionTrace({
                      title: 'Refine prompt',
                      endpoint: `/api/projects/${projectId}/scenes/${selectedScene.uid}/prompt-refine`,
                      request: { feedback },
                      status: 'running',
                      happenedAt: new Date().toISOString(),
                      error: null,
                    })
                    refineP.mutate(
                      { sceneUid: selectedScene.uid, feedback },
                      {
                        onSuccess: () => {
                          setLiveMsg('Prompt refined')
                          setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
                        },
                        onError: (mutationError) => {
                          const message = getApiErrorMessage(mutationError, 'Prompt refinement failed.')
                          setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
                        },
                      },
                    )
                  }}
                  onRefineNarration={(feedback) => {
                    if (!selectedScene) return
                    setActionTrace({
                      title: 'Refine narration',
                      endpoint: `/api/projects/${projectId}/scenes/${selectedScene.uid}/narration-refine`,
                      request: { feedback },
                      status: 'running',
                      happenedAt: new Date().toISOString(),
                      error: null,
                    })
                    refineN.mutate(
                      { sceneUid: selectedScene.uid, feedback },
                      {
                        onSuccess: () => {
                          setLiveMsg('Narration refined')
                          setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
                        },
                        onError: (mutationError) => {
                          const message = getApiErrorMessage(mutationError, 'Narration refinement failed.')
                          setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
                        },
                      },
                    )
                  }}
                  onGeneratePreview={() => {
                    if (!selectedScene) return
                    setActionTrace({
                      title: 'Generate preview',
                      endpoint: `/api/projects/${projectId}/scenes/${selectedScene.uid}/preview`,
                      request: { scene_uid: selectedScene.uid },
                      status: 'running',
                      happenedAt: new Date().toISOString(),
                      error: null,
                    })
                    genPreview.mutate(selectedScene.uid, {
                      onSuccess: () => {
                        setLiveMsg('Preview generated')
                        setActionTrace((current) => current ? { ...current, status: 'succeeded', error: null } : current)
                      },
                      onError: (mutationError) => {
                        const message = getApiErrorMessage(mutationError, 'Preview generation failed.')
                        setActionTrace((current) => current ? { ...current, status: 'error', error: message } : current)
                      },
                    })
                  }}
                  assetProgress={assetProgress}
                  visualProgress={visualProgress}
                  audioProgress={audioProgress}
                  previewProgress={previewProgress}
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
