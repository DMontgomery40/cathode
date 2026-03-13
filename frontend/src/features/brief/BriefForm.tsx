import { useEffect, useRef } from 'react'
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

const COMPOSITION_MODE_OPTIONS = [
  { value: 'classic', label: 'Classic' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'motion_only', label: 'Motion Only' },
]

interface BriefFormProps {
  defaults?: Partial<Brief>
  onSubmit: (data: Brief, action: 'video' | 'storyboard') => void
  loading?: boolean
  isNew?: boolean
  loadingAction?: 'video' | 'storyboard' | null
  remotionAvailable?: boolean
  autoHybridPreferred?: boolean
}

export function BriefForm({
  defaults,
  onSubmit,
  loading,
  isNew,
  loadingAction,
  remotionAvailable = false,
  autoHybridPreferred = false,
}: BriefFormProps) {
  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
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
      composition_mode: 'classic',
      visual_source_strategy: 'images_only',
      ...defaults,
    },
  })

  const targetLength = watch('target_length_minutes')
  const compositionMode = watch('composition_mode')
  const compositionTouchedRef = useRef(false)

  useEffect(() => {
    if (compositionTouchedRef.current || !remotionAvailable) {
      return
    }
    if (autoHybridPreferred && compositionMode === 'classic') {
      setValue('composition_mode', 'hybrid', { shouldDirty: true })
    }
  }, [autoHybridPreferred, compositionMode, remotionAvailable, setValue])

  const submitVideo = handleSubmit((data) => onSubmit(data, 'video'))
  const submitStoryboard = handleSubmit((data) => onSubmit(data, 'storyboard'))
  const compositionModeOptions = remotionAvailable
    ? COMPOSITION_MODE_OPTIONS
    : COMPOSITION_MODE_OPTIONS.filter((option) => option.value === 'classic')

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
              <Select
                label="Composition Mode"
                options={compositionModeOptions}
                error={errors.composition_mode?.message}
                {...register('composition_mode', {
                  onChange: () => {
                    compositionTouchedRef.current = true
                  },
                })}
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
