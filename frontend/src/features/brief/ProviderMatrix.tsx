import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { Badge } from '../../components/primitives/Badge.tsx'
import { useBootstrap } from '../../lib/api/hooks.ts'

function displayProviderName(name: string): string {
  switch (name) {
    case 'codex':
      return 'codex exec'
    default:
      return name
  }
}

export function ProviderMatrix() {
  const { data: bootstrap } = useBootstrap()

  if (!bootstrap) {
    return (
      <GlassPanel variant="default" padding="lg" rounded="lg">
        <div className="workspace-panel-head">
          <div className="min-w-0">
            <p className="workspace-eyebrow">Capability matrix</p>
            <h3 className="workspace-panel-title">Loading provider surface</h3>
            <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">
              Checking local and configured providers for text, image, audio, and video work.
            </p>
          </div>
        </div>

        <div className="workspace-kpi-grid" aria-hidden="true">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] animate-pulse"
              style={{ minHeight: 104 }}
            />
          ))}
        </div>

        <div className="mt-[var(--space-4)] flex flex-wrap gap-[var(--space-2)]" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, index) => (
            <span
              key={index}
              className="rounded-[var(--radius-full)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] animate-pulse"
              style={{ width: index % 2 === 0 ? 88 : 120, height: 28 }}
            />
          ))}
        </div>
      </GlassPanel>
    )
  }

  const { providers } = bootstrap

  const llmItems = [
    providers.api_keys.anthropic ? {
      name: 'anthropic',
      available: true,
    } : null,
    providers.api_keys.openai ? {
      name: 'openai',
      available: true,
    } : null,
  ].filter((item): item is { name: string; available: boolean } => Boolean(item))

  const groups = [
    {
      label: 'LLM',
      items: llmItems,
    },
    {
      label: 'Images',
      items: providers.image_providers.map((p) => ({
        name: displayProviderName(p),
        available: true,
      })),
    },
    {
      label: 'Audio',
      items: Object.entries(providers.tts_providers).map(([name, voice]) => ({
        name: `${name} (${voice})`,
        available: true,
      })),
    },
    {
      label: 'Video',
      items: providers.video_providers.map((p) => ({
        name: p,
        available: true,
      })),
    },
  ]

  const summary = [
    { label: 'Text Models', value: providers.llm_provider ? 1 : 0, note: providers.llm_provider || 'Unavailable' },
    { label: 'Image Engines', value: providers.image_providers.length, note: displayProviderName(providers.image_providers[0] || 'Unavailable') },
    { label: 'Audio Voices', value: Object.keys(providers.tts_providers).length, note: Object.keys(providers.tts_providers)[0] || 'Unavailable' },
    { label: 'Video Engines', value: providers.video_providers.length, note: providers.video_providers[0] || 'Unavailable' },
  ]

  return (
    <GlassPanel variant="default" padding="lg" rounded="lg">
      <div className="workspace-panel-head">
        <div className="min-w-0">
          <p className="workspace-eyebrow">Capability matrix</p>
          <h3 className="workspace-panel-title">Providers</h3>
          <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">
            Cathode only surfaces configured or always-available capabilities, so this page mirrors the real machine instead of pretending every backend exists. For stills, the intended default lane is local Codex execution when it is available.
          </p>
          <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">
            Exact costs are model- and route-specific. Provider badges stay generic; the precise pricing belongs on the model or route choice itself.
          </p>
        </div>
      </div>

      <div className="workspace-kpi-grid" style={{ marginBottom: 'var(--space-4)' }}>
        {summary.map((item) => (
          <div
            key={item.label}
            className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--surface-stage)]"
            style={{ padding: 'var(--space-3)' }}
          >
            <p className="workspace-eyebrow">{item.label}</p>
            <div className="workspace-panel-title text-[var(--text-2xl)]" style={{ marginTop: 'var(--space-2)' }}>
              {item.value}
            </div>
            <p className="workspace-panel-copy m-0 mt-[var(--space-1)]">{item.note}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-[var(--space-4)]">
        {groups.map((group) => (
          <div
            key={group.label}
            className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--surface-stage)]"
            style={{ padding: 'var(--space-3)' }}
          >
            <p className="workspace-eyebrow">{group.label}</p>
            <div
              className="flex flex-wrap gap-[var(--space-2)]"
              style={{ marginTop: 'var(--space-2)' }}
            >
              {group.items.length === 0 ? (
                <Badge variant="default">None available</Badge>
              ) : (
                group.items.map((item) => (
                  <Badge
                    key={item.name}
                    variant={item.available ? 'active' : 'default'}
                  >
                    {item.name}
                  </Badge>
                ))
              )}
            </div>
          </div>
        ))}
      </div>

      <div
        className="border-t border-[var(--border-subtle)]"
        style={{ marginTop: 'var(--space-4)', paddingTop: 'var(--space-4)' }}
      >
        <p className="workspace-eyebrow">API Keys</p>
        <div
          className="flex flex-wrap gap-[var(--space-2)]"
          style={{ marginTop: 'var(--space-2)' }}
        >
          {Object.entries(providers.api_keys).map(([key, present]) => (
            <Badge key={key} variant={present ? 'success' : 'danger'} size="sm">
              {key}
            </Badge>
          ))}
        </div>
      </div>
    </GlassPanel>
  )
}
