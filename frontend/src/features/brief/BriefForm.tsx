import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { BriefSchema, type Brief } from '../../lib/schemas/plan.ts'
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

interface BriefFormProps {
  defaults?: Partial<Brief>
  onSubmit: (data: Brief, action: 'video' | 'storyboard') => void
  loading?: boolean
  isNew?: boolean
  loadingAction?: 'video' | 'storyboard' | null
  remotionAvailable?: boolean | null
  paidMediaGenerationAvailable?: boolean
}

export function BriefForm({
  defaults,
  onSubmit,
  loading,
  isNew,
  loadingAction,
  remotionAvailable = null,
  paidMediaGenerationAvailable = false,
}: BriefFormProps) {
  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<Brief>({
    resolver: zodResolver(BriefSchema),
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
      ...defaults,
    },
  })

  const targetLength = watch('target_length_minutes')
  const visualSourceStrategy = watch('visual_source_strategy')
  const budgetAppliesToVideo = visualSourceStrategy === 'mixed_media' || visualSourceStrategy === 'video_preferred'
  const showPaidMediaBudget = paidMediaGenerationAvailable

  const submitVideo = handleSubmit((data) => onSubmit(data, 'video'))
  const submitStoryboard = handleSubmit((data) => onSubmit(data, 'storyboard'))
  const sceneEngineOptions = remotionAvailable === false
    ? SCENE_ENGINE_OPTIONS.map((option) => (
      option.value === 'hybrid' || option.value === 'motion_only'
        ? { ...option, label: `${option.label} (requires Remotion)`, disabled: true }
        : option
    ))
    : SCENE_ENGINE_OPTIONS

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
            </div>
          </fieldset>
        </GlassPanel>

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
                  Cathode now treats GPT Image stills as the primary visual path. Mixed-media and motion should be deliberate choices for scenes that truly need them, not the default posture of the whole storyboard.
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
                hint="When Cathode plans generated video scenes, tell it whether to lean cinematic, speaking-to-camera, or a mix."
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
                        : 'Useful when you want Cathode to stay disciplined about paid image generation.'}
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
                    : 'Auto keeps Cathode image-first by default. Mixed Media and Motion System are explicit specialist overrides when you truly want them.'}
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
