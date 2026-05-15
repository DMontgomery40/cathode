type CostEntry = Record<string, unknown>

export interface CostCatalog {
  version?: string
  entries?: CostEntry[]
  fx?: Record<string, number>
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

export function costCatalogEntries(catalog?: CostCatalog | null): CostEntry[] {
  return Array.isArray(catalog?.entries) ? catalog!.entries : []
}

export function findCostEntry(
  catalog: CostCatalog | null | undefined,
  query: { kind: string; provider: string; model: string; variant?: string | null },
): CostEntry | null {
  const desiredVariant = query.variant ? query.variant.toLowerCase() : ''
  return costCatalogEntries(catalog).find((entry) => {
    if (asString(entry.kind) !== query.kind) return false
    if (asString(entry.provider).toLowerCase() !== query.provider.toLowerCase()) return false
    if (asString(entry.model) !== query.model) return false
    const entryVariant = asString(entry.variant).toLowerCase()
    if (desiredVariant) return entryVariant === desiredVariant
    return !entryVariant
  }) ?? null
}

export function entryDisplayPrice(entry: CostEntry | null | undefined): string {
  const value = asString(entry?.display_price)
  return value || ''
}

export function entryLabel(entry: CostEntry | null | undefined): string {
  return asString(entry?.label)
}
