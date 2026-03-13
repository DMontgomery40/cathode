import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { clsx } from 'clsx'

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-[var(--space-2)]',
    'rounded-[var(--radius-md)] font-[family-name:var(--font-body)]',
    'outline-none focus-visible:shadow-[var(--focus-ring)]',
    'cursor-pointer select-none whitespace-nowrap',
    'transition-colors duration-150',
    'disabled:opacity-50 disabled:cursor-not-allowed',
  ].join(' '),
  {
    variants: {
      variant: {
        primary: [
          'bg-[var(--accent-primary)] text-[var(--surface-void)]',
          'hover:bg-[var(--accent-primary-hover)]',
          'border border-transparent',
        ].join(' '),
        secondary: [
          'bg-[var(--surface-stage)] text-[var(--text-primary)]',
          'hover:bg-[var(--surface-panel-glass-hover)]',
          'border border-[var(--border-subtle)]',
        ].join(' '),
        ghost: [
          'bg-transparent text-[var(--text-secondary)]',
          'hover:bg-[var(--surface-stage)] hover:text-[var(--text-primary)]',
          'border border-transparent',
        ].join(' '),
        danger: [
          'bg-[rgba(200,90,90,0.12)] text-[var(--signal-danger)]',
          'hover:bg-[rgba(200,90,90,0.2)]',
          'border border-[rgba(200,90,90,0.3)]',
        ].join(' '),
      },
      size: {
        sm: '',
        md: '',
        lg: '',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  },
)

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ variant, size, loading, className, children, disabled, ...rest }, ref) {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        className={clsx(buttonVariants({ variant, size }), className)}
        style={{
          fontSize: size === 'lg' ? 'var(--text-base)' : size === 'sm' ? 'var(--text-xs)' : 'var(--text-sm)',
          fontWeight: 'var(--weight-semibold)',
          padding:
            size === 'lg'
              ? 'var(--space-3) var(--space-6)'
              : size === 'sm'
                ? 'var(--space-1) var(--space-3)'
                : 'var(--space-2) var(--space-4)',
          height: size === 'lg' ? 44 : size === 'sm' ? 30 : 36,
        }}
        {...rest}
      >
        {loading && (
          <svg
            className="animate-spin"
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
          >
            <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" opacity="0.3" />
            <path d="M14 8a6 6 0 0 0-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        )}
        {children}
      </button>
    )
  },
)
