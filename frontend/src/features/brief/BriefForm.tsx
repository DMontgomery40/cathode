import { useForm, Controller, type FieldErrors, type Resolver } from 'react-hook-form'
import { BriefSchema, type Brief } from '../../lib/schemas/plan.ts'
import type { ShortFormOption, ShortFormOptions } from '../../lib/api/hooks.ts'
import { TextInput } from '../../components/primitives/TextInput.tsx'
import { TextArea } from '../../components/primitives/TextArea.tsx'
import { Select } from '../../components/primitives/Select.tsx'
import { Slider } from '../../components/primitives/Slider.tsx'
import { Button } from '../../components/primitives/Button.tsx'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'

const SOURCE_MODE_OPTIONS = [
  { value: 'ideas_notes', label: 'Ideas / Notes' },
  { value: 'source_text', label: 'Source Text' },
  { value: 'final_script', label: 'Final Script' },
]

const OUTPUT_MODE_OPTIONS = [
  { value: '', label: 'Standard explainer' },
  { value: 'vertical_short', label: 'Vertical short' },
]

const FALLBACK_SHORT_FORM_TIERS: ShortFormOption[] = [
  { value: 'dev-native-credible', label: 'Dev-native credible', description: 'Proof-first and technically credible.' },
  { value: 'mass-native-technical', label: 'Mass-native technical', description: 'Broader cold-feed energy.' },
]

const FALLBACK_SHORT_FORM_APPROACHES: ShortFormOption[] = [
  { value: 'public-reframe', label: 'Public reframe', description: 'Source as research input, fresh vertical concept.' },
  { value: 'mixed-media-proof', label: 'Mixed-media proof', description: 'Source proof moments plus generated vertical visuals.' },
  { value: 'source-cutdown', label: 'Source cutdown', description: 'Source footage as the primary proof spine.' },
]

const FALLBACK_CAPTION_STRATEGIES: ShortFormOption[] = [
  { value: 'meaning-card-captions', label: 'Meaning-card captions', description: 'Phrase-level cards.' },
  { value: 'word-level-highlight', label: 'Word-level highlight', description: 'Requires final-audio word timings.' },
  { value: 'keyword-labels', label: 'Keyword labels', description: 'Sparse labels.' },
]

const FALLBACK_PLATFORM_TARGETS: ShortFormOption[] = [
  { value: 'tiktok', label: 'TikTok' },
  { value: 'instagram-reels', label: 'Instagram Reels' },
  { value: 'youtube-shorts', label: 'YouTube Shorts' },
]

const DEFAULT_SHORT_RUNTIME_SECONDS = 42
const DEFAULT_SHORT_TONE = 'fast, clear, confident, social-native, and not forced'
const DEFAULT_SHORT_VISUAL_STYLE = '9:16 vertical short-form, tight mobile-safe framing, kinetic captions, fast visual resets, source-loyal visuals'
const DEFAULT_SHORT_VOICE_DIRECTION = 'naturally fast presenter, clear consonants, no chipmunk pitch, no exaggerated influencer cadence'

const VISUAL_STRATEGY_OPTIONS = [
  { value: 'images_only', label: 'Images Only' },
  { value: 'mixed_media', label: 'Mixed Media' },
  { value: 'video_preferred', label: 'Video Preferred' },
]

const VIDEO_SCENE_STYLE_OPTIONS = [
  { value: 'auto', label: 'Auto' },
  { value: 'cinematic', label: 'Cinematic Clips' },
  { value: 'speaking', label: 'Speaking Clips' },
  { value: 'mixed', label: 'Mixed Clip Styles' },
]

const SCENE_ENGINE_OPTIONS = [
  { value: 'auto', label: 'Image-First Auto' },
  { value: 'classic', label: 'Still-Image Focus' },
  { value: 'hybrid', label: 'Mixed Media' },
  { value: 'motion_only', label: 'Motion System' },
]

const TEXT_RENDER_MODE_OPTIONS = [
  { value: 'visual_authored', label: 'Visual-Authored Text' },
  { value: 'deterministic_overlay', label: 'Deterministic Overlay' },
]

// The approved ProGet feed does not serve @hookform/resolvers, so the zod resolver is
// inlined here (functionally equivalent to zodResolver(BriefSchema)) to keep the build
// installable from the feed without an extra dependency.
const briefResolver: Resolver<Brief> = async (values) => {
  const result = BriefSchema.safeParse(values)
  if (result.success) {
    return { values: result.data, errors: {} }
  }

  const errors = {} as FieldErrors<Brief>
  for (const issue of result.error.issues) {
    const path = issue.path.join('.')
    if (!path) continue
    ;(errors as Record<string, { type: string; message: string }>)[path] = {
      type: issue.code,
      message: issue.message,
    }
  }
  return { values: {}, errors }
}

interface BriefFormProps {
  defaults?: Partial<Brief>
  onSubmit: (data: Brief, action: 'video' | 'storyboard') => void
  loading?: boolean
  isNew?: boolean
  loadingAction?: 'video' | 'storyboard' | null
  remotionAvailable?: boolean | null
  paidMediaGenerationAvailable?: boolean
  shortFormOptions?: ShortFormOptions
}

function shortSelectOptions(options: ShortFormOption[] | undefined, fallback: ShortFormOption[]) {
  return (options?.length ? options : fallback).map((option) => ({
    value: option.value,
    label: option.label,
  }))
}

function optionDescription(options: ShortFormOption[] | undefined, fallback: ShortFormOption[], value: string | undefined) {
  const source = options?.length ? options : fallback
  return source.find((option) => option.value === value)?.description ?? ''
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

export function BriefForm({
  defaults,
  onSubmit,
  loading,
  isNew,
  loadingAction,
  remotionAvailable = null,
  paidMediaGenerationAvailable = false,
  shortFormOptions,
}: BriefFormProps) {
  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors },
  } = useForm<Brief>({
    resolver: briefResolver,
    defaultValues: {
      project_name: '',
      source_mode: 'ideas_notes',
      video_goal: '',
      audience: '',
      source_material: '',
      target_length_minutes: 2,
      tone: '',
      visual_style: '',
      must_include: '',
      must_avoid: '',
      ending_cta: '',
      paid_media_budget_usd: '',
      composition_mode: 'auto',
      visual_source_strategy: 'images_only',
      video_scene_style: 'auto',
      text_render_mode: 'visual_authored',
      short_form_format: '',
      short_form_tier: '',
      short_form_approach: '',
      short_form_duration_seconds: 0,
      platform_targets: [],
      hook_promise: '',
      payoff: '',
      source_anchor_card: '',
      source_context_lock: '',
      caption_strategy: '',
      caption_timing_source: '',
      caption_renderer: '',
      voice_direction: '',
      motion_intensity: '',
      ...defaults,
    },
  })

  const targetLength = watch('target_length_minutes')
  const visualSourceStrategy = watch('visual_source_strategy')
  const shortFormFormat = watch('short_form_format')
  const shortFormTier = watch('short_form_tier')
  const shortFormApproach = watch('short_form_approach')
  const captionStrategy = watch('caption_strategy')
  const shortRuntime = Number(watch('short_form_duration_seconds') || 42)
  const shortFormEnabled = shortFormFormat === 'vertical_short'
  const budgetAppliesToVideo = visualSourceStrategy === 'mixed_media' || visualSourceStrategy === 'video_preferred'
  const showPaidMediaBudget = paidMediaGenerationAvailable
  const shortTierOptions = shortSelectOptions(shortFormOptions?.tiers, FALLBACK_SHORT_FORM_TIERS)
  const shortApproachOptions = shortSelectOptions(shortFormOptions?.approaches, FALLBACK_SHORT_FORM_APPROACHES)
  const captionOptions = shortSelectOptions(shortFormOptions?.caption_strategies, FALLBACK_CAPTION_STRATEGIES)
  const platformOptions = shortFormOptions?.platform_targets?.length ? shortFormOptions.platform_targets : FALLBACK_PLATFORM_TARGETS
  const tierHint = optionDescription(shortFormOptions?.tiers, FALLBACK_SHORT_FORM_TIERS, shortFormTier)
  const approachHint = optionDescription(shortFormOptions?.approaches, FALLBACK_SHORT_FORM_APPROACHES, shortFormApproach)
  const captionHint = optionDescription(shortFormOptions?.caption_strategies, FALLBACK_CAPTION_STRATEGIES, captionStrategy)

  const submitVideo = handleSubmit((data) => onSubmit(data, 'video'))
  const submitStoryboard = handleSubmit((data) => onSubmit(data, 'storyboard'))
  const sceneEngineOptions = remotionAvailable === false
    ? SCENE_ENGINE_OPTIONS.map((option) => (
      option.value === 'hybrid' || option.value === 'motion_only'
        ? { ...option, label: `${option.label} (requires Remotion)`, disabled: true }
        : option
    ))
    : SCENE_ENGINE_OPTIONS

  function applyShortFormMode(enabled: boolean) {
    setValue('short_form_format', enabled ? 'vertical_short' : '', { shouldDirty: true })
    if (!enabled) {
      setValue('source_mode', defaults?.source_mode ?? 'ideas_notes', { shouldDirty: true })
      setValue('target_length_minutes', Number(defaults?.short_form_format ? 2 : defaults?.target_length_minutes ?? 2), { shouldDirty: true })
      setValue('short_form_tier', '', { shouldDirty: true })
      setValue('short_form_approach', '', { shouldDirty: true })
      setValue('short_form_duration_seconds', 0, { shouldDirty: true })
      setValue('platform_targets', [], { shouldDirty: true })
      setValue('hook_promise', '', { shouldDirty: true })
      setValue('payoff', '', { shouldDirty: true })
      setValue('source_anchor_card', '', { shouldDirty: true })
      setValue('source_context_lock', '', { shouldDirty: true })
      setValue('caption_strategy', '', { shouldDirty: true })
      setValue('caption_timing_source', '', { shouldDirty: true })
      setValue('caption_renderer', '', { shouldDirty: true })
      setValue('voice_direction', '', { shouldDirty: true })
      setValue('motion_intensity', '', { shouldDirty: true })
      setValue('visual_source_strategy', 'images_only', { shouldDirty: true })
      setValue('video_scene_style', 'auto', { shouldDirty: true })
      setValue('composition_mode', 'auto', { shouldDirty: true })
      setValue('text_render_mode', 'visual_authored', { shouldDirty: true })
      if (watch('tone') === DEFAULT_SHORT_TONE) {
        setValue('tone', '', { shouldDirty: true })
      }
      if (watch('visual_style') === DEFAULT_SHORT_VISUAL_STYLE) {
        setValue('visual_style', '', { shouldDirty: true })
      }
      return
    }

    const shortDefaults = shortFormOptions?.defaults
    const runtimeSeconds = Number(shortDefaults?.runtime_seconds || DEFAULT_SHORT_RUNTIME_SECONDS)
    setValue('source_mode', 'source_text', { shouldDirty: true })
    setValue('target_length_minutes', Number((runtimeSeconds / 60).toFixed(3)), { shouldDirty: true })
    setValue('short_form_duration_seconds', runtimeSeconds, { shouldDirty: true })
    setValue('short_form_tier', shortDefaults?.short_form_tier || 'dev-native-credible', { shouldDirty: true })
    setValue('short_form_approach', shortDefaults?.approach || 'public-reframe', { shouldDirty: true })
    setValue('caption_strategy', shortDefaults?.caption_strategy || 'meaning-card-captions', { shouldDirty: true })
    setValue('platform_targets', shortDefaults?.platform_targets?.length ? shortDefaults.platform_targets : ['tiktok', 'instagram-reels', 'youtube-shorts'], { shouldDirty: true })
    setValue('visual_source_strategy', 'images_only', { shouldDirty: true })
    setValue('video_scene_style', 'auto', { shouldDirty: true })
    setValue('composition_mode', 'classic', { shouldDirty: true })
    setValue('text_render_mode', 'visual_authored', { shouldDirty: true })
    setValue('tone', watch('tone') || DEFAULT_SHORT_TONE, { shouldDirty: true })
    setValue('visual_style', watch('visual_style') || DEFAULT_SHORT_VISUAL_STYLE, { shouldDirty: true })
    setValue('voice_direction', watch('voice_direction') || DEFAULT_SHORT_VOICE_DIRECTION, { shouldDirty: true })
  }

  function syncShortApproach(approach: string) {
    setValue('short_form_approach', approach, { shouldDirty: true })
    if (approach === 'mixed-media-proof' || approach === 'source-cutdown') {
      setValue('visual_source_strategy', 'mixed_media', { shouldDirty: true })
      setValue('video_scene_style', 'mixed', { shouldDirty: true })
      return
    }
    if (approach === 'public-reframe') {
      setValue('visual_source_strategy', 'images_only', { shouldDirty: true })
      setValue('video_scene_style', 'auto', { shouldDirty: true })
    }
  }

  function syncShortRuntime(seconds: number) {
    setValue('short_form_duration_seconds', seconds, { shouldDirty: true })
    setValue('target_length_minutes', Number((seconds / 60).toFixed(3)), { shouldDirty: true })
  }

  return (
    <form onSubmit={(event) => {
      event.preventDefault()
      void submitVideo()
    }} noValidate>
      <div className="flex flex-col gap-[var(--space-6)]">
        {/* Project Basics */}
        <GlassPanel variant="inset" padding="lg" rounded="lg">
          <fieldset className="border-none p-0 m-0">
            <legend
              className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0 p-0"
              style={{
                fontSize: 'var(--text-lg)',
                fontWeight: 'var(--weight-semibold)',
                marginBottom: 'var(--space-4)',
              }}
            >
              Project Basics
            </legend>
            <div className="flex flex-col gap-[var(--space-4)]">
              <TextInput
                label="Project Name"
                placeholder="e.g. Product Launch Explainer"
                error={errors.project_name?.message}
                {...register('project_name')}
              />
              <Select
                label="Source Mode"
                options={SOURCE_MODE_OPTIONS}
                error={errors.source_mode?.message}
                {...register('source_mode')}
              />
              <Controller
                control={control}
                name="short_form_format"
                render={({ field }) => (
                  <Select
                    label="Output Mode"
                    value={field.value ?? ''}
                    options={OUTPUT_MODE_OPTIONS}
                    hint={shortFormEnabled
                      ? 'Vertical Short keeps Brief Studio canonical while selecting the short-form director capability and 9:16 render profile.'
                      : 'Standard Explainer uses the normal broad-video brief contract.'}
                    onChange={(event) => applyShortFormMode(event.currentTarget.value === 'vertical_short')}
                  />
                )}
              />
            </div>
          </fieldset>
        </GlassPanel>

        {/* Content */}
        <GlassPanel variant="inset" padding="lg" rounded="lg">
          <fieldset className="border-none p-0 m-0">
            <legend
              className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0 p-0"
              style={{
                fontSize: 'var(--text-lg)',
                fontWeight: 'var(--weight-semibold)',
                marginBottom: 'var(--space-4)',
              }}
            >
              Content
            </legend>
            <div className="flex flex-col gap-[var(--space-4)]">
              <TextArea
                label="Source Material"
                rows={8}
                placeholder="Paste your notes, script, or source text here..."
                error={errors.source_material?.message}
                {...register('source_material')}
              />
              <TextInput
                label="Video Goal"
                placeholder="What should the viewer learn or do?"
                error={errors.video_goal?.message}
                {...register('video_goal')}
              />
              <TextInput
                label="Audience"
                placeholder="Who is this video for?"
                error={errors.audience?.message}
                {...register('audience')}
              />
              {!shortFormEnabled ? (
                <Controller
                  control={control}
                  name="target_length_minutes"
                  render={({ field }) => (
                    <Slider
                      label="Target Length"
                      min={0.5}
                      max={10}
                      step={0.5}
                      displayValue={`${targetLength} min`}
                      value={field.value}
                      onChange={(e) => field.onChange(parseFloat(e.currentTarget.value))}
                    />
                  )}
                />
              ) : (
                <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] p-[var(--space-3)]">
                  <p className="workspace-eyebrow">Target Length</p>
                  <p className="workspace-panel-copy m-0">
                    Controlled by Short Runtime below so the brief and render plan stay in the 30-50 second vertical-short range.
                  </p>
                </div>
              )}
            </div>
          </fieldset>
        </GlassPanel>

        {shortFormEnabled && (
          <GlassPanel variant="inset" padding="lg" rounded="lg">
            <fieldset className="border-none p-0 m-0">
              <legend
                className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0 p-0"
                style={{
                  fontSize: 'var(--text-lg)',
                  fontWeight: 'var(--weight-semibold)',
                  marginBottom: 'var(--space-4)',
                }}
              >
                Short-Form Mode
              </legend>
              <div className="flex flex-col gap-[var(--space-4)]">
                <div
                  className="rounded-[var(--radius-lg)] border p-[var(--space-4)]"
                  style={{
                    borderColor: 'rgba(91, 138, 130, 0.32)',
                    background: 'linear-gradient(135deg, rgba(91,138,130,0.14), rgba(245,233,219,0.58))',
                  }}
                >
                  <div className="text-[var(--text-primary)]" style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-semibold)' }}>
                    9:16 brief to director to normalized plan
                  </div>
                  <p className="m-0 mt-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    This mode uses the same pipeline as Brief Studio, but adds the vertical-short capability block, source-loyalty fields, caption policy, and 928x1664 render profile.
                  </p>
                </div>
                <div className="grid gap-[var(--space-4)] md:grid-cols-2">
                  <Select
                    label="Short Tier"
                    options={shortTierOptions}
                    hint={tierHint}
                    error={errors.short_form_tier?.message}
                    {...register('short_form_tier')}
                  />
                  <Controller
                    control={control}
                    name="short_form_approach"
                    render={({ field }) => (
                      <Select
                        label="Short Mode"
                        value={field.value ?? ''}
                        options={shortApproachOptions}
                        hint={approachHint}
                        error={errors.short_form_approach?.message}
                        onChange={(event) => syncShortApproach(event.currentTarget.value)}
                      />
                    )}
                  />
                  <Select
                    label="Caption Strategy"
                    options={captionOptions}
                    hint={captionHint}
                    error={errors.caption_strategy?.message}
                    {...register('caption_strategy')}
                  />
                  <Controller
                    control={control}
                    name="short_form_duration_seconds"
                    render={() => (
                      <Slider
                        label="Short Runtime"
                        min={30}
                        max={50}
                        step={1}
                        value={shortRuntime}
                        displayValue={`${shortRuntime}s`}
                        onChange={(event) => syncShortRuntime(Number(event.currentTarget.value))}
                      />
                    )}
                  />
                </div>
                <Controller
                  control={control}
                  name="platform_targets"
                  render={({ field }) => (
                    <div>
                      <p className="workspace-eyebrow">Platforms</p>
                      <div className="mt-[var(--space-2)] flex flex-wrap gap-[var(--space-3)]">
                        {platformOptions.map((platform) => (
                          <label
                            key={platform.value}
                            className="flex items-center gap-[var(--space-2)] text-[var(--text-secondary)]"
                            style={{ fontSize: 'var(--text-sm)' }}
                          >
                            <input
                              type="checkbox"
                              checked={(field.value ?? []).includes(platform.value)}
                              onChange={(event) => field.onChange(updateList(field.value, platform.value, event.target.checked))}
                            />
                            {platform.label}
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                />
                <div className="grid gap-[var(--space-4)] md:grid-cols-2">
                  <TextInput
                    label="Hook Promise"
                    placeholder="The first 1-3 seconds reason to stop scrolling"
                    error={errors.hook_promise?.message}
                    {...register('hook_promise')}
                  />
                  <TextInput
                    label="Payoff"
                    placeholder="What the viewer knows or sees before the CTA"
                    error={errors.payoff?.message}
                    {...register('payoff')}
                  />
                </div>
                <div className="grid gap-[var(--space-4)] md:grid-cols-2">
                  <TextArea
                    label="Source Anchor Card"
                    rows={4}
                    placeholder="Subject, domain, setting, actors, objects, workflow, visual anchors, supported claims, evidence boundary, allowed metaphors, forbidden drift."
                    error={errors.source_anchor_card?.message}
                    {...register('source_anchor_card')}
                  />
                  <TextArea
                    label="Source Context Lock"
                    rows={4}
                    placeholder="The domain, objects, claims, and workflow generated visuals must preserve."
                    error={errors.source_context_lock?.message}
                    {...register('source_context_lock')}
                  />
                </div>
              </div>
            </fieldset>
          </GlassPanel>
        )}

        {/* Style */}
        <GlassPanel variant="inset" padding="lg" rounded="lg">
          <fieldset className="border-none p-0 m-0">
            <legend
              className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0 p-0"
              style={{
                fontSize: 'var(--text-lg)',
                fontWeight: 'var(--weight-semibold)',
                marginBottom: 'var(--space-4)',
              }}
            >
              Style
            </legend>
            <div className="flex flex-col gap-[var(--space-4)]">
              <div
                className="rounded-[var(--radius-lg)] border p-[var(--space-4)]"
                style={{
                  borderColor: 'rgba(214, 118, 88, 0.26)',
                  background: 'linear-gradient(135deg, rgba(255,245,232,0.92), rgba(245,229,214,0.56))',
                }}
              >
                <p
                  className="m-0 uppercase tracking-[0.22em] text-[var(--text-tertiary)]"
                  style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}
                >
                  Default lane
                </p>
                <div
                  className="mt-[var(--space-2)] text-[var(--text-primary)]"
                  style={{ fontSize: 'clamp(1.4rem, 3vw, 2.2rem)', lineHeight: 0.92, fontWeight: 700, letterSpacing: '-0.04em' }}
                >
                  Author the stills first.
                </div>
                <p className="m-0 mt-[var(--space-2)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-sm)' }}>
                  betTube Studio now treats GPT Image stills as the primary visual path. Mixed-media and motion should be deliberate choices for scenes that truly need them, not the default posture of the whole storyboard.
                </p>
              </div>
              <TextInput
                label="Tone"
                placeholder="e.g. professional, friendly, dramatic"
                error={errors.tone?.message}
                {...register('tone')}
              />
              <TextInput
                label="Visual Style"
                placeholder="e.g. minimalist, cinematic, illustrated"
                error={errors.visual_style?.message}
                {...register('visual_style')}
              />
              <Select
                label="Visual Source Strategy"
                options={VISUAL_STRATEGY_OPTIONS}
                error={errors.visual_source_strategy?.message}
                {...register('visual_source_strategy')}
              />
              <Select
                label="Generated Video Scene Style"
                options={VIDEO_SCENE_STYLE_OPTIONS}
                hint="When betTube Studio plans generated video scenes, tell it whether to lean cinematic, speaking-to-camera, or a mix."
                error={errors.video_scene_style?.message}
                {...register('video_scene_style')}
              />
              {showPaidMediaBudget && (
                <div className="rounded-[var(--radius-lg)] border border-[var(--border-accent)] bg-[linear-gradient(135deg,rgba(255,196,83,0.14),rgba(255,86,56,0.08))] p-[var(--space-4)]">
                  <div className="text-[var(--text-primary)]" style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-semibold)' }}>
                    Paid media path
                  </div>
                  <p className="m-0 mt-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-xs)' }}>
                    Use this only for image/video generation spend such as GPT Image stills or generated video clips. TTS is intentionally left out here because the spend is usually too small to budget separately.
                  </p>
                  <div className="mt-[var(--space-3)]">
                    <TextInput
                      label="Paid Media Budget (USD)"
                      type="number"
                      min="0"
                      step="1"
                      inputMode="numeric"
                      placeholder={budgetAppliesToVideo ? 'e.g. 60' : 'e.g. 25'}
                      hint={budgetAppliesToVideo
                        ? 'Useful when the chosen media strategy may invoke both still-image and video generation.'
                        : 'Useful when you want betTube Studio to stay disciplined about paid image generation.'}
                      error={errors.paid_media_budget_usd?.message}
                      {...register('paid_media_budget_usd')}
                    />
                  </div>
                </div>
              )}
            </div>
          </fieldset>
        </GlassPanel>

        {/* Constraints */}
        <GlassPanel variant="inset" padding="lg" rounded="lg">
          <fieldset className="border-none p-0 m-0">
            <legend
              className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0 p-0"
              style={{
                fontSize: 'var(--text-lg)',
                fontWeight: 'var(--weight-semibold)',
                marginBottom: 'var(--space-4)',
              }}
            >
              Constraints
            </legend>
            <div className="flex flex-col gap-[var(--space-4)]">
              <TextArea
                label="Must Include"
                rows={3}
                placeholder="Key points, terms, or visuals that must appear"
                error={errors.must_include?.message}
                {...register('must_include')}
              />
              <TextArea
                label="Must Avoid"
                rows={3}
                placeholder="Topics, phrases, or imagery to avoid"
                error={errors.must_avoid?.message}
                {...register('must_avoid')}
              />
              <TextInput
                label="Ending CTA"
                placeholder="e.g. Visit our website, Subscribe for more"
                error={errors.ending_cta?.message}
                {...register('ending_cta')}
              />
            </div>
          </fieldset>
        </GlassPanel>

        <GlassPanel variant="inset" padding="lg" rounded="lg">
          <fieldset className="border-none p-0 m-0">
            <legend
              className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0 p-0"
              style={{
                fontSize: 'var(--text-lg)',
                fontWeight: 'var(--weight-semibold)',
                marginBottom: 'var(--space-4)',
              }}
            >
              Advanced Creative Controls
            </legend>
            <details>
              <summary
                className="cursor-pointer text-[var(--text-secondary)]"
                style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)' }}
              >
                Override scene engine and text strategy
              </summary>
              <div className="mt-[var(--space-4)] grid gap-[var(--space-4)] md:grid-cols-2">
                <Select
                  label="Scene Engine"
                  options={sceneEngineOptions}
                  hint={remotionAvailable === false
                    ? 'Auto and Classic stay available. Hybrid and Motion Only need the local Remotion toolchain.'
                    : 'Auto keeps betTube Studio image-first by default. Mixed Media and Motion System are explicit specialist overrides when you truly want them.'}
                  error={errors.composition_mode?.message}
                  {...register('composition_mode')}
                />
                <Select
                  label="Text Strategy"
                  options={TEXT_RENDER_MODE_OPTIONS}
                  hint="Visual-authored text keeps the director image-first. Deterministic overlay is the advanced path when exact renderer-owned copy matters."
                  error={errors.text_render_mode?.message}
                  {...register('text_render_mode')}
                />
              </div>
            </details>
          </fieldset>
        </GlassPanel>

        <div className="flex flex-wrap gap-[var(--space-3)]">
          <Button type="submit" variant="primary" size="lg" loading={loading && loadingAction === 'video'}>
            F#@K it, we&apos;re doing it live!!
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="lg"
            onClick={() => void submitStoryboard()}
            loading={loading && loadingAction === 'storyboard'}
          >
            {isNew ? 'Storyboard Only' : 'Rebuild Storyboard'}
          </Button>
        </div>
      </div>
    </form>
  )
}
