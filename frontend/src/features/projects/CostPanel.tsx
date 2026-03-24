import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { Badge } from '../../components/primitives/Badge.tsx'
import type { Plan } from '../../lib/schemas/plan.ts'

function asNumber(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function asEntries(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === 'object'))
    : []
}

function money(value: unknown): string {
  return `$${asNumber(value).toFixed(2)}`
}

function labelForEntry(entry: Record<string, unknown>): string {
  const sceneTitle = typeof entry.scene_title === 'string' && entry.scene_title.trim() ? entry.scene_title.trim() : ''
  const label = typeof entry.label === 'string' && entry.label.trim() ? entry.label.trim() : String(entry.model || entry.provider || entry.kind || 'Cost line')
  const operation = typeof entry.operation === 'string' && entry.operation.trim() ? entry.operation.trim() : ''
  const route = typeof entry.route_kind === 'string' && entry.route_kind.trim() ? entry.route_kind.trim() : ''
  const quality = typeof entry.quality_mode === 'string' && entry.quality_mode.trim() ? entry.quality_mode.trim() : ''
  const parts = [sceneTitle, label, operation, route, quality].filter(Boolean)
  return parts.join(' · ')
}

function cacheDetail(entry: Record<string, unknown>): string | null {
  const units = entry.units && typeof entry.units === 'object' ? entry.units as Record<string, unknown> : null
  if (!units) return null
  const cacheCreate = asNumber(units.cache_creation_input_tokens)
  const cacheRead = asNumber(units.cache_read_input_tokens)
  if (!cacheCreate && !cacheRead) return null
  const total = asNumber(units.input_tokens) + cacheCreate + cacheRead
  const hitRate = total > 0 ? Math.round((cacheRead / total) * 100) : 0
  return `Cache: ${hitRate}% hit (${(cacheRead / 1000).toFixed(0)}K read, ${(cacheCreate / 1000).toFixed(0)}K write)`
}

export function CostPanel({ plan }: { plan: Plan | undefined }) {
  const estimate = plan?.meta?.cost_estimate && typeof plan.meta.cost_estimate === 'object'
    ? plan.meta.cost_estimate as Record<string, unknown>
    : null
  const actual = plan?.meta?.cost_actual && typeof plan.meta.cost_actual === 'object'
    ? plan.meta.cost_actual as Record<string, unknown>
    : null

  if (!estimate && !actual) {
    return null
  }

  const estimateEntries = asEntries(estimate?.entries)
  const actualEntries = asEntries(actual?.entries)
  const status = typeof estimate?.status === 'string' ? estimate.status : 'unbudgeted'
  const budget = estimate?.budget_usd
  const badges = [
    { label: `Estimated ${money(estimate?.gating_total_usd ?? estimate?.total_usd)}`, variant: status === 'over_budget' ? 'warning' as const : 'active' as const },
    budget != null ? { label: `Budget ${money(budget)}`, variant: 'default' as const } : null,
    actual ? { label: `Actual ${money(actual.total_usd)}`, variant: 'success' as const } : null,
  ].filter((item): item is { label: string; variant: 'warning' | 'active' | 'default' | 'success' } => Boolean(item))

  return (
    <GlassPanel variant="default" padding="lg" rounded="lg">
      <h3
        className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0"
        style={{ fontSize: 'var(--text-lg)', fontWeight: 'var(--weight-semibold)', marginBottom: 'var(--space-3)' }}
      >
        Cost Outlook
      </h3>
      <div className="flex flex-wrap gap-[var(--space-2)]" style={{ marginBottom: 'var(--space-3)' }}>
        {badges.map((badge) => (
          <Badge key={badge.label} variant={badge.variant} size="sm">
            {badge.label}
          </Badge>
        ))}
      </div>
      {status === 'over_budget' && (
        <p className="workspace-panel-copy m-0" style={{ marginBottom: 'var(--space-3)' }}>
          Estimated paid generation exceeds the current budget. Review the routes below before kicking off the asset pass.
        </p>
      )}
      {estimate && typeof estimate.breakdown === 'object' && estimate.breakdown && (
        <div className="workspace-kpi-grid" style={{ marginBottom: 'var(--space-3)' }}>
          <div>
            <p className="workspace-eyebrow">LLM</p>
            <div className="workspace-panel-title text-[var(--text-xl)]">{money((estimate.breakdown as Record<string, unknown>).llm_total_usd)}</div>
          </div>
          <div>
            <p className="workspace-eyebrow">Video</p>
            <div className="workspace-panel-title text-[var(--text-xl)]">{money((estimate.breakdown as Record<string, unknown>).video_generation_total_usd)}</div>
          </div>
          <div>
            <p className="workspace-eyebrow">Images</p>
            <div className="workspace-panel-title text-[var(--text-xl)]">{money(asNumber((estimate.breakdown as Record<string, unknown>).image_generation_total_usd) + asNumber((estimate.breakdown as Record<string, unknown>).image_edit_total_usd))}</div>
          </div>
          <div>
            <p className="workspace-eyebrow">Paid TTS</p>
            <div className="workspace-panel-title text-[var(--text-xl)]">{money((estimate.breakdown as Record<string, unknown>).tts_total_usd)}</div>
          </div>
        </div>
      )}
      {actual && typeof actual.total_usd === 'number' && actual.total_usd > 0 && (
        <div className="workspace-kpi-grid" style={{ marginBottom: 'var(--space-3)' }}>
          <div>
            <p className="workspace-eyebrow">Actual LLM</p>
            <div className="workspace-panel-title text-[var(--text-xl)]">{money((actual as Record<string, unknown>).llm_total_usd)}</div>
          </div>
          <div>
            <p className="workspace-eyebrow">Actual Total</p>
            <div className="workspace-panel-title text-[var(--text-xl)]">{money(actual.total_usd)}</div>
          </div>
        </div>
      )}
      <ul className="list-none p-0 m-0 flex flex-col gap-[var(--space-2)]">
        {estimateEntries.slice(0, 5).map((entry, index) => (
          <li key={`estimate-${index}`} className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-3)] py-[var(--space-2)]">
            <div className="text-[var(--text-primary)]" style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)' }}>
              {labelForEntry(entry)}
            </div>
            <div className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)', marginTop: 'var(--space-1)' }}>
              Estimated {money(entry.total_usd)}
            </div>
          </li>
        ))}
        {!estimateEntries.length && actualEntries.slice(0, 5).map((entry, index) => (
          <li key={`actual-${index}`} className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-3)] py-[var(--space-2)]">
            <div className="text-[var(--text-primary)]" style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)' }}>
              {labelForEntry(entry)}
            </div>
            <div className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)', marginTop: 'var(--space-1)' }}>
              Actual {money(entry.total_usd)}
            </div>
            {cacheDetail(entry) && (
              <div className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)', marginTop: 'var(--space-1)' }}>
                {cacheDetail(entry)}
              </div>
            )}
          </li>
        ))}
      </ul>
    </GlassPanel>
  )
}
