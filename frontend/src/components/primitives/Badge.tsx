import { cva, type VariantProps } from 'class-variance-authority'
import { clsx } from 'clsx'
import type { ReactNode } from 'react'

const badgeVariants = cva(
  [
    'inline-flex items-center rounded-[var(--radius-full)]',
    'font-[family-name:var(--font-mono)]',
    'select-none whitespace-nowrap',
  ].join(' '),
  {
    variants: {
      variant: {
        default: 'bg-[var(--surface-stage)] text-[var(--text-secondary)] border border-[var(--border-subtle)]',
        success: 'bg-[rgba(107,154,114,0.12)] text-[var(--signal-success)] border border-[rgba(107,154,114,0.3)]',
        active: 'bg-[rgba(91,138,130,0.12)] text-[var(--signal-active)] border border-[rgba(91,138,130,0.3)]',
        warning: 'bg-[rgba(200,122,78,0.12)] text-[var(--signal-warning)] border border-[rgba(200,122,78,0.3)]',
        danger: 'bg-[rgba(200,90,90,0.12)] text-[var(--signal-danger)] border border-[rgba(200,90,90,0.3)]',
        accent: 'bg-[var(--accent-primary-muted)] text-[var(--accent-primary)] border border-[var(--border-accent)]',
      },
      size: {
        sm: '',
        md: '',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'sm',
    },
  },
)

interface BadgeProps extends VariantProps<typeof badgeVariants> {
  children: ReactNode
  className?: string
}

export function Badge({ variant, size, className, children }: BadgeProps) {
  return (
    <span
      className={clsx(badgeVariants({ variant, size }), className)}
      style={{
        fontSize: size === 'md' ? 'var(--text-sm)' : 'var(--text-xs)',
        padding: size === 'md' ? 'var(--space-1) var(--space-3)' : 'var(--space-0) var(--space-2)',
        fontWeight: 'var(--weight-medium)',
      }}
    >
      {children}
    </span>
  )
}
