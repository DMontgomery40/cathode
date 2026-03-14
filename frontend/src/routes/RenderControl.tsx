import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { clsx } from 'clsx'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader.tsx'
import { ProjectWorkspaceNav } from '../components/composed/ProjectWorkspaceNav.tsx'
import { RenderSettings } from '../features/render/RenderSettings.tsx'
import { RenderProgress } from '../features/render/RenderProgress.tsx'
import { ArtifactShelf } from '../features/render/ArtifactShelf.tsx'
import { CostPanel } from '../features/projects/CostPanel.tsx'
import { useBootstrap, usePlan, useRemotionManifest } from '../lib/api/hooks.ts'
import {
  useStartRender,
  useGenerateAssets,
  useProjectJobs,
  useCancelJob,
  useJobLog,
  useSavePlan,
} from '../lib/api/scene-hooks.ts'
import type { Job } from '../lib/api/jobs.ts'
import { WorkspaceCanvas, WorkspaceGrid, WorkspacePanel } from '../design-system/recipes'
import { sceneHasRenderableAudio, sceneHasRenderableVisual } from '../lib/scene-media.ts'
import { useInvalidateProjectOnJobCompletion } from '../lib/api/project-job-sync.ts'
import { PlayerSurface } from '../remotion/PlayerSurface.tsx'

const DEFAULT_OUTPUT_FILENAME = 'final_video.mp4'
const DEFAULT_FPS = 24

function resolveRenderFps(renderProfile: Record<string, unknown> | null): number {
  const parsed = Number(renderProfile?.fps ?? DEFAULT_FPS)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_FPS
}

function resolveTextRenderMode(
  renderProfile: Record<string, unknown> | null,
  brief: Record<string, unknown> | null,
): string {
  const candidate = String(renderProfile?.text_render_mode ?? brief?.text_render_mode ?? 'visual_authored').trim().toLowerCase()
  return candidate === 'deterministic_overlay' ? 'deterministic_overlay' : 'visual_authored'
}

export function RenderControl() {
  const { projectId = '' } = useParams<{ projectId: string }>()
  const { data: bootstrap } = useBootstrap()
  const { data: plan } = usePlan(projectId)
  const remotionManifest = useRemotionManifest(projectId, {
    enabled: Boolean(bootstrap?.providers?.remotion_capabilities?.player_available && projectId),
  })
  const { data: jobs } = useProjectJobs(projectId, { refetchInterval: 2000 })
  const startRender = useStartRender(projectId)
  const genAssets = useGenerateAssets(projectId)
  const cancelJobMut = useCancelJob()
  const savePlan = useSavePlan(projectId)

  const [outputFilename, setOutputFilename] = useState(DEFAULT_OUTPUT_FILENAME)
  const [fps, setFps] = useState(DEFAULT_FPS)
  const [outputFilenameDirty, setOutputFilenameDirty] = useState(false)
  const [fpsDirty, setFpsDirty] = useState(false)
  const [textRenderMode, setTextRenderMode] = useState('visual_authored')
  const [textRenderModeDirty, setTextRenderModeDirty] = useState(false)

  const scenes = plan?.scenes ?? []
  const renderProfile = plan?.meta?.render_profile ?? null
  const brief = typeof plan?.meta?.brief === 'object' && plan?.meta?.brief
    ? plan.meta.brief as Record<string, unknown>
    : null
  const renderBackend = typeof renderProfile === 'object' && renderProfile
    ? String((renderProfile as Record<string, unknown>).render_backend || 'ffmpeg')
    : 'ffmpeg'
  const planTextRenderMode = resolveTextRenderMode(
    typeof renderProfile === 'object' && renderProfile
      ? renderProfile as Record<string, unknown>
      : null,
    brief,
  )

  // Readiness checks
  const scenesWithVisual = scenes.filter((s) => sceneHasRenderableVisual(projectId, s, renderBackend))
  const scenesWithAudio = scenes.filter((s) => sceneHasRenderableAudio(projectId, s))
  const allReady = scenes.length > 0 && scenesWithVisual.length === scenes.length && scenesWithAudio.length === scenes.length

  const renderJobs = [...(jobs ?? [])]
    .filter((j) => j.requested_stage === 'render' || j.requested_stage === 'assets' || j.current_stage === 'render' || j.current_stage === 'assets')
    .sort((left, right) => {
      const leftTime = left.updated_utc ? new Date(left.updated_utc).valueOf() : 0
      const rightTime = right.updated_utc ? new Date(right.updated_utc).valueOf() : 0
      return rightTime - leftTime
    })
  // Find active render/asset jobs
  const activeRenderJob: Job | null = renderJobs.find(
    (j) => (j.requested_stage === 'render' || j.requested_stage === 'assets') && (j.status === 'queued' || j.status === 'running'),
  ) ?? null
  const latestRenderJob: Job | null = renderJobs[0] ?? null

  const hasActiveJob = activeRenderJob !== null
  const existingOutputFilename = typeof plan?.meta?.video_path === 'string' && plan.meta.video_path
    ? plan.meta.video_path.split('/').pop() ?? DEFAULT_OUTPUT_FILENAME
    : DEFAULT_OUTPUT_FILENAME
  const renderFps = resolveRenderFps(
    typeof renderProfile === 'object' && renderProfile
      ? renderProfile as Record<string, unknown>
      : null,
  )

  useInvalidateProjectOnJobCompletion(projectId, jobs, ['assets', 'render'])
  const { data: renderLog } = useJobLog(projectId, (activeRenderJob ?? latestRenderJob)?.job_id ?? null, {
    enabled: Boolean(activeRenderJob ?? latestRenderJob),
    tailLines: 160,
  })

  useEffect(() => {
    setOutputFilenameDirty(false)
    setFpsDirty(false)
    setOutputFilename(DEFAULT_OUTPUT_FILENAME)
    setFps(DEFAULT_FPS)
    setTextRenderModeDirty(false)
    setTextRenderMode('visual_authored')
  }, [projectId])

  useEffect(() => {
    if (!outputFilenameDirty) {
      setOutputFilename(existingOutputFilename)
    }
  }, [existingOutputFilename, outputFilenameDirty])

  useEffect(() => {
    if (!fpsDirty) {
      setFps(renderFps)
    }
  }, [fpsDirty, renderFps])

  useEffect(() => {
    if (!textRenderModeDirty) {
      setTextRenderMode(planTextRenderMode)
    }
  }, [planTextRenderMode, textRenderModeDirty])

  const handleOutputFilenameChange = (value: string) => {
    setOutputFilenameDirty(true)
    setOutputFilename(value)
  }

  const handleFpsChange = (value: number) => {
    setFpsDirty(true)
    setFps(value)
  }

  const handleTextRenderModeChange = (value: string) => {
    if (!plan || savePlan.isPending) return
    setTextRenderModeDirty(true)
    setTextRenderMode(value)
    savePlan.mutate(
      {
        ...plan,
        meta: {
          ...plan.meta,
          brief: {
            ...(brief ?? {}),
            text_render_mode: value,
          },
          render_profile: {
            ...(typeof renderProfile === 'object' && renderProfile ? renderProfile as Record<string, unknown> : {}),
            text_render_mode: value,
          },
        },
      },
      {
        onSettled: () => {
          setTextRenderModeDirty(false)
        },
      },
    )
  }

  const status = hasActiveJob
    ? 'rendering' as const
    : startRender.isError || genAssets.isError || savePlan.isError
      ? 'error' as const
      : 'idle' as const

  return (
    <div className="flex flex-col h-full">
      <WorkspaceHeader
        title="Render"
        subtitle={projectId}
        breadcrumbs={[
          { label: 'Projects', href: '/projects' },
          { label: projectId, href: `/projects/${projectId}/scenes` },
          { label: 'Render' },
        ]}
        status={status}
      />
      <ProjectWorkspaceNav projectId={projectId} />

      <WorkspaceCanvas>
        <WorkspaceGrid
          asideWidth={340}
          main={(
            <div className="workspace-panel-stack">
              <WorkspacePanel
                title="Render surface"
                eyebrow="Output"
                copy="The final render should stay front and center, with settings and gating details acting like a sidecar instead of overwhelming the canvas."
              >
                {remotionManifest.data && (
                  <div style={{ marginBottom: 'var(--space-4)' }}>
                    <PlayerSurface manifest={remotionManifest.data} height={420} />
                  </div>
                )}
                <ArtifactShelf
                  videoPath={plan?.meta?.video_path}
                  videoExists={typeof plan?.meta?.video_exists === 'boolean' ? plan.meta.video_exists : undefined}
                  project={projectId}
                />
              </WorkspacePanel>

              <RenderProgress
                job={activeRenderJob ?? latestRenderJob}
                logContent={renderLog?.content ?? null}
                onCancel={() => {
                  if (activeRenderJob) {
                    cancelJobMut.mutate({ jobId: activeRenderJob.job_id, project: projectId })
                  }
                }}
              />
            </div>
          )}
          aside={(
            <div className="workspace-panel-stack">
              <WorkspacePanel
                title="Render actions"
                eyebrow="Execution"
                copy="Launch the full asset pass or the final render from the render workspace itself, not from the page chrome."
              >
                <div className="flex flex-col gap-[var(--space-3)]">
                  <button
                    onClick={() => genAssets.mutate()}
                    disabled={scenes.length === 0 || genAssets.isPending || hasActiveJob}
                    className={clsx(
                      'rounded-[var(--radius-md)] border cursor-pointer outline-none text-left',
                      'focus-visible:shadow-[var(--focus-ring)]',
                      'disabled:opacity-40 disabled:cursor-not-allowed',
                      'border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)]',
                    )}
                    style={{
                      padding: `var(--space-3) var(--space-4)`,
                      fontSize: 'var(--text-sm)',
                      fontWeight: 'var(--weight-medium)',
                    }}
                  >
                    <div>Generate All Assets</div>
                    <div className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)', marginTop: 'var(--space-1)' }}>
                      Refresh images, audio, and any missing scene media before the final render.
                    </div>
                  </button>
                  <button
                    onClick={() => startRender.mutate({ output_filename: outputFilename, fps })}
                    disabled={!allReady || startRender.isPending || hasActiveJob || savePlan.isPending}
                    className={clsx(
                      'rounded-[var(--radius-md)] border cursor-pointer outline-none text-left',
                      'focus-visible:shadow-[var(--focus-ring)]',
                      'disabled:opacity-40 disabled:cursor-not-allowed',
                      'border-[var(--border-accent)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/20',
                    )}
                    style={{
                      padding: `var(--space-3) var(--space-4)`,
                      fontSize: 'var(--text-sm)',
                      fontWeight: 'var(--weight-medium)',
                    }}
                  >
                    <div>Render Video</div>
                    <div className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)', marginTop: 'var(--space-1)' }}>
                      Assemble the current storyboard into the final MP4 when the readiness gate is green.
                    </div>
                  </button>
                </div>
              </WorkspacePanel>

              <CostPanel plan={plan} />

              <RenderSettings
                outputFilename={outputFilename}
                onOutputFilenameChange={handleOutputFilenameChange}
                fps={fps}
                onFpsChange={handleFpsChange}
                textRenderMode={textRenderMode}
                onTextRenderModeChange={handleTextRenderModeChange}
                textRenderModeDisabled={!plan || savePlan.isPending}
                renderProfile={renderProfile as Record<string, unknown> | null}
              />

              <WorkspacePanel
                title="Readiness"
                eyebrow="Render gate"
                copy="Rendering should feel transactional: you know exactly what is ready, what is missing, and whether the current project is safe to kick off."
              >
                <ul className="list-none p-0 m-0 flex flex-col gap-[var(--space-2)]">
                  <li className="flex items-center gap-[var(--space-2)]">
                    <span
                      className={clsx(
                        'inline-block rounded-full',
                        scenes.length > 0 ? 'bg-[var(--signal-success)]' : 'bg-[var(--text-tertiary)]',
                      )}
                      style={{ width: 6, height: 6 }}
                    />
                    <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      {scenes.length} scene{scenes.length !== 1 ? 's' : ''}
                    </span>
                  </li>
                  <li className="flex items-center gap-[var(--space-2)]">
                    <span
                      className={clsx(
                        'inline-block rounded-full',
                        scenesWithVisual.length === scenes.length && scenes.length > 0
                          ? 'bg-[var(--signal-success)]'
                          : 'bg-[var(--text-tertiary)]',
                      )}
                      style={{ width: 6, height: 6 }}
                    />
                    <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      {scenesWithVisual.length}/{scenes.length} with visuals
                    </span>
                  </li>
                  <li className="flex items-center gap-[var(--space-2)]">
                    <span
                      className={clsx(
                        'inline-block rounded-full',
                        renderBackend === 'remotion' ? 'bg-[var(--accent-primary)]' : 'bg-[var(--text-tertiary)]',
                      )}
                      style={{ width: 6, height: 6 }}
                    />
                    <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      Backend: {renderBackend}
                    </span>
                  </li>
                  <li className="flex items-center gap-[var(--space-2)]">
                    <span
                      className={clsx(
                        'inline-block rounded-full',
                        scenesWithAudio.length === scenes.length && scenes.length > 0
                          ? 'bg-[var(--signal-success)]'
                          : 'bg-[var(--text-tertiary)]',
                      )}
                      style={{ width: 6, height: 6 }}
                    />
                    <span className="text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      {scenesWithAudio.length}/{scenes.length} with audio
                    </span>
                  </li>
                </ul>
              </WorkspacePanel>
            </div>
          )}
        />
      </WorkspaceCanvas>
    </div>
  )
}
