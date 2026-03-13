import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, createElement, type ElementType, type ReactNode, type Ref } from 'react'
import { clsx } from 'clsx'

const glassPanelVariants = cva(
  [
    'border border-[var(--border-subtle)]',
    'backdrop-blur-[var(--glass-blur)]',
    'bg-[var(--surface-panel-glass)]',
    'transition-colors duration-250',
    'hover:bg-[var(--surface-panel-glass-hover)]',
  ].join(' '),
  {
    variants: {
      variant: {
        default: 'shadow-[var(--glass-highlight)]',
        elevated: 'shadow-[var(--glass-highlight),var(--glass-shadow)]',
        inset: 'shadow-[var(--glass-highlight)] bg-[var(--surface-stage)]',
        floating:
          'shadow-[var(--glass-highlight),var(--glass-shadow)] border-[var(--border-default)]',
      },
      padding: {
        none: 'p-0',
        sm: 'p-[var(--space-3)]',
        md: 'p-[var(--space-4)]',
        lg: 'p-[var(--space-6)]',
      },
      rounded: {
        md: 'rounded-[var(--radius-md)]',
        lg: 'rounded-[var(--radius-lg)]',
        xl: 'rounded-[var(--radius-xl)]',
      },
    },
    defaultVariants: {
      variant: 'default',
      padding: 'md',
      rounded: 'lg',
    },
  },
)

interface GlassPanelProps extends VariantProps<typeof glassPanelVariants> {
  as?: ElementType
  className?: string
  children?: ReactNode
  ref?: Ref<HTMLElement>
  // Common HTML props used by consumers
  id?: string
  role?: string
  tabIndex?: number
  style?: React.CSSProperties
  onClick?: React.MouseEventHandler
  onKeyDown?: React.KeyboardEventHandler
  'aria-label'?: string
  'aria-labelledby'?: string
  'aria-describedby'?: string
  'aria-hidden'?: boolean
  href?: string
  type?: string
  disabled?: boolean
}

export const GlassPanel = forwardRef<HTMLElement, GlassPanelProps>(
  function GlassPanel(
    { as = 'div', variant, padding, rounded, className, children, ...rest },
    ref,
  ) {
    return createElement(
      as,
      {
        ref,
        className: clsx(glassPanelVariants({ variant, padding, rounded }), className),
        ...rest,
      },
      children,
    )
  },
)
