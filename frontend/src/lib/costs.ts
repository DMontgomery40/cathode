export interface CostCatalogEntry {
  kind?: string
  provider?: string
  model?: string
  unit_label?: string
  unit_price_usd?: number
  display_price?: string
  [key: string]: unknown
}

export type CostCatalog = CostCatalogEntry[] | Record<string, unknown>

export function findCostEntry(
  catalog: CostCatalog | null,
  query: { kind?: string; provider?: string; model?: string },
): CostCatalogEntry | null {
  const entries = Array.isArray(catalog)
    ? catalog
    : Array.isArray((catalog as Record<string, unknown> | null)?.entries)
      ? ((catalog as Record<string, unknown>).entries as CostCatalogEntry[])
      : []
  return entries.find((entry) => {
    return (!query.kind || entry.kind === query.kind)
      && (!query.provider || entry.provider === query.provider)
      && (!query.model || entry.model === query.model)
  }) ?? null
}

export function entryDisplayPrice(entry: CostCatalogEntry | null): string {
  if (!entry) return ''
  if (typeof entry.display_price === 'string') return entry.display_price
  if (typeof entry.unit_price_usd === 'number') {
    return `$${entry.unit_price_usd.toFixed(4)}${entry.unit_label ? ` / ${entry.unit_label}` : ''}`
  }
  return ''
}
