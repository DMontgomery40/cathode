import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { DetailGrid } from '../../components/composed/DetailGrid.tsx'
import { Select } from '../../components/primitives/Select.tsx'
import { Slider } from '../../components/primitives/Slider.tsx'
import { TextInput } from '../../components/primitives/TextInput.tsx'
import { entryDisplayPrice, findCostEntry, type CostCatalog } from '../../lib/costs.ts'

interface ImageProfilePanelProps {
  profile: Record<string, unknown> | null
  imageProviders: string[]
  editModels: string[]
  costCatalog?: CostCatalog | null
  saving?: boolean
  disabled?: boolean
  onProfileChange: (patch: Record<string, unknown>) => void
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function asNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function asBool(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback
}

function defaultGenerationModelFor(provider: string): string {
  switch (provider) {
    case 'codex':
      return 'gpt-image-2'
    case 'replicate':
      return 'qwen/qwen-image-2512'
    default:
      return ''
  }
}

function providerLabel(provider: string): string {
  switch (provider) {
    case 'codex':
      return 'GPT Image'
    case 'replicate':
      return 'Replicate'
    case 'manual':
      return 'Manual'
    case 'local':
      return 'Local'
    default:
      return provider || 'Unknown'
  }
}

function providerHint(provider: string, generationModel: string): string {
  switch (provider) {
    case 'codex':
      return generationModel
        ? `Image generation uses the configured GPT Image route with ${generationModel}.`
        : 'Image generation uses the configured GPT Image route.'
    case 'replicate':
      return 'Cloud image generation stays available as a fallback. Generate and Regenerate Image will use the model shown here only when you keep Replicate selected.'
    case 'local':
      return generationModel
        ? `Local image generation will use ${generationModel} on this machine.`
        : 'Local image generation will use the configured on-device model.'
    case 'manual':
      return 'Manual image generation skips AI image generation. The scene workspace remains upload-first.'
    default:
      return 'The selected provider determines what the scene generation actions will actually call.'
  }
}

function editorBackendLabel(model: string): string {
  if (!model) return 'None configured'
  if (model.startsWith('gpt-image')) return 'GPT Image'
  if (model.startsWith('qwen/')) return 'Replicate-backed'
  if (model.startsWith('qwen-image-edit')) return 'DashScope-backed'
  return 'Custom'
}

function editorLabel(model: string): string {
  if (model === 'gpt-image-2') return 'GPT Image 2'
  if (model === 'qwen/qwen-image-edit-2511') return 'Qwen Image Edit 2511 (Replicate)'
  if (model === 'qwen-image-edit-plus') return 'Qwen Image Edit Plus (DashScope)'
  if (model === 'qwen-image-edit') return 'Qwen Image Edit (DashScope)'
  return model || 'No editor'
}

function editorCostProvider(model: string): string {
  if (model.startsWith('gpt-image')) return 'openai'
  if (model.startsWith('qwen-image-edit')) return 'dashscope'
  return 'replicate'
}

export function ImageProfilePanel({
  profile,
  imageProviders,
  editModels,
  costCatalog,
  saving,
  disabled,
  onProfileChange,
}: ImageProfilePanelProps) {
  const currentProfile = profile ?? {}
  const savedProvider = asString(currentProfile.provider, imageProviders[0] ?? 'manual')
  const provider = imageProviders.includes(savedProvider) ? savedProvider : imageProviders[0] ?? 'manual'
  const unavailableSavedProvider = savedProvider && savedProvider !== provider ? savedProvider : ''
  const generationModel = asString(currentProfile.generation_model, 'gpt-image-2')
  const editModel = asString(currentProfile.edit_model, editModels[0] ?? '')
  const dashscopeN = asNumber(currentProfile.dashscope_edit_n, 1)
  const dashscopeSeed = asString(currentProfile.dashscope_edit_seed)
  const dashscopeNegativePrompt = asString(currentProfile.dashscope_edit_negative_prompt)
  const dashscopePromptExtend = asBool(currentProfile.dashscope_edit_prompt_extend, true)
  const isDashscopeModel = editModel.startsWith('qwen-image-edit')
  const generationCost = entryDisplayPrice(findCostEntry(costCatalog ?? null, {
    kind: 'image_generation',
    provider,
    model: generationModel,
  }))
  const editModelOptions = editModels.map((item) => {
    const entry = findCostEntry(costCatalog ?? null, {
      kind: 'image_edit',
      provider: editorCostProvider(item),
      model: item,
    })
    const price = entryDisplayPrice(entry)
    return {
      value: item,
      label: price ? `${editorLabel(item)} · ~${price} est.` : editorLabel(item),
    }
  })
  return (
    <GlassPanel variant="default" padding="lg" rounded="lg">
      <div className="workspace-panel-head">
        <div className="min-w-0">
          <p className="workspace-eyebrow">Image defaults</p>
          <h3 className="workspace-panel-title">Image profile</h3>
          <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">
            Project-level defaults for image generation and image editing.
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
        <div className="workspace-kpi-grid">
          <div>
            <p className="workspace-eyebrow">Generator</p>
            <div className="workspace-panel-title text-[var(--text-xl)]">{providerLabel(provider)}</div>
          </div>
          <div>
            <p className="workspace-eyebrow">Image editor route</p>
            <div className="workspace-panel-title text-[var(--text-xl)]">{editorBackendLabel(editModel)}</div>
          </div>
          <div>
            <p className="workspace-eyebrow">Edit variants</p>
            <div className="workspace-panel-title text-[var(--text-xl)]">{isDashscopeModel ? dashscopeN : 'Model default'}</div>
          </div>
        </div>
        {unavailableSavedProvider && (
          <p className="m-0 rounded-[var(--radius-md)] border border-[var(--signal-warning)]/40 bg-[var(--signal-warning)]/10 p-[var(--space-3)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-sm)' }}>
            Saved image provider {providerLabel(unavailableSavedProvider)} is not configured on this machine. Current actions will use {providerLabel(provider)} until credentials are added or a new provider is saved.
          </p>
        )}

        <div className="grid gap-[var(--space-4)] xl:grid-cols-2">
          <GlassPanel variant="inset" padding="sm" rounded="lg">
            <div className="flex flex-col gap-[var(--space-3)]">
              <div>
                <p className="workspace-eyebrow">Generate defaults</p>
                <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">
                  {providerHint(provider, generationModel)}
                </p>
              </div>
              <Select
                label="Image Provider"
                value={provider}
                onChange={(event) => {
                  const nextProvider = event.target.value
                  // Switching providers must also switch the model — leaving
                  // the previous provider's model produces an incoherent
                  // profile (e.g. the GPT Image route with a Replicate slug).
                  onProfileChange({
                    provider: nextProvider,
                    generation_model: defaultGenerationModelFor(nextProvider),
                  })
                }}
                options={imageProviders.map((item) => ({ value: item, label: providerLabel(item) }))}
                disabled={disabled}
              />
              <TextInput
                label="Generation Model"
                value={generationModel}
                onChange={(event) => onProfileChange({ generation_model: event.target.value })}
                disabled={disabled}
                hint={provider === 'codex'
                  ? 'Used by image generation. GPT Image pricing varies by requested size and quality.'
                  : generationCost
                    ? `Used by Generate and Regenerate Image. Est. list rate: ~${generationCost} est.`
                    : 'Used by Generate and Regenerate Image.'}
              />
            </div>
          </GlassPanel>

          <GlassPanel variant="inset" padding="sm" rounded="lg">
            <div className="flex flex-col gap-[var(--space-3)]">
              <div>
                <p className="workspace-eyebrow">Edit defaults</p>
                <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">
                  Choose the route that the per-scene Edit Image action will call.
                </p>
              </div>
              <Select
                label="Image editor"
                value={editModel}
                onChange={(event) => onProfileChange({ edit_model: event.target.value })}
                options={editModelOptions}
                disabled={disabled || editModels.length === 0}
                hint={editModels.length === 0 ? 'No AI image editor is configured for this machine.' : 'Used by the per-scene Edit Image action.'}
              />
              {editModel && (
                <p className="m-0 text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  Selected route: {editorBackendLabel(editModel)}.
                </p>
              )}

              {isDashscopeModel && (
                <>
                  <Slider
                    label="DashScope Variants"
                    min={1}
                    max={6}
                    step={1}
                    value={dashscopeN}
                    onChange={(event) => onProfileChange({ dashscope_edit_n: Number(event.currentTarget.value) })}
                    displayValue={`${dashscopeN}`}
                    disabled={disabled}
                  />
                  <TextInput
                    label="DashScope Seed"
                    value={dashscopeSeed}
                    onChange={(event) => onProfileChange({ dashscope_edit_seed: event.target.value })}
                    disabled={disabled}
                    hint="Leave blank for random."
                  />
                  <TextInput
                    label="Negative Guidance"
                    value={dashscopeNegativePrompt}
                    onChange={(event) => onProfileChange({ dashscope_edit_negative_prompt: event.target.value })}
                    disabled={disabled}
                  />
                  <label className="flex items-center gap-[var(--space-2)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-sm)' }}>
                    <input
                      type="checkbox"
                      checked={dashscopePromptExtend}
                      onChange={(event) => onProfileChange({ dashscope_edit_prompt_extend: event.target.checked })}
                      disabled={disabled}
                    />
                    Expand edit direction
                  </label>
                </>
              )}
            </div>
          </GlassPanel>
        </div>

        <div className="grid gap-[var(--space-4)] xl:grid-cols-2">
          <GlassPanel variant="inset" padding="sm" rounded="lg">
            <div className="workspace-eyebrow">Generation path</div>
            <DetailGrid
              className="mt-[var(--space-2)]"
              items={[
                { label: 'Provider', value: providerLabel(provider) },
                { label: 'Model', value: generationModel || 'Model default', title: generationModel },
                { label: 'Route', value: provider === 'codex' ? 'GPT Image' : providerLabel(provider) },
                { label: 'Price', value: generationCost ? `~${generationCost} est.` : 'Catalog default' },
              ]}
            />
          </GlassPanel>
          <GlassPanel variant="inset" padding="sm" rounded="lg">
            <div className="workspace-eyebrow">Edit path</div>
            <DetailGrid
              className="mt-[var(--space-2)]"
              items={[
                { label: 'Provider', value: editorBackendLabel(editModel) },
                { label: 'Model', value: editorLabel(editModel), title: editModel },
                { label: 'Variants', value: isDashscopeModel ? String(dashscopeN) : 'Model default' },
                { label: 'Direction', value: isDashscopeModel && dashscopePromptExtend ? 'Expanded' : 'As written' },
              ]}
            />
          </GlassPanel>
        </div>
      </div>
    </GlassPanel>
  )
}
