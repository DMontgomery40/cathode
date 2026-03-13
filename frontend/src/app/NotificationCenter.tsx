import { clsx } from 'clsx'
import { useNotificationsStore } from '../stores/notifications'

function toneClass(tone: string | undefined): string {
  switch (tone) {
    case 'success':
      return 'border-[rgba(74,179,117,0.3)] bg-[rgba(74,179,117,0.14)] text-[var(--text-primary)]'
    case 'warning':
      return 'border-[rgba(209,146,50,0.32)] bg-[rgba(209,146,50,0.14)] text-[var(--text-primary)]'
    case 'danger':
      return 'border-[rgba(200,90,90,0.3)] bg-[rgba(200,90,90,0.14)] text-[var(--text-primary)]'
    default:
      return 'border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] text-[var(--text-primary)]'
  }
}

export function NotificationCenter() {
  const items = useNotificationsStore((state) => state.items)
  const dismiss = useNotificationsStore((state) => state.dismiss)

  if (items.length === 0) {
    return null
  }

  return (
    <div
      className="pointer-events-none fixed right-[var(--space-4)] top-[var(--space-4)] z-[var(--z-toast)] flex w-[min(28rem,calc(100vw-2rem))] flex-col gap-[var(--space-2)]"
      role="region"
      aria-label="Notifications"
    >
      {items.map((item) => (
        <div
          key={item.id}
          className={clsx(
            'pointer-events-auto rounded-[var(--radius-lg)] border shadow-[var(--shadow-floating)] backdrop-blur-[var(--glass-blur)]',
            toneClass(item.tone),
          )}
          role="alert"
          style={{ padding: 'var(--space-3)' }}
        >
          <div className="flex items-start gap-[var(--space-3)]">
            <div className="min-w-0 flex-1">
              <div
                className="truncate"
                style={{
                  fontSize: 'var(--text-sm)',
                  fontWeight: 'var(--weight-semibold)',
                  fontFamily: 'var(--font-display)',
                }}
              >
                {item.title}
              </div>
              {item.description && (
                <div
                  className="mt-[var(--space-1)] whitespace-pre-wrap text-[var(--text-secondary)]"
                  style={{ fontSize: 'var(--text-xs)', lineHeight: 'var(--leading-normal)' }}
                >
                  {item.description}
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => dismiss(item.id)}
              className="rounded-[var(--radius-sm)] bg-transparent px-[var(--space-1)] py-[var(--space-1)] text-[var(--text-tertiary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
