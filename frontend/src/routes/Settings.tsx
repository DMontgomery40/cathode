import { useEffect, useMemo, useRef, useState } from 'react'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader.tsx'
import { ImageActivityPanel } from '../features/providers/ImageActivityPanel.tsx'
import { ProviderMatrix } from '../features/brief/ProviderMatrix.tsx'
import { ImageProfilePanel } from '../features/providers/ImageProfilePanel.tsx'
import { TtsProfilePanel } from '../features/providers/TtsProfilePanel.tsx'
import { WorkspaceCanvas, WorkspaceGrid, WorkspacePanel } from '../design-system/recipes'
import { Badge } from '../components/primitives/Badge.tsx'
import { Select } from '../components/primitives/Select.tsx'
import { useBootstrap, usePlan, useProjects } from '../lib/api/hooks.ts'
import { useProjectJobs, useSavePlan } from '../lib/api/scene-hooks.ts'
import { readLastProjectId, writeLastProjectId } from '../lib/project-context.ts'
import type { ImageActionHistoryEntry, Plan } from '../lib/schemas/plan.ts'

function mergeTtsProfile(defaults: Record<string, unknown> | undefined, persisted: Record<string, unknown> | undefined) {
  return {
    ...(defaults ?? {}),
    ...(persisted ?? {}),
  }
}

function mergeImageProfile(defaults: Record<string, unknown> | undefined, persisted: Record<string, unknown> | undefined) {
  return {
    ...(defaults ?? {}),
    ...(persisted ?? {}),
  }
}

function imageProviderDisplayName(provider: string): string {
  switch (provider) {
    case 'codex':
      return 'Codex Exec'
    case 'replicate':
      return 'Replicate'
    case 'local':
      return 'Local'
    case 'manual':
      return 'Manual'
    default:
      return provider || 'manual'
  }
}

export function Settings() {
  const { data: bootstrap } = useBootstrap()
  const { data: projects } = useProjects()
  const [selectedProject, setSelectedProject] = useState(() => readLastProjectId())
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!projects || projects.length === 0) {
      if (selectedProject) {
        setSelectedProject('')
        writeLastProjectId(null)
      }
      return
    }

    const projectNames = new Set(projects.map((project) => project.name))
    const rememberedProject = readLastProjectId()
    const desiredProject = rememberedProject && projectNames.has(rememberedProject)
      ? rememberedProject
      : selectedProject && projectNames.has(selectedProject)
        ? selectedProject
        : projects[0].name

    if (selectedProject !== desiredProject) {
      setSelectedProject(desiredProject)
    }
    if (rememberedProject !== desiredProject) {
      writeLastProjectId(desiredProject)
    }
  }, [projects, selectedProject])

  useEffect(() => {
    if (!selectedProject) {
      return
    }
    writeLastProjectId(selectedProject)
  }, [selectedProject])

  const { data: plan } = usePlan(selectedProject)
  const { data: projectJobs } = useProjectJobs(selectedProject, { refetchInterval: 4000 })
  const savePlan = useSavePlan(selectedProject)

  const ttsProfile = useMemo(
    () => mergeTtsProfile(
      bootstrap?.defaults?.tts_profile as Record<string, unknown> | undefined,
      plan?.meta?.tts_profile as Record<string, unknown> | undefined,
    ),
    [bootstrap, plan],
  )
  const imageProfile = useMemo(
    () => mergeImageProfile(
      bootstrap?.defaults?.image_profile as Record<string, unknown> | undefined,
      plan?.meta?.image_profile as Record<string, unknown> | undefined,
    ),
    [bootstrap, plan],
  )
  const imageActionHistory = useMemo(
    () => Array.isArray(plan?.meta?.image_action_history)
      ? (plan?.meta?.image_action_history as ImageActionHistoryEntry[]).filter((entry): entry is ImageActionHistoryEntry => Boolean(entry && typeof entry === 'object'))
      : [],
    [plan],
  )
  const imageJobs = useMemo(
    () => [...(projectJobs ?? [])]
      .filter((job) => job.requested_stage === 'assets' || job.current_stage === 'assets')
      .sort((left, right) => {
        const leftTime = left.created_utc ? new Date(left.created_utc).valueOf() : 0
        const rightTime = right.created_utc ? new Date(right.created_utc).valueOf() : 0
        return rightTime - leftTime
      }),
    [projectJobs],
  )

  const handleTtsProfileChange = (patch: Record<string, unknown>) => {
    if (!plan || !selectedProject) {
      return
    }

    const nextProfile = {
      ...ttsProfile,
      ...patch,
    }
    const nextPlan: Plan = {
      ...plan,
      meta: {
        ...plan.meta,
        tts_profile: nextProfile,
      },
    }

    if (saveTimer.current) clearTimeout(saveTimer.current)
    setSaving(true)
    saveTimer.current = setTimeout(() => {
      savePlan.mutate(nextPlan, {
        onSettled: () => setSaving(false),
      })
    }, 300)
  }

  const handleImageProfileChange = (patch: Record<string, unknown>) => {
    if (!plan || !selectedProject) {
      return
    }

    const nextProfile = {
      ...imageProfile,
      ...patch,
    }
    const nextPlan: Plan = {
      ...plan,
      meta: {
        ...plan.meta,
        image_profile: nextProfile,
      },
    }

    if (saveTimer.current) clearTimeout(saveTimer.current)
    setSaving(true)
    saveTimer.current = setTimeout(() => {
      savePlan.mutate(nextPlan, {
        onSettled: () => setSaving(false),
      })
    }, 300)
  }

  return (
    <div className="flex flex-col h-full">
      <WorkspaceHeader
        title="Settings"
        breadcrumbs={[{ label: 'Home', href: '/' }]}
      />
      <WorkspaceCanvas size="wide">
        <WorkspaceGrid
          main={(
            <div className="workspace-panel-stack">
              <WorkspacePanel
                title="Target project"
                eyebrow="Editing context"
                copy="Choose the project once, then tune image and voice defaults for that exact project without hunting for a hidden selector in a sub-panel."
              >
                <div className="flex flex-col gap-[var(--space-4)]">
                  <Select
                    label="Project"
                    value={selectedProject}
                    onChange={(event) => {
                      const nextProject = event.target.value
                      setSelectedProject(nextProject)
                      writeLastProjectId(nextProject)
                    }}
                    options={(projects ?? []).map((project) => ({ value: project.name, label: project.name }))}
                    disabled={!projects || projects.length === 0}
                    hint={!projects || projects.length === 0 ? 'Create a project first to store per-project settings.' : undefined}
                  />
                  {selectedProject && plan && (
                    <div className="workspace-kpi-grid">
                      <div>
                        <p className="workspace-eyebrow">Scenes</p>
                        <div className="workspace-panel-title text-[var(--text-2xl)]">{plan.scenes.length}</div>
                      </div>
                      <div>
                        <p className="workspace-eyebrow">Image provider</p>
                        <div className="workspace-panel-title text-[var(--text-xl)]">{imageProviderDisplayName(String(imageProfile.provider || 'manual'))}</div>
                      </div>
                      <div>
                        <p className="workspace-eyebrow">Voice provider</p>
                        <div className="workspace-panel-title text-[var(--text-xl)]">{String(ttsProfile.provider || 'kokoro')}</div>
                      </div>
                    </div>
                  )}
                </div>
              </WorkspacePanel>
              <ImageProfilePanel
                profile={imageProfile}
                imageProviders={bootstrap?.providers?.image_providers ?? []}
                editModels={bootstrap?.providers?.image_edit_models ?? []}
                costCatalog={bootstrap?.providers?.cost_catalog ?? null}
                saving={saving || savePlan.isPending}
                disabled={!selectedProject || !plan}
                onProfileChange={handleImageProfileChange}
              />
              {selectedProject && plan && (
                <ImageActivityPanel
                  project={selectedProject}
                  entries={imageActionHistory}
                  jobs={imageJobs}
                />
              )}
              <TtsProfilePanel
                profile={ttsProfile}
                providers={bootstrap?.providers?.tts_providers ?? {}}
                voiceOptions={bootstrap?.providers?.tts_voice_options ?? {}}
                costCatalog={bootstrap?.providers?.cost_catalog ?? null}
                saving={saving || savePlan.isPending}
                disabled={!selectedProject || !plan}
                onProfileChange={handleTtsProfileChange}
              />
              <ProviderMatrix />
              <WorkspacePanel
                title="Provider policy"
                eyebrow="Operating model"
                copy="This should clarify what the current machine can actually do, while making the image-first product stance obvious instead of treating motion and stills like equal defaults."
              >
                <div className="flex flex-wrap gap-[var(--space-2)]">
                  <Badge variant="success">Env-driven</Badge>
                  <Badge variant="active">Local-first</Badge>
                  <Badge variant="active">Stills first</Badge>
                  <Badge variant="default">No fake providers</Badge>
                  <Badge variant="default">Capability-gated UI</Badge>
                </div>
              </WorkspacePanel>
            </div>
          )}
          aside={(
            <div className="workspace-panel-stack">
              <WorkspacePanel
                title="Image-first policy"
                eyebrow="Provider UX"
                copy="Configured capability should influence generation buttons, route affordances, and defaults across the app. Local Codex execution plus GPT Image should be the visible preferred lane for stills when this machine can support it."
              >
                <div className="workspace-kpi-grid">
                  <div>
                    <p className="workspace-eyebrow">Surface</p>
                    <div className="workspace-panel-title text-[var(--text-2xl)]">Practical</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Fallback</p>
                    <div className="workspace-panel-title text-[var(--text-2xl)]">Visible</div>
                  </div>
                </div>
              </WorkspacePanel>
              <WorkspacePanel
                title="What this page should do"
                eyebrow="Scope"
                copy="Clarify the current machine state, show capability buckets, and explain what that means for the rest of the product without drowning the user in raw provider plumbing."
              >
                <div className="flex flex-col gap-[var(--space-2)]">
                  <p className="workspace-panel-copy m-0">If cloud image generation is missing, scene editing still needs a sane local/manual path.</p>
                  <p className="workspace-panel-copy m-0">If only local TTS is available, render and scene actions should stay shippable instead of looking half broken.</p>
                  <p className="workspace-panel-copy m-0">If a provider appears here, it should mean the rest of the app can actually use it.</p>
                </div>
              </WorkspacePanel>
            </div>
          )}
          asideWidth={336}
        />
      </WorkspaceCanvas>
    </div>
  )
}
