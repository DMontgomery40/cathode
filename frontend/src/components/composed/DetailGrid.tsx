import type { ReactNode } from 'react'
import { clsx } from 'clsx'

export interface DetailGridItem {
  label: string
  value: ReactNode
  title?: string
}

interface DetailGridProps {
  items: DetailGridItem[]
  columns?: 2 | 3
  className?: string
}

export function DetailGrid({ items, columns = 2, className }: DetailGridProps) {
  return (
    <div
      className={clsx(
        'grid grid-cols-1 gap-[var(--space-2)] rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)]',
        columns === 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-2',
        className,
      )}
      style={{ padding: 'var(--space-2) var(--space-3)' }}
    >
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <div
            className="text-[var(--text-tertiary)]"
            style={{
              fontSize: '10px',
              fontWeight: 'var(--weight-medium)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {item.label}
          </div>
          <div
            className="text-[var(--text-secondary)] truncate"
            style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)' }}
            title={item.title}
          >
            {item.value}
          </div>
        </div>
      ))}
    </div>
  )
}
