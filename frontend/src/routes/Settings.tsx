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
import type { CostCatalog } from '../lib/costs.ts'

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
      return 'GPT Image'
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
  const [selectedProjectDraft, setSelectedProjectDraft] = useState(() => readLastProjectId())
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [saving, setSaving] = useState(false)
  const selectedProject = useMemo(() => {
    if (!projects || projects.length === 0) {
      return ''
    }
    const projectNames = new Set(projects.map((project) => project.name))
    if (selectedProjectDraft && projectNames.has(selectedProjectDraft)) {
      return selectedProjectDraft
    }
    const rememberedProject = readLastProjectId()
    if (rememberedProject && projectNames.has(rememberedProject)) {
      return rememberedProject
    }
    return projects[0].name
  }, [projects, selectedProjectDraft])

  useEffect(() => {
    if (!selectedProject) {
      return
    }
    writeLastProjectId(selectedProject)
  }, [selectedProject])

  const { data: plan } = usePlan(selectedProject)
  const { data: projectJobs } = useProjectJobs(selectedProject, { refetchInterval: 4000 })
  const savePlan = useSavePlan(selectedProject)
  const costCatalog = (bootstrap?.providers?.cost_catalog ?? null) as CostCatalog | null

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
  const configuredImageProviders = bootstrap?.providers?.image_providers ?? []
  const savedImageProvider = String(imageProfile.provider || configuredImageProviders[0] || 'manual')
  const effectiveImageProvider = configuredImageProviders.includes(savedImageProvider)
    ? savedImageProvider
    : configuredImageProviders[0] || 'manual'
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
                copy="Choose the project, then tune image and voice defaults for that production."
              >
                <div className="flex flex-col gap-[var(--space-4)]">
                  <Select
                    label="Project"
                    value={selectedProject}
                    onChange={(event) => {
                      const nextProject = event.target.value
                      setSelectedProjectDraft(nextProject)
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
                        <div className="workspace-panel-title text-[var(--text-xl)]">{imageProviderDisplayName(effectiveImageProvider)}</div>
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
                imageProviders={configuredImageProviders}
                editModels={bootstrap?.providers?.image_edit_models ?? []}
                costCatalog={costCatalog}
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
                apiKeys={bootstrap?.providers?.api_keys ?? {}}
                voiceOptions={bootstrap?.providers?.tts_voice_options ?? {}}
                costCatalog={costCatalog}
                saving={saving || savePlan.isPending}
                disabled={!selectedProject || !plan}
                onProfileChange={handleTtsProfileChange}
              />
              <ProviderMatrix />
              <WorkspacePanel
                title="Provider availability"
                eyebrow="Credentials"
                copy="Configured services are enabled in the controls above. Missing services stay visible in provider menus with the credential they need."
              >
                <div className="flex flex-wrap gap-[var(--space-2)]">
                  <Badge variant={bootstrap?.providers?.api_keys?.anthropic ? 'success' : 'default'}>Anthropic</Badge>
                  <Badge variant={bootstrap?.providers?.api_keys?.openai ? 'success' : 'default'}>OpenAI</Badge>
                  <Badge variant={bootstrap?.providers?.api_keys?.replicate ? 'success' : 'default'}>Replicate</Badge>
                  <Badge variant={bootstrap?.providers?.api_keys?.elevenlabs ? 'success' : 'default'}>ElevenLabs</Badge>
                </div>
              </WorkspacePanel>
            </div>
          )}
          aside={(
            <div className="workspace-panel-stack">
              <WorkspacePanel
                title="Selected project"
                eyebrow="Context"
                copy="Settings are saved to the selected project and used by scene generation, narration, and render actions."
              >
                <div className="workspace-kpi-grid">
                  <div>
                    <p className="workspace-eyebrow">Scenes</p>
                    <div className="workspace-panel-title text-[var(--text-2xl)]">{plan?.scenes.length ?? 0}</div>
                  </div>
                  <div>
                    <p className="workspace-eyebrow">Image</p>
                    <div className="workspace-panel-title text-[var(--text-2xl)]">{imageProviderDisplayName(effectiveImageProvider)}</div>
                  </div>
                </div>
              </WorkspacePanel>
              <WorkspacePanel
                title="Voice availability"
                eyebrow="Narration"
                copy="Kokoro is available without cloud credentials. Cloud voices appear in the provider list with setup requirements when credentials are missing."
              >
                <div className="flex flex-col gap-[var(--space-2)]">
                  <Badge variant="success">Kokoro available</Badge>
                  <Badge variant={bootstrap?.providers?.api_keys?.elevenlabs || bootstrap?.providers?.api_keys?.replicate ? 'success' : 'default'}>ElevenLabs</Badge>
                  <Badge variant={bootstrap?.providers?.api_keys?.openai ? 'success' : 'default'}>OpenAI voice</Badge>
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
