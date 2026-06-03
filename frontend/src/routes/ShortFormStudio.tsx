import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { WorkspaceHeader } from '../components/composed/WorkspaceHeader'
import { Button } from '../components/primitives/Button'
import { GlassPanel } from '../components/primitives/GlassPanel'
import { Select } from '../components/primitives/Select'
import { Slider } from '../components/primitives/Slider'
import { TextArea } from '../components/primitives/TextArea'
import { TextInput } from '../components/primitives/TextInput'
import { WorkspaceCanvas, WorkspaceGrid, WorkspacePanel } from '../design-system/recipes'
import { getApiErrorMessage } from '../lib/api/errors'
import {
  type ShortFormOption,
  type ShortFormRequest,
  usePreviewShortForm,
  useShortFormOptions,
  useStartShortFormJob,
} from '../lib/api/hooks'

const FALLBACK_TIER_OPTIONS: ShortFormOption[] = [
  {
    value: 'dev-native-credible',
    label: 'Dev-native credible',
    description: 'Proof-first, technically credible, inspectable visuals, and less slang.',
  },
  {
    value: 'mass-native-technical',
    label: 'Mass-native technical',
    description: 'Broader cold-feed energy with simple language and restrained social-native punch.',
  },
]

const FALLBACK_APPROACH_OPTIONS: ShortFormOption[] = [
  {
    value: 'public-reframe',
    label: 'Public reframe',
    description: 'Treat the source as research input and make one cold-audience idea with fresh vertical visuals.',
  },
  {
    value: 'mixed-media-proof',
    label: 'Mixed-media proof',
    description: 'Use source footage as proof moments, surrounded by generated vertical hook/payoff visuals.',
  },
  {
    value: 'source-cutdown',
    label: 'Source cutdown',
    description: 'Use the source footage as the primary proof and isolate one standalone moment.',
  },
]

const FALLBACK_CAPTION_OPTIONS: ShortFormOption[] = [
  {
    value: 'meaning-card-captions',
    label: 'Meaning-card captions',
    description: 'Phrase-level cards that carry the idea without requiring exact word timings.',
  },
  {
    value: 'word-level-highlight',
    label: 'Word-level highlight',
    description: 'Current-word highlighting, only when final-audio word timings are available.',
  },
  {
    value: 'keyword-labels',
    label: 'Keyword labels',
    description: 'Sparse labels that emphasize proof, objects, and turns in the argument.',
  },
]

const FALLBACK_RUN_UNTIL_OPTIONS: ShortFormOption[] = [
  { value: 'storyboard', label: 'Storyboard', description: 'Plan only; safest first pass before spending media calls.' },
  { value: 'assets', label: 'Assets', description: 'Plan plus image/video/audio generation.' },
  { value: 'render', label: 'Render', description: 'Run through final MP4 assembly.' },
]

const FALLBACK_PLATFORM_OPTIONS: ShortFormOption[] = [
  { value: 'tiktok', label: 'TikTok' },
  { value: 'instagram-reels', label: 'Instagram Reels' },
  { value: 'youtube-shorts', label: 'YouTube Shorts' },
]

const DEFAULT_FORM: ShortFormRequest = {
  project_name: 'vertical_short',
  source_material: '',
  source_transcript: '',
  footage_notes: '',
  available_footage: '',
  audience: 'technical viewers scrolling cold',
  hook_promise: '',
  payoff: '',
  ending_cta: 'watch the full breakdown',
  short_form_tier: 'dev-native-credible',
  approach: 'public-reframe',
  caption_strategy: 'meaning-card-captions',
  platform_targets: ['tiktok', 'instagram-reels', 'youtube-shorts'],
  runtime_seconds: 42,
  source_anchor_card: '',
  subject: '',
  domain: '',
  setting: '',
  actors: '',
  primary_objects: '',
  workflow_action: '',
  visual_anchors: '',
  supported_claims: '',
  evidence_boundary: '',
  allowed_metaphors: '',
  forbidden_drift: '',
  source_context_lock: '',
  must_include: '',
  must_avoid: '',
  paid_media_budget_usd: '',
  run_until: 'storyboard',
  overwrite: false,
}

function updateList(values: string[] | undefined, value: string, checked: boolean): string[] {
  const current = new Set(values ?? [])
  if (checked) {
    current.add(value)
  } else {
    current.delete(value)
  }
  return [...current]
}

function selectOptions(options: ShortFormOption[] | undefined, fallback: ShortFormOption[]) {
  return (options?.length ? options : fallback).map((option) => ({
    value: option.value,
    label: option.label,
  }))
}

function selectedOption(options: ShortFormOption[] | undefined, fallback: ShortFormOption[], value: string | undefined) {
  const source = options?.length ? options : fallback
  return source.find((option) => option.value === value) ?? source[0]
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : []
}

export function ShortFormStudio() {
  const navigate = useNavigate()
  const shortFormOptions = useShortFormOptions()
  const preview = usePreviewShortForm()
  const startJob = useStartShortFormJob()
  const [form, setForm] = useState<ShortFormRequest>(DEFAULT_FORM)
  const [formDirty, setFormDirty] = useState(false)
  const [defaultsHydrated, setDefaultsHydrated] = useState(false)

  const options = shortFormOptions.data
  const tierOptions = selectOptions(options?.tiers, FALLBACK_TIER_OPTIONS)
  const approachOptions = selectOptions(options?.approaches, FALLBACK_APPROACH_OPTIONS)
  const captionOptions = selectOptions(options?.caption_strategies, FALLBACK_CAPTION_OPTIONS)
  const runUntilOptions = selectOptions(options?.run_until, FALLBACK_RUN_UNTIL_OPTIONS)
  const platformOptions = options?.platform_targets?.length ? options.platform_targets : FALLBACK_PLATFORM_OPTIONS
  const selectedTier = selectedOption(options?.tiers, FALLBACK_TIER_OPTIONS, form.short_form_tier)
  const selectedApproach = selectedOption(options?.approaches, FALLBACK_APPROACH_OPTIONS, form.approach)
  const selectedCaption = selectedOption(options?.caption_strategies, FALLBACK_CAPTION_OPTIONS, form.caption_strategy)
  const selectedRunUntil = selectedOption(options?.run_until, FALLBACK_RUN_UNTIL_OPTIONS, form.run_until ?? 'storyboard')
  const payloadPreview = preview.data ?? null
  const previewMeta = payloadPreview?.preview ?? null
  const runtimeSeconds = Number(form.runtime_seconds ?? 42)
  const status = startJob.isPending || preview.isPending ? 'generating' : startJob.isError || preview.isError ? 'error' : 'idle'
  const errorMessage = startJob.error
    ? getApiErrorMessage(startJob.error, 'Short-form job failed.')
    : preview.error
      ? getApiErrorMessage(preview.error, 'Short-form preview failed.')
      : null
  const hasSourceInput = Boolean(
    form.source_material?.trim()
      || form.source_transcript?.trim()
      || form.footage_notes?.trim()
      || form.available_footage?.trim()
      || form.source_anchor_card?.trim()
      || form.source_context_lock?.trim()
      || form.subject?.trim()
      || form.domain?.trim()
      || form.setting?.trim()
      || form.actors?.trim()
      || form.primary_objects?.trim()
      || form.workflow_action?.trim()
      || form.visual_anchors?.trim()
      || form.supported_claims?.trim()
      || form.evidence_boundary?.trim()
      || form.allowed_metaphors?.trim()
      || form.forbidden_drift?.trim()
  )
  const canSubmit = form.project_name.trim().length > 0 && hasSourceInput
  const previewSummary = useMemo(() => {
    if (!payloadPreview) return null
    const render = payloadPreview.render_profile as Record<string, unknown> | undefined
    const brief = payloadPreview.brief as Record<string, unknown> | undefined
    return {
      project: String(payloadPreview.project_name ?? form.project_name),
      aspect: String(previewMeta?.frame ?? `${render?.aspect_ratio ?? '9:16'} ${render?.width ?? 928}x${render?.height ?? 1664}`),
      tier: String(brief?.short_form_tier ?? form.short_form_tier),
      approach: String(brief?.short_form_approach ?? form.approach),
      run_until: String(payloadPreview.run_until ?? form.run_until),
    }
  }, [form.approach, form.project_name, form.run_until, form.short_form_tier, payloadPreview, previewMeta])
  const previewPipeline = asStringArray(previewMeta?.pipeline)
  const previewGuardrails = asStringArray(previewMeta?.guardrails)

  useEffect(() => {
    const defaults = options?.defaults
    if (!defaults || defaultsHydrated || formDirty) return
    setForm((current) => ({
      ...current,
      short_form_tier: defaults.short_form_tier || current.short_form_tier,
      approach: defaults.approach || current.approach,
      caption_strategy: defaults.caption_strategy || current.caption_strategy,
      platform_targets: defaults.platform_targets.length > 0
        ? defaults.platform_targets
        : current.platform_targets,
      runtime_seconds: Number.isFinite(defaults.runtime_seconds)
        ? defaults.runtime_seconds
        : current.runtime_seconds,
      run_until: defaults.run_until || current.run_until,
    }))
    setDefaultsHydrated(true)
  }, [defaultsHydrated, formDirty, options?.defaults])

  function patch(patchValue: Partial<ShortFormRequest>) {
    setFormDirty(true)
    setForm((current) => ({ ...current, ...patchValue }))
  }

  function handlePreview() {
    preview.mutate(form)
  }

  function handleStart() {
    startJob.mutate(form, {
      onSuccess: (job) => {
        const projectName = job.project_name || form.project_name
        navigate(`/projects/${encodeURIComponent(projectName)}/queue`)
      },
    })
  }

  return (
    <div className="flex flex-col h-full">
      <WorkspaceHeader
        title="Short Form Studio"
        subtitle="9:16 vertical"
        breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Short Form' }]}
        status={status}
      />

      <WorkspaceCanvas>
        <WorkspaceGrid
          asideWidth={340}
          main={(
            <div className="workspace-panel-stack">
              <WorkspacePanel
                title="Short-form brief"
                eyebrow="Vertical surface"
                copy="Create a hook-first 30-50 second short through the same brief, director, plan, asset, and render pipeline as the rest of betTube Studio."
              >
                <div className="flex flex-col gap-[var(--space-5)]">
                  <GlassPanel variant="inset" padding="lg" rounded="lg">
                    <div className="grid gap-[var(--space-4)] md:grid-cols-2">
                      <TextInput
                        label="Project Name"
                        value={form.project_name}
                        onChange={(event) => patch({ project_name: event.target.value })}
                        placeholder="e.g. agent_demo_short"
                      />
                      <TextInput
                        label="Audience"
                        value={form.audience}
                        onChange={(event) => patch({ audience: event.target.value })}
                        placeholder="e.g. AI developers scrolling cold"
                      />
                    </div>
                    <div className="mt-[var(--space-4)]">
                      <TextArea
                        label="Source Material"
                        value={form.source_material}
                        onChange={(event) => patch({ source_material: event.target.value })}
                        rows={8}
                        placeholder="Paste notes, a transcript excerpt, or the source idea."
                      />
                    </div>
                    <div className="mt-[var(--space-4)] grid gap-[var(--space-4)] md:grid-cols-2">
                      <TextArea
                        label="Transcript Excerpt"
                        value={form.source_transcript}
                        onChange={(event) => patch({ source_transcript: event.target.value })}
                        rows={4}
                        placeholder="Optional: paste the strongest source-video lines."
                      />
                      <TextArea
                        label="Footage Notes"
                        value={form.footage_notes}
                        onChange={(event) => patch({ footage_notes: event.target.value })}
                        rows={4}
                        placeholder="Optional: note proof moments, timestamps, or usable clips."
                      />
                    </div>
                    <div className="mt-[var(--space-4)]">
                      <TextArea
                        label="Available Footage"
                        value={form.available_footage}
                        onChange={(event) => patch({ available_footage: event.target.value })}
                        rows={3}
                        placeholder="Optional: local paths, uploaded clip notes, or footage manifest summary."
                      />
                    </div>
                  </GlassPanel>

                  <GlassPanel variant="inset" padding="lg" rounded="lg">
                    <div className="grid gap-[var(--space-4)] md:grid-cols-2">
                      <TextInput
                        label="Hook Promise"
                        value={form.hook_promise}
                        onChange={(event) => patch({ hook_promise: event.target.value })}
                        placeholder="The thing worth stopping for in the first 3 seconds"
                      />
                      <TextInput
                        label="Payoff"
                        value={form.payoff}
                        onChange={(event) => patch({ payoff: event.target.value })}
                        placeholder="What the viewer sees or understands by the end"
                      />
                      <Select
                        label="Tier"
                        value={form.short_form_tier}
                        onChange={(event) => patch({ short_form_tier: event.target.value })}
                        options={tierOptions}
                      />
                      <Select
                        label="Short Mode"
                        value={form.approach}
                        onChange={(event) => patch({ approach: event.target.value })}
                        options={approachOptions}
                      />
                      <Select
                        label="Caption Strategy"
                        value={form.caption_strategy}
                        onChange={(event) => patch({ caption_strategy: event.target.value })}
                        options={captionOptions}
                      />
                      <TextInput
                        label="CTA"
                        value={form.ending_cta}
                        onChange={(event) => patch({ ending_cta: event.target.value })}
                      />
                    </div>
                    <div className="mt-[var(--space-4)]">
                      <Slider
                        label="Runtime"
                        min={30}
                        max={50}
                        step={1}
                        value={runtimeSeconds}
                        displayValue={`${runtimeSeconds}s`}
                        onChange={(event) => patch({ runtime_seconds: Number(event.currentTarget.value) })}
                      />
                    </div>
                    <div className="mt-[var(--space-4)] flex flex-wrap gap-[var(--space-3)]">
                      {platformOptions.map((platform) => (
                        <label
                          key={platform.value}
                          className="flex items-center gap-[var(--space-2)] text-[var(--text-secondary)]"
                          style={{ fontSize: 'var(--text-sm)' }}
                        >
                          <input
                            type="checkbox"
                            checked={(form.platform_targets ?? []).includes(platform.value)}
                            onChange={(event) => patch({
                              platform_targets: updateList(form.platform_targets, platform.value, event.target.checked),
                            })}
                          />
                          {platform.label}
                        </label>
                      ))}
                    </div>
                  </GlassPanel>

                  <GlassPanel variant="inset" padding="lg" rounded="lg">
                    <div className="grid gap-[var(--space-4)] md:grid-cols-2">
                      <TextInput label="Subject" value={form.subject} onChange={(event) => patch({ subject: event.target.value })} />
                      <TextInput label="Domain" value={form.domain} onChange={(event) => patch({ domain: event.target.value })} />
                      <TextInput label="Setting" value={form.setting} onChange={(event) => patch({ setting: event.target.value })} />
                      <TextInput label="Actors / Users" value={form.actors} onChange={(event) => patch({ actors: event.target.value })} />
                      <TextInput label="Primary Objects" value={form.primary_objects} onChange={(event) => patch({ primary_objects: event.target.value })} />
                      <TextInput label="Workflow / Action" value={form.workflow_action} onChange={(event) => patch({ workflow_action: event.target.value })} />
                    </div>
                    <div className="mt-[var(--space-4)] grid gap-[var(--space-4)] md:grid-cols-2">
                      <TextArea label="Visual Anchors" rows={3} value={form.visual_anchors} onChange={(event) => patch({ visual_anchors: event.target.value })} />
                      <TextArea label="Supported Claims" rows={3} value={form.supported_claims} onChange={(event) => patch({ supported_claims: event.target.value })} />
                      <TextArea label="Evidence Boundary" rows={3} value={form.evidence_boundary} onChange={(event) => patch({ evidence_boundary: event.target.value })} />
                      <TextArea label="Allowed Metaphors" rows={3} value={form.allowed_metaphors} onChange={(event) => patch({ allowed_metaphors: event.target.value })} />
                      <TextArea label="Forbidden Drift" rows={3} value={form.forbidden_drift} onChange={(event) => patch({ forbidden_drift: event.target.value })} />
                      <TextArea label="Source Context Lock" rows={3} value={form.source_context_lock} onChange={(event) => patch({ source_context_lock: event.target.value })} />
                    </div>
                    <div className="mt-[var(--space-4)]">
                      <TextArea
                        label="Source Anchor Card"
                        rows={5}
                        value={form.source_anchor_card}
                        onChange={(event) => patch({ source_anchor_card: event.target.value })}
                        placeholder="Leave blank to build it from the source-loyalty fields above."
                      />
                    </div>
                  </GlassPanel>
                </div>
              </WorkspacePanel>
            </div>
          )}
          aside={(
            <div className="workspace-panel-stack">
              <WorkspacePanel
                title="Mode"
                eyebrow="Short-form strategy"
                copy="The selected mode controls how the director treats source material, footage, captions, and spend depth."
              >
                <div className="flex flex-col gap-[var(--space-3)]">
                  {[
                    { label: 'Tier', option: selectedTier },
                    { label: 'Source mode', option: selectedApproach },
                    { label: 'Captions', option: selectedCaption },
                    { label: 'Run depth', option: selectedRunUntil },
                  ].map(({ label, option }) => (
                    <div key={label} className="border-b border-[var(--border-subtle)] pb-[var(--space-3)] last:border-b-0 last:pb-0">
                      <p className="workspace-eyebrow">{label}</p>
                      <div className="workspace-panel-title text-[var(--text-base)]">{option?.label}</div>
                      {option?.description ? (
                        <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">{option.description}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              </WorkspacePanel>

              <WorkspacePanel
                title="Run controls"
                eyebrow="Job"
                copy="Preview the exact backend payload, then launch the short-form job at storyboard, asset, or render depth."
              >
                <div className="flex flex-col gap-[var(--space-4)]">
                  <Select
                    label="Run Until"
                    value={form.run_until ?? 'storyboard'}
                    onChange={(event) => patch({ run_until: event.target.value })}
                    options={runUntilOptions}
                  />
                  <TextInput
                    label="Paid Media Budget (USD)"
                    value={form.paid_media_budget_usd}
                    onChange={(event) => patch({ paid_media_budget_usd: event.target.value })}
                    type="number"
                    min="0"
                    step="1"
                  />
                  <label className="flex items-center gap-[var(--space-2)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-sm)' }}>
                    <input
                      type="checkbox"
                      checked={Boolean(form.overwrite)}
                      onChange={(event) => patch({ overwrite: event.target.checked })}
                    />
                    Overwrite matching project
                  </label>
                  <div className="flex flex-col gap-[var(--space-2)]">
                    <Button type="button" variant="secondary" onClick={handlePreview} loading={preview.isPending}>
                      Preview Payload
                    </Button>
                    <Button type="button" variant="primary" onClick={handleStart} loading={startJob.isPending} disabled={!canSubmit}>
                      Start Short
                    </Button>
                  </div>
                  {errorMessage && (
                    <p className="m-0 text-[var(--signal-danger)]" style={{ fontSize: 'var(--text-sm)' }}>
                      {errorMessage}
                    </p>
                  )}
                </div>
              </WorkspacePanel>

              <WorkspacePanel
                title="Payload"
                eyebrow="Effective request"
                copy="The preview is the contract the GUI sends to the FastAPI short-form backend."
              >
                {previewSummary ? (
                  <div className="workspace-kpi-grid" style={{ marginBottom: 'var(--space-3)' }}>
                    <div>
                      <p className="workspace-eyebrow">Project</p>
                      <div className="workspace-panel-title text-[var(--text-lg)]">{previewSummary.project}</div>
                    </div>
                    <div>
                      <p className="workspace-eyebrow">Frame</p>
                      <div className="workspace-panel-title text-[var(--text-lg)]">{previewSummary.aspect}</div>
                    </div>
                    <div>
                      <p className="workspace-eyebrow">Tier</p>
                      <div className="workspace-panel-title text-[var(--text-lg)]">{previewSummary.tier}</div>
                    </div>
                    <div>
                      <p className="workspace-eyebrow">Approach</p>
                      <div className="workspace-panel-title text-[var(--text-lg)]">{previewSummary.approach}</div>
                    </div>
                    <div>
                      <p className="workspace-eyebrow">Depth</p>
                      <div className="workspace-panel-title text-[var(--text-lg)]">{previewSummary.run_until}</div>
                    </div>
                  </div>
                ) : null}
                <pre
                  className="m-0 max-h-[30rem] overflow-auto rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-void)] p-[var(--space-3)] text-[var(--text-tertiary)]"
                  style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
                >
                  {payloadPreview ? JSON.stringify(payloadPreview, null, 2) : 'Preview has not been generated yet.'}
                </pre>
                {previewPipeline.length > 0 || previewGuardrails.length > 0 ? (
                  <div className="mt-[var(--space-4)] grid gap-[var(--space-3)]">
                    {previewPipeline.length > 0 ? (
                      <div>
                        <p className="workspace-eyebrow">Pipeline</p>
                        <p className="workspace-panel-copy m-0">{previewPipeline.join(' -> ')}</p>
                      </div>
                    ) : null}
                    {previewGuardrails.length > 0 ? (
                      <div>
                        <p className="workspace-eyebrow">Guardrails</p>
                        <p className="workspace-panel-copy m-0">{previewGuardrails.join(', ')}</p>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </WorkspacePanel>
            </div>
          )}
        />
      </WorkspaceCanvas>
    </div>
  )
}
