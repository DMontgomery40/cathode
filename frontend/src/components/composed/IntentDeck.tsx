import { useRef, useEffect, useCallback } from 'react'
import { clsx } from 'clsx'
import { GlassPanel } from '../primitives/GlassPanel'
import { useReducedMotion, transitions } from '../../design-system/motion'
import { handleArrowNav } from '../../design-system/a11y'

interface IntentCard {
  id: string
  title: string
  description: string
  icon: React.ReactNode
  href?: string
  onClick?: () => void
  disabled?: boolean
  badge?: string
}

interface IntentDeckProps {
  cards: IntentCard[]
  columns?: 2 | 3
}

export function IntentDeck({ cards, columns = 3 }: IntentDeckProps) {
  const reducedMotion = useReducedMotion()
  const gridRef = useRef<HTMLDivElement>(null)
  const cardRefs = useRef<(HTMLButtonElement | HTMLAnchorElement | null)[]>([])

  // Staggered entrance animation
  useEffect(() => {
    if (reducedMotion) return
    const els = cardRefs.current.filter(Boolean) as HTMLElement[]
    els.forEach((el, i) => {
      el.style.opacity = '0'
      el.style.transform = 'translateY(8px)'
      const timeout = setTimeout(() => {
        el.style.transition = `opacity ${transitions.enterSoft}, transform ${transitions.enterSoft}`
        el.style.opacity = '1'
        el.style.transform = 'translateY(0)'
      }, 50 * i)
      return () => clearTimeout(timeout)
    })
  }, [reducedMotion])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const items = cardRefs.current.filter(Boolean) as HTMLElement[]
      const current = items.findIndex((el) => el === document.activeElement)
      if (current === -1) return
      handleArrowNav(e, items, current, { orientation: 'both', wrap: true })
    },
    [],
  )

  return (
    <div
      ref={gridRef}
      role="group"
      aria-label="Quick actions"
      className={clsx(
        'grid gap-[var(--space-4)]',
        columns === 2 && 'grid-cols-1 sm:grid-cols-2',
        columns === 3 && 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
      )}
      onKeyDown={handleKeyDown}
    >
      {cards.map((card, i) => {
        const isPrimary = i === 0

        const cardContent = (
          <>
            {/* Top row: icon + badge */}
            <div className="flex items-start justify-between">
              <span
                className={clsx(
                  'flex items-center justify-center rounded-[var(--radius-md)]',
                  isPrimary
                    ? 'text-[var(--accent-primary)] bg-[var(--accent-primary-muted)]'
                    : 'text-[var(--text-secondary)] bg-[var(--surface-stage)]',
                )}
                style={{ width: 40, height: 40 }}
                aria-hidden="true"
              >
                {card.icon}
              </span>
              {card.badge && (
                <span
                  className="rounded-[var(--radius-full)] bg-[var(--accent-secondary-muted)] text-[var(--accent-secondary)] font-[family-name:var(--font-mono)]"
                  style={{
                    fontSize: 'var(--text-xs)',
                    padding: `var(--space-1) var(--space-2)`,
                    fontWeight: 'var(--weight-medium)',
                  }}
                >
                  {card.badge}
                </span>
              )}
            </div>

            {/* Title */}
            <h3
              className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0"
              style={{
                fontSize: 'var(--text-lg)',
                fontWeight: 'var(--weight-semibold)',
                lineHeight: 'var(--leading-snug)',
                marginTop: 'var(--space-3)',
              }}
            >
              {card.title}
            </h3>

            {/* Description */}
            <p
              className="font-[family-name:var(--font-body)] text-[var(--text-secondary)] m-0"
              style={{
                fontSize: 'var(--text-sm)',
                lineHeight: 'var(--leading-normal)',
                marginTop: 'var(--space-1)',
              }}
            >
              {card.description}
            </p>
          </>
        )

        const sharedClassName = clsx(
          'block text-left cursor-pointer w-full',
          'outline-none focus-visible:shadow-[var(--focus-ring)]',
          isPrimary && 'border-[var(--border-accent)] shadow-[0_0_24px_rgba(200,169,110,0.06)]',
          card.disabled && 'opacity-50 cursor-not-allowed',
          !reducedMotion && 'transition-all duration-200',
          !reducedMotion && !card.disabled && 'hover:-translate-y-0.5 hover:border-[var(--border-accent)]',
        )

        if (card.href && !card.disabled) {
          return (
            <GlassPanel
              key={card.id}
              as="a"
              ref={(el: HTMLElement | null) => { cardRefs.current[i] = el as HTMLAnchorElement | null }}
              href={card.href}
              variant="elevated"
              padding="lg"
              rounded="xl"
              className={sharedClassName}
              tabIndex={0}
            >
              {cardContent}
            </GlassPanel>
          )
        }

        return (
          <GlassPanel
            key={card.id}
            as="button"
            ref={(el: HTMLElement | null) => { cardRefs.current[i] = el as HTMLButtonElement | null }}
            type="button"
            variant="elevated"
            padding="lg"
            rounded="xl"
            className={sharedClassName}
            onClick={card.disabled ? undefined : card.onClick}
            disabled={card.disabled}
            tabIndex={0}
          >
            {cardContent}
          </GlassPanel>
        )
      })}
    </div>
  )
}
