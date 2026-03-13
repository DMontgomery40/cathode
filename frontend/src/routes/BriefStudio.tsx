import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader.tsx'
import { ProjectWorkspaceNav } from '../components/composed/ProjectWorkspaceNav.tsx'
import { BriefForm } from '../features/brief/BriefForm.tsx'
import { FootageUpload } from '../features/brief/FootageUpload.tsx'
import { StyleRefUpload } from '../features/brief/StyleRefUpload.tsx'
import { ProviderMatrix } from '../features/brief/ProviderMatrix.tsx'
import { WhyThisNext } from '../features/projects/WhyThisNext.tsx'
import {
  useBootstrap,
  usePlan,
  useCreateProject,
  useRebuildStoryboard,
  useStartMakeVideoJob,
} from '../lib/api/hooks.ts'
import type { Brief } from '../lib/schemas/plan.ts'
import { GlassPanel } from '../components/primitives/GlassPanel.tsx'
import { Select } from '../components/primitives/Select.tsx'
import { TextInput } from '../components/primitives/TextInput.tsx'
import { WorkspaceCanvas, WorkspaceGrid, WorkspacePanel } from '../design-system/recipes'

export function BriefStudio() {
  const { projectId = 'new' } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const isNew = projectId === 'new'

  const { data: bootstrap } = useBootstrap()
  const { data: plan, isLoading: planLoading } = usePlan(projectId)

  const createProject = useCreateProject()
  const rebuildStoryboard = useRebuildStoryboard(projectId)
  const startMakeVideoJob = useStartMakeVideoJob()
  const [loadingAction, setLoadingAction] = useState<'video' | 'storyboard' | null>(null)
  const [demoTarget, setDemoTarget] = useState({
    workspace_path: '',
    app_url: '',
    launch_command: '',
    expected_url: '',
    preferred_agent: 'codex',
    repo_url: '',
    flow_hints: '',
  })

  const loading = createProject.isPending || rebuildStoryboard.isPending || startMakeVideoJob.isPending
  const briefMeta = (plan?.meta?.brief as Record<string, unknown> | undefined) ?? {}
  const agentDemoProfile = (plan?.meta?.agent_demo_profile as Record<string, unknown> | undefined) ?? {}

  // Build defaults from bootstrap + existing plan
  const defaults: Partial<Brief> = {
    ...(bootstrap?.defaults?.brief as Partial<Brief> | undefined),
    ...(plan?.meta?.brief as Partial<Brief> | undefined),
    ...(plan?.meta?.project_name ? { project_name: plan.meta.project_name as string } : {}),
  }

  const styleRefs = briefMeta.style_reference_paths as string[] | undefined
  const styleSummary = briefMeta.style_reference_summary as string | null | undefined
  const footageManifest = briefMeta.footage_manifest as Array<Record<string, unknown>> | undefined
  const footageSummary = briefMeta.available_footage as string | null | undefined

  useEffect(() => {
    setDemoTarget({
      workspace_path: String(agentDemoProfile.workspace_path ?? ''),
      app_url: String(agentDemoProfile.app_url ?? ''),
      launch_command: String(agentDemoProfile.launch_command ?? ''),
      expected_url: String(agentDemoProfile.expected_url ?? ''),
      preferred_agent: String(agentDemoProfile.preferred_agent ?? 'codex') || 'codex',
      repo_url: String(agentDemoProfile.repo_url ?? ''),
      flow_hints: Array.isArray(agentDemoProfile.flow_hints)
        ? agentDemoProfile.flow_hints.map((value) => String(value)).join('\n')
        : String(agentDemoProfile.flow_hints ?? ''),
    })
  }, [agentDemoProfile.app_url, agentDemoProfile.expected_url, agentDemoProfile.flow_hints, agentDemoProfile.launch_command, agentDemoProfile.preferred_agent, agentDemoProfile.repo_url, agentDemoProfile.workspace_path])

  function normalizedDemoTarget() {
    const flowHints = demoTarget.flow_hints
      .split('\n')
      .map((value) => value.trim())
      .filter(Boolean)
    const baseTarget = {
      workspace_path: demoTarget.workspace_path.trim(),
      app_url: demoTarget.app_url.trim(),
      launch_command: demoTarget.launch_command.trim(),
      expected_url: demoTarget.expected_url.trim(),
      repo_url: demoTarget.repo_url.trim(),
    }
    const hasTargetContext = Object.values(baseTarget).some(Boolean) || flowHints.length > 0
    if (!hasTargetContext) {
      return {}
    }

    return Object.fromEntries(
      Object.entries({
        ...baseTarget,
        preferred_agent: demoTarget.preferred_agent.trim(),
        flow_hints: flowHints,
      }).filter(([, value]) => {
        if (Array.isArray(value)) {
          return value.length > 0
        }
        return String(value || '').trim() !== ''
      }),
    )
  }

  const autoHybridPreferred = Boolean((footageManifest?.length ?? 0) > 0 || Object.keys(normalizedDemoTarget()).length > 0)

  function handleSubmit(data: Brief, action: 'video' | 'storyboard') {
    const nextDemoTarget = normalizedDemoTarget()
    setLoadingAction(action)
    if (action === 'video') {
      const { project_name, ...brief } = data
      const nextBrief = {
        ...brief,
        project_name,
      }
      startMakeVideoJob.mutate(
        {
          project_name,
          brief: nextBrief,
          agent_demo_profile: Object.keys(nextDemoTarget).length > 0 ? nextDemoTarget : null,
          run_until: 'render',
        },
        {
          onSuccess: (job) => {
            const name = job.project_name || project_name
            navigate(`/projects/${encodeURIComponent(name)}/render`)
          },
          onSettled: () => setLoadingAction(null),
        },
      )
      return
    }

    if (isNew) {
      const { project_name, ...brief } = data
      createProject.mutate(
        {
          project_name,
          brief,
          agent_demo_profile: Object.keys(nextDemoTarget).length > 0 ? nextDemoTarget : null,
        },
        {
          onSuccess: (result) => {
            const name = (result as Record<string, unknown>).project_name as string ?? project_name
            navigate(`/projects/${encodeURIComponent(name)}/scenes`)
          },
          onSettled: () => setLoadingAction(null),
        },
      )
    } else {
      rebuildStoryboard.mutate(
        {
          brief: {
            ...data,
            project_name: projectId,
          },
          agent_demo_profile: Object.keys(nextDemoTarget).length > 0 ? nextDemoTarget : {},
        },
        {
          onSuccess: () => {
            navigate(`/projects/${encodeURIComponent(projectId)}/scenes`)
          },
          onSettled: () => setLoadingAction(null),
        },
      )
    }
  }

  const breadcrumbs = [
    { label: 'Projects', href: '/projects' },
    { label: isNew ? 'New Project' : projectId },
  ]

  if (!isNew && planLoading) {
    return (
      <div className="flex flex-col h-full">
        <WorkspaceHeader
          title="Brief Studio"
          breadcrumbs={breadcrumbs}
        />
        <div
          className="flex-1 flex items-center justify-center"
          style={{ padding: 'var(--space-8)' }}
        >
          <p className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-sm)' }}>
            Loading project...
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <WorkspaceHeader
        title="Brief Studio"
        subtitle={isNew ? 'New project' : projectId}
        breadcrumbs={breadcrumbs}
        status={loading ? 'generating' : 'idle'}
      />
      {!isNew && <ProjectWorkspaceNav projectId={projectId} />}
      <WorkspaceCanvas>
        <WorkspaceGrid
          asideWidth={312}
          main={(
            <div className="workspace-panel-stack">
              <WorkspacePanel
                title={isNew ? 'Shape the brief' : 'Retune the project brief'}
                eyebrow="Intent-driven setup"
                copy="The brief should stay outcome-first, but the primary path now goes straight to a real background video run instead of pretending storyboard generation is the whole product."
              >
                <BriefForm
                  defaults={defaults}
                  onSubmit={handleSubmit}
                  loading={loading}
                  isNew={isNew}
                  loadingAction={loadingAction}
                  remotionAvailable={Boolean(bootstrap?.providers?.remotion_available)}
                  autoHybridPreferred={autoHybridPreferred}
                />
              </WorkspacePanel>

              <WorkspacePanel
                title="Demo target"
                eyebrow="One-click live path"
                copy="Optional, but this is what lets Cathode pivot from still-image generation into the heavier repo/app demo path. Leave it empty to stay on the classic track."
              >
                <GlassPanel variant="inset" padding="lg" rounded="lg">
                  <div className="flex flex-col gap-[var(--space-4)]">
                    <div className="rounded-[var(--radius-lg)] border border-[var(--border-accent)] bg-[linear-gradient(135deg,rgba(255,86,56,0.16),rgba(255,196,83,0.08))] px-[var(--space-4)] py-[var(--space-3)]">
                      <div className="text-[var(--text-primary)]" style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-semibold)' }}>
                        F#@K it, we&apos;re doing it live!!
                      </div>
                      <p className="m-0 mt-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                        The primary button starts the full background run: storyboard, assets, demo capture path, logs, and final render. This panel tells that job what app or repo it should actually show.
                      </p>
                    </div>

                    <TextInput
                      label="Workspace Path"
                      value={demoTarget.workspace_path}
                      onChange={(event) => setDemoTarget((current) => ({ ...current, workspace_path: event.target.value }))}
                      placeholder="/absolute/path/to/the/repo/or-workspace"
                      hint="If omitted, Cathode will try to use the current local Cathode workspace for tonight's self-demo path."
                    />
                    <TextInput
                      label="App URL"
                      value={demoTarget.app_url}
                      onChange={(event) => setDemoTarget((current) => ({ ...current, app_url: event.target.value }))}
                      placeholder="http://127.0.0.1:9322"
                      hint="Prefill this when the app is already running and you want the agent path to attach instead of guessing."
                    />
                    <TextInput
                      label="Launch Command"
                      value={demoTarget.launch_command}
                      onChange={(event) => setDemoTarget((current) => ({ ...current, launch_command: event.target.value }))}
                      placeholder="./start.sh --react"
                    />
                    <TextInput
                      label="Expected URL"
                      value={demoTarget.expected_url}
                      onChange={(event) => setDemoTarget((current) => ({ ...current, expected_url: event.target.value }))}
                      placeholder="http://127.0.0.1:9322"
                    />
                    <TextInput
                      label="Repo URL"
                      value={demoTarget.repo_url}
                      onChange={(event) => setDemoTarget((current) => ({ ...current, repo_url: event.target.value }))}
                      placeholder="https://github.com/your/repo"
                    />
                    <Select
                      label="Preferred Agent"
                      value={demoTarget.preferred_agent}
                      onChange={(event) => setDemoTarget((current) => ({ ...current, preferred_agent: event.target.value }))}
                      options={[
                        { value: 'codex', label: 'Codex' },
                        { value: 'claude', label: 'Claude' },
                      ]}
                    />
                    <label className="flex flex-col gap-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                      <span>Flow Hints</span>
                      <textarea
                        value={demoTarget.flow_hints}
                        onChange={(event) => setDemoTarget((current) => ({ ...current, flow_hints: event.target.value }))}
                        rows={4}
                        placeholder={'Open GitHub to the system prompts\nShow the queue/log surface\nReturn to storyboard for manual tweaks'}
                        className="w-full resize-y rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                        aria-label="Flow Hints"
                      />
                    </label>
                  </div>
                </GlassPanel>
              </WorkspacePanel>
            </div>
          )}
          aside={(
            <div className="workspace-panel-stack">
              {!isNew && <WhyThisNext plan={plan} />}
              <WorkspacePanel
                title="Why these panels moved"
                eyebrow="Layout priority"
                copy="The right rail is now for light guidance. Style refs and footage live in the main workspace so the operator can actually inspect and compare them at a useful size."
              >
                <p className="workspace-panel-copy m-0">
                  Keep the rail lightweight: use it for status and nudges, not for the primary creative material.
                </p>
              </WorkspacePanel>
            </div>
          )}
        />

        <div className="workspace-panel-stack">
          <div className="workspace-panel-head">
            <div className="min-w-0">
              <p className="workspace-eyebrow">Creative inputs</p>
              <h2 className="workspace-panel-title">Style references and footage</h2>
              <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">
                These inputs should read like first-class creative material, not like cramped utilities. Give them room to breathe before storyboarding.
              </p>
            </div>
          </div>
          <div className="workspace-dual-panel-grid">
            <StyleRefUpload
              project={projectId}
              styleRefs={styleRefs}
              styleSummary={styleSummary}
            />
            <FootageUpload
              project={projectId}
              footageManifest={footageManifest}
              footageSummary={footageSummary}
            />
          </div>

          <ProviderMatrix />
        </div>
      </WorkspaceCanvas>
    </div>
  )
}
