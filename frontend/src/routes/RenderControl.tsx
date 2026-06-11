import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { clsx } from 'clsx'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader.tsx'
import { ProjectWorkspaceNav } from '../components/composed/ProjectWorkspaceNav.tsx'
import { RenderSettings } from '../features/render/RenderSettings.tsx'
import { RenderProgress } from '../features/render/RenderProgress.tsx'
import { ArtifactShelf } from '../features/render/ArtifactShelf.tsx'
import { CostPanel } from '../features/projects/CostPanel.tsx'
import { usePlan, useRemotionManifest } from '../lib/api/hooks.ts'
import {
  useStartRender,
  useGenerateAssets,
  useProjectJobs,
  useCancelJob,
  useJobLog,
  useSavePlan,
} from '../lib/api/scene-hooks.ts'
import type { Job } from '../lib/api/jobs.ts'
import { WorkspaceCanvas, WorkspaceEmptyState, WorkspaceGrid, WorkspacePanel } from '../design-system/recipes'
import { sceneHasRenderableAudio, sceneHasRenderableVisual } from '../lib/scene-media.ts'
import { useInvalidateProjectOnJobCompletion } from '../lib/api/project-job-sync.ts'
import { resolveRenderOutputFilename } from '../lib/render-output.ts'
import { projectModeFromPlan } from '../lib/project-mode.ts'
import { PlayerSurface } from '../remotion/PlayerSurface.tsx'

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
  const { data: plan, isError: planError, isFetching: planFetching, isLoading: planLoading } = usePlan(projectId)
  const { data: jobs } = useProjectJobs(projectId, { refetchInterval: 2000 })
  const startRender = useStartRender(projectId)
  const genAssets = useGenerateAssets(projectId)
  const cancelJobMut = useCancelJob()
  const savePlan = useSavePlan(projectId)

  const [outputFilenameDraft, setOutputFilenameDraft] = useState<{ projectId: string; value: string } | null>(null)
  const [fpsDraft, setFpsDraft] = useState<{ projectId: string; value: number } | null>(null)
  const [textRenderModeDraft, setTextRenderModeDraft] = useState<{ projectId: string; value: string } | null>(null)

  const allJobs = jobs ?? []
  const hasAnyActiveJob = allJobs.some((job) => job.status === 'queued' || job.status === 'running')

  const scenes = plan?.scenes ?? []
  const renderProfile = plan?.meta?.render_profile ?? null
  const projectMode = projectModeFromPlan(plan)
  const brief = typeof plan?.meta?.brief === 'object' && plan?.meta?.brief
    ? plan.meta.brief as Record<string, unknown>
    : null
  const renderBackend = typeof renderProfile === 'object' && renderProfile
    ? String((renderProfile as Record<string, unknown>).render_backend || 'ffmpeg')
    : 'ffmpeg'
  const remotionExplicitlyEnabled = typeof renderProfile === 'object' && renderProfile
    ? (
        String((renderProfile as Record<string, unknown>).render_strategy || '').trim().toLowerCase() === 'force_remotion'
        || (
          String((renderProfile as Record<string, unknown>).render_backend || '').trim().toLowerCase() === 'remotion'
          && String((renderProfile as Record<string, unknown>).render_backend_reason || '').trim().toLowerCase().includes('explicit')
        )
      )
    : false
  const remotionManifest = useRemotionManifest(projectId, {
    enabled: remotionExplicitlyEnabled && Boolean(projectId),
  })
  const renderBackendReason = typeof renderProfile === 'object' && renderProfile
    ? String((renderProfile as Record<string, unknown>).render_backend_reason || '').trim() || null
    : null
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

  const renderJobs = [...allJobs]
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
  const existingOutputFilename = resolveRenderOutputFilename({
    videoPath: typeof plan?.meta?.video_path === 'string' ? plan.meta.video_path : null,
    projectName: typeof plan?.meta?.project_name === 'string' ? plan.meta.project_name : null,
    projectId,
  })
  const renderFps = projectMode.locksFps
    ? 30
    : resolveRenderFps(
        typeof renderProfile === 'object' && renderProfile
          ? renderProfile as Record<string, unknown>
          : null,
      )
  const outputFilename = outputFilenameDraft?.projectId === projectId
    ? outputFilenameDraft.value
    : existingOutputFilename
  const fps = projectMode.locksFps
    ? 30
    : fpsDraft?.projectId === projectId
      ? fpsDraft.value
      : renderFps
  const textRenderMode = textRenderModeDraft?.projectId === projectId
    ? textRenderModeDraft.value
    : planTextRenderMode

  useInvalidateProjectOnJobCompletion(projectId, jobs, ['assets', 'render'])
  const { data: renderLog } = useJobLog(projectId, (activeRenderJob ?? latestRenderJob)?.job_id ?? null, {
    enabled: Boolean(activeRenderJob ?? latestRenderJob),
    tailLines: 160,
  })

  if (!plan) {
    const loading = planLoading || planFetching
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
          status={planError ? 'error' : hasAnyActiveJob ? 'rendering' : 'idle'}
        />
        <ProjectWorkspaceNav projectId={projectId} plan={plan} jobs={jobs} />
        <WorkspaceCanvas>
          <WorkspaceEmptyState
            title={loading ? 'Loading project render state' : 'Project render state unavailable'}
            copy={loading
              ? 'Waiting for the project plan and render metadata before showing output, settings, or readiness.'
              : 'The project plan is not available yet. Check the queue for active work or retry after the project plan is written.'}
          />
        </WorkspaceCanvas>
      </div>
    )
  }

  const handleOutputFilenameChange = (value: string) => {
    setOutputFilenameDraft({ projectId, value })
  }

  const handleFpsChange = (value: number) => {
    setFpsDraft({ projectId, value })
  }

  const handleTextRenderModeChange = (value: string) => {
    if (!plan || savePlan.isPending) return
    setTextRenderModeDraft({ projectId, value })
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
          setTextRenderModeDraft((current) => current?.projectId === projectId ? null : current)
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
      <ProjectWorkspaceNav projectId={projectId} plan={plan} jobs={jobs} />

      <WorkspaceCanvas>
        <WorkspaceGrid
          asideWidth={340}
          main={(
            <div className="workspace-panel-stack">
              <WorkspacePanel
                title="Render surface"
                eyebrow="Output"
                copy="Review the current output, render settings, and readiness checks."
              >
                <ArtifactShelf
                  videoPath={plan?.meta?.video_path}
                  videoExists={typeof plan?.meta?.video_exists === 'boolean' ? plan.meta.video_exists : undefined}
                  videoVersion={typeof plan?.meta?.video_version === 'number' ? plan.meta.video_version : undefined}
                  project={projectId}
                />
                {remotionManifest.data && (
                  <div style={{ marginTop: 'var(--space-4)' }}>
                    <PlayerSurface manifest={remotionManifest.data} height={420} />
                  </div>
                )}
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
                    onClick={() => startRender.mutate({
                      output_filename: outputFilename,
                      fps: projectMode.locksFps ? undefined : fps,
                    })}
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
                fpsLocked={projectMode.locksFps}
                renderBackend={renderBackend}
                renderBackendReason={renderBackendReason}
                textRenderMode={textRenderMode}
                onTextRenderModeChange={handleTextRenderModeChange}
                textRenderModeDisabled={savePlan.isPending}
                renderProfile={renderProfile as Record<string, unknown> | null}
              />

              <WorkspacePanel
                title="Readiness"
                eyebrow="Render gate"
                copy="Check scenes, audio, and output settings before starting a render."
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
                      Engine: {renderBackend}
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
