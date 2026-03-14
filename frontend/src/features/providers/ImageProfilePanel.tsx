import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
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

function providerLabel(provider: string): string {
  switch (provider) {
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
    case 'replicate':
      return 'Cloud image generation stays enabled. Generate and Regenerate Image will use the generation model shown here.'
    case 'local':
      return generationModel
        ? `Local image generation will use ${generationModel} on this machine.`
        : 'Local image generation will use the configured on-device model.'
    case 'manual':
      return 'Manual mode skips AI image generation. The scene workspace remains upload-first.'
    default:
      return 'The selected provider determines what the scene generation actions will actually call.'
  }
}

function editorBackendLabel(model: string): string {
  if (!model) return 'None configured'
  if (model.startsWith('qwen/')) return 'Replicate-backed'
  if (model.startsWith('qwen-image-edit')) return 'DashScope-backed'
  return 'Custom'
}

function editorLabel(model: string): string {
  if (model === 'qwen/qwen-image-edit-2511') return 'Qwen Image Edit 2511 (Replicate)'
  if (model === 'qwen-image-edit-plus') return 'Qwen Image Edit Plus (DashScope)'
  if (model === 'qwen-image-edit') return 'Qwen Image Edit (DashScope)'
  return model || 'No editor'
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
  const provider = asString(currentProfile.provider, imageProviders[0] ?? 'manual')
  const generationModel = asString(currentProfile.generation_model, 'qwen/qwen-image-2512')
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
      provider: item.startsWith('qwen-image-edit') ? 'dashscope' : 'replicate',
      model: item,
    })
    const price = entryDisplayPrice(entry)
    return {
      value: item,
      label: price ? `${editorLabel(item)} · ${price}` : editorLabel(item),
    }
  })
  const effectiveGenerateRequest = {
    provider,
    model: generationModel || null,
  }
  const effectiveEditRequest = {
    backend: editorBackendLabel(editModel),
    model: editModel || null,
    dashscope_edit_n: isDashscopeModel ? dashscopeN : null,
    dashscope_edit_seed: isDashscopeModel && dashscopeSeed ? dashscopeSeed : null,
    dashscope_edit_negative_prompt: isDashscopeModel && dashscopeNegativePrompt ? dashscopeNegativePrompt : null,
    dashscope_edit_prompt_extend: isDashscopeModel ? dashscopePromptExtend : null,
  }

  return (
    <GlassPanel variant="default" padding="lg" rounded="lg">
      <div className="workspace-panel-head">
        <div className="min-w-0">
          <p className="workspace-eyebrow">Streamlit parity</p>
          <h3 className="workspace-panel-title">Image profile</h3>
          <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">
            Project-level generation and edit defaults. This is where the React app should let you choose the actual image editor before scene edits happen.
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
            <p className="workspace-eyebrow">Editor backend</p>
            <div className="workspace-panel-title text-[var(--text-xl)]">{editorBackendLabel(editModel)}</div>
          </div>
          <div>
            <p className="workspace-eyebrow">Edit variants</p>
            <div className="workspace-panel-title text-[var(--text-xl)]">{isDashscopeModel ? dashscopeN : 'Model default'}</div>
          </div>
        </div>

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
                onChange={(event) => onProfileChange({ provider: event.target.value })}
                options={imageProviders.map((item) => ({ value: item, label: providerLabel(item) }))}
                disabled={disabled}
              />
              <TextInput
                label="Generation Model"
                value={generationModel}
                onChange={(event) => onProfileChange({ generation_model: event.target.value })}
                disabled={disabled}
                hint={generationCost ? `Used by Generate and Regenerate Image. Current catalog rate: ${generationCost}.` : 'Used by Generate and Regenerate Image.'}
              />
            </div>
          </GlassPanel>

          <GlassPanel variant="inset" padding="sm" rounded="lg">
            <div className="flex flex-col gap-[var(--space-3)]">
              <div>
                <p className="workspace-eyebrow">Edit defaults</p>
                <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">
                  Choose the backend that the per-scene Edit Image action will actually call, then tune the parameters it will send.
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
                  Effective backend: {editorBackendLabel(editModel)}.
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
                    label="Negative Prompt"
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
                    Prompt extend
                  </label>
                </>
              )}
            </div>
          </GlassPanel>
        </div>

        <div className="grid gap-[var(--space-4)] xl:grid-cols-2">
          <GlassPanel variant="inset" padding="sm" rounded="lg">
            <div className="workspace-eyebrow">Effective generate request</div>
            <pre
              className="m-0 mt-[var(--space-2)] overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-void)] p-[var(--space-3)] text-[var(--text-tertiary)]"
              style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
            >
              {JSON.stringify(effectiveGenerateRequest, null, 2)}
            </pre>
          </GlassPanel>
          <GlassPanel variant="inset" padding="sm" rounded="lg">
            <div className="workspace-eyebrow">Effective edit request</div>
            <pre
              className="m-0 mt-[var(--space-2)] overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-void)] p-[var(--space-3)] text-[var(--text-tertiary)]"
              style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
            >
              {JSON.stringify(effectiveEditRequest, null, 2)}
            </pre>
          </GlassPanel>
        </div>
      </div>
    </GlassPanel>
  )
}
