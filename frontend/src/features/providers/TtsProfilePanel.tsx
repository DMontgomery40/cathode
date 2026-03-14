import { useMemo } from 'react'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { Select } from '../../components/primitives/Select.tsx'
import { Slider } from '../../components/primitives/Slider.tsx'
import { TextInput } from '../../components/primitives/TextInput.tsx'
import { entryDisplayPrice, findCostEntry, type CostCatalog } from '../../lib/costs.ts'

type VoiceOption = { value: string; label: string; description: string }

interface TtsProfilePanelProps {
  profile: Record<string, unknown> | null
  providers: Record<string, string>
  voiceOptions: Record<string, VoiceOption[]>
  costCatalog?: CostCatalog | null
  saving?: boolean
  disabled?: boolean
  onProfileChange: (patch: Record<string, unknown>) => void
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.trim() ? value : fallback
}

function asNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function asBool(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback
}

function providerModelHint(provider: string, currentModelId: unknown): string {
  const value = typeof currentModelId === 'string' ? currentModelId.trim() : ''
  if (provider === 'openai') {
    return value.startsWith('tts-') ? value : 'tts-1'
  }
  if (provider === 'elevenlabs') {
    return value && !value.startsWith('tts-') ? value : 'eleven_multilingual_v2'
  }
  if (provider === 'chatterbox') {
    return 'resemble-ai/chatterbox'
  }
  return ''
}

function providerCostHint(provider: string): string {
  if (provider === 'kokoro') return 'free/local'
  if (provider === 'elevenlabs') return 'paid, model-specific'
  if (provider === 'openai') return 'paid, model-specific'
  if (provider === 'chatterbox') return 'paid, model-specific'
  return ''
}

export function TtsProfilePanel({
  profile,
  providers,
  voiceOptions,
  costCatalog,
  saving,
  disabled,
  onProfileChange,
}: TtsProfilePanelProps) {
  const currentProfile = profile ?? {}
  const providerOptions = useMemo(
    () => Object.entries(providers).map(([value, label]) => {
      const hint = providerCostHint(value)
      return { value, label: hint ? `${label} · ${hint}` : label }
    }),
    [providers],
  )

  const provider = asString(currentProfile.provider, providerOptions[0]?.value ?? 'kokoro')
  const voice = asString(currentProfile.voice)
  const speed = asNumber(currentProfile.speed, 1.1)
  const exaggeration = asNumber(currentProfile.exaggeration, 0.6)
  const stability = asNumber(currentProfile.stability, 0.38)
  const similarityBoost = asNumber(currentProfile.similarity_boost, 0.8)
  const style = asNumber(currentProfile.style, 0.65)
  const useSpeakerBoost = asBool(currentProfile.use_speaker_boost, true)
  const textNormalization = asString(currentProfile.text_normalization, 'auto')

  const providerVoiceOptions = (voiceOptions[provider] ?? []).map((item) => ({
    value: item.value,
    label: item.description ? `${item.label} - ${item.description}` : item.label,
  }))
  const providerModel = providerModelHint(provider, currentProfile.model_id)
  const providerCostEntry = provider === 'kokoro' ? null : findCostEntry(costCatalog ?? null, {
    kind: 'tts',
    provider: provider === 'chatterbox' ? 'replicate' : provider,
    model: providerModel,
  })
  const providerExactCost = entryDisplayPrice(providerCostEntry)

  return (
    <GlassPanel variant="default" padding="lg" rounded="lg">
      <div className="workspace-panel-head">
        <div className="min-w-0">
          <p className="workspace-eyebrow">Streamlit parity</p>
          <h3 className="workspace-panel-title">Voice settings</h3>
          <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">
            Project-level TTS profile for Kokoro, ElevenLabs, Chatterbox, and OpenAI. These controls write back to `meta.tts_profile`.
          </p>
        </div>
        <span
          className="rounded-full border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-secondary)]"
          style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
        >
          {saving ? 'Saving…' : 'Saved'}
        </span>
      </div>

      <div className="flex flex-col gap-[var(--space-4)]">
        <Select
          label="TTS Provider"
          value={provider}
          onChange={(event) => onProfileChange({ provider: event.target.value })}
          options={providerOptions}
          disabled={disabled}
          hint={provider === 'kokoro'
            ? 'Kokoro stays local and free on this machine.'
            : 'Provider pricing depends on the selected model. Exact numbers are shown on the active model path below.'}
        />

        {provider === 'kokoro' && (
          <>
            <Select
              label="Voice"
              value={voice}
              onChange={(event) => onProfileChange({ voice: event.target.value })}
              options={providerVoiceOptions}
              disabled={disabled}
            />
            <Slider
              label="Speed"
              min={0.8}
              max={1.5}
              step={0.1}
              value={speed}
              onChange={(event) => onProfileChange({ speed: Number(event.currentTarget.value) })}
              displayValue={`${speed.toFixed(2)}x`}
              disabled={disabled}
            />
          </>
        )}

        {provider === 'elevenlabs' && (
          <>
            <Select
              label="Voice"
              value={voice}
              onChange={(event) => onProfileChange({ voice: event.target.value })}
              options={providerVoiceOptions}
              disabled={disabled}
            />
            <Slider
              label="Stability"
              min={0}
              max={1}
              step={0.05}
              value={stability}
              onChange={(event) => onProfileChange({ stability: Number(event.currentTarget.value) })}
              displayValue={stability.toFixed(2)}
              disabled={disabled}
            />
            <Slider
              label="Similarity Boost"
              min={0}
              max={1}
              step={0.05}
              value={similarityBoost}
              onChange={(event) => onProfileChange({ similarity_boost: Number(event.currentTarget.value) })}
              displayValue={similarityBoost.toFixed(2)}
              disabled={disabled}
            />
            <Slider
              label="Style"
              min={0}
              max={1}
              step={0.05}
              value={style}
              onChange={(event) => onProfileChange({ style: Number(event.currentTarget.value) })}
              displayValue={style.toFixed(2)}
              disabled={disabled}
            />
            <Slider
              label="Speed"
              min={0.7}
              max={1.4}
              step={0.05}
              value={speed}
              onChange={(event) => onProfileChange({ speed: Number(event.currentTarget.value) })}
              displayValue={`${speed.toFixed(2)}x`}
              disabled={disabled}
            />
            <Select
              label="Text Normalization"
              value={textNormalization}
              onChange={(event) => onProfileChange({ text_normalization: event.target.value })}
              options={[
                { value: 'auto', label: 'Auto' },
                { value: 'on', label: 'On' },
                { value: 'off', label: 'Off' },
              ]}
              disabled={disabled}
            />
            <label className="flex items-center gap-[var(--space-2)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-sm)' }}>
              <input
                type="checkbox"
                checked={useSpeakerBoost}
                onChange={(event) => onProfileChange({ use_speaker_boost: event.target.checked })}
                disabled={disabled}
              />
              Use speaker boost
            </label>
            {providerExactCost && (
              <p className="m-0 text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                Current model rate: {providerExactCost}.
              </p>
            )}
          </>
        )}

        {provider === 'chatterbox' && (
          <>
            <Slider
              label="Exaggeration"
              min={0.25}
              max={2.0}
              step={0.05}
              value={exaggeration}
              onChange={(event) => onProfileChange({ exaggeration: Number(event.currentTarget.value) })}
              displayValue={exaggeration.toFixed(2)}
              disabled={disabled}
            />
            {providerExactCost && (
              <p className="m-0 text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                Current model rate: {providerExactCost}.
              </p>
            )}
          </>
        )}

        {provider === 'openai' && (
          <>
            <Select
              label="Voice"
              value={voice}
              onChange={(event) => onProfileChange({ voice: event.target.value })}
              options={providerVoiceOptions}
              disabled={disabled}
            />
            <TextInput
              label="Model"
              value={asString(currentProfile.model_id, 'tts-1')}
              onChange={(event) => onProfileChange({ model_id: event.target.value })}
              disabled={disabled}
              hint={providerExactCost ? `Optional override if you want a specific OpenAI TTS model. Current model rate: ${providerExactCost}.` : 'Optional override if you want a specific OpenAI TTS model.'}
            />
          </>
        )}
      </div>
    </GlassPanel>
  )
}
