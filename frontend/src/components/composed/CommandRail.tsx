import { useRef, useCallback, useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import { useUIStore } from '../../stores/ui'
import { useReducedMotion } from '../../design-system/motion'
import { handleArrowNav } from '../../design-system/a11y'
import { transitions } from '../../design-system/motion'
import { ResizeHandle, workspaceLayout } from '../../design-system/layout'

interface NavItem {
  label: string
  icon: React.ReactNode
  path: string
}

const navItems: NavItem[] = [
  {
    label: 'Home',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 7.5L10 2L17 7.5V16.5C17 17.05 16.55 17.5 16 17.5H4C3.45 17.5 3 17.05 3 16.5V7.5Z" />
        <path d="M7.5 17.5V10.5H12.5V17.5" />
      </svg>
    ),
    path: '/',
  },
  {
    label: 'Projects',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2.5 5C2.5 3.62 3.62 2.5 5 2.5H8L10 5H15C16.38 5 17.5 6.12 17.5 7.5V14.5C17.5 15.88 16.38 17 15 17H5C3.62 17 2.5 15.88 2.5 14.5V5Z" />
      </svg>
    ),
    path: '/projects',
  },
  {
    label: 'Queue',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="14" height="4" rx="1" />
        <rect x="3" y="9" width="14" height="4" rx="1" />
        <rect x="3" y="15" width="8" height="2" rx="1" />
      </svg>
    ),
    path: '/queue',
  },
  {
    label: 'Settings',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="10" cy="10" r="2.5" />
        <path d="M16.2 12.3a1.2 1.2 0 0 0 .24 1.32l.04.04a1.46 1.46 0 1 1-2.06 2.06l-.04-.04a1.2 1.2 0 0 0-1.32-.24 1.2 1.2 0 0 0-.73 1.1v.12a1.46 1.46 0 0 1-2.91 0v-.06a1.2 1.2 0 0 0-.79-1.1 1.2 1.2 0 0 0-1.32.24l-.04.04a1.46 1.46 0 1 1-2.06-2.06l.04-.04a1.2 1.2 0 0 0 .24-1.32 1.2 1.2 0 0 0-1.1-.73h-.12a1.46 1.46 0 0 1 0-2.91h.06a1.2 1.2 0 0 0 1.1-.79 1.2 1.2 0 0 0-.24-1.32l-.04-.04A1.46 1.46 0 1 1 7.2 4.44l.04.04a1.2 1.2 0 0 0 1.32.24h.06a1.2 1.2 0 0 0 .73-1.1v-.12a1.46 1.46 0 0 1 2.91 0v.06a1.2 1.2 0 0 0 .73 1.1 1.2 1.2 0 0 0 1.32-.24l.04-.04a1.46 1.46 0 1 1 2.06 2.06l-.04.04a1.2 1.2 0 0 0-.24 1.32v.06a1.2 1.2 0 0 0 1.1.73h.12a1.46 1.46 0 0 1 0 2.91h-.06a1.2 1.2 0 0 0-1.1.73Z" />
      </svg>
    ),
    path: '/settings',
  },
]

export function CommandRail() {
  const railCollapsed = useUIStore((s) => s.railCollapsed)
  const toggleRail = useUIStore((s) => s.toggleRail)
  const railWidth = useUIStore((s) => s.railWidth)
  const setRailWidth = useUIStore((s) => s.setRailWidth)
  const reducedMotion = useReducedMotion()
  const navListRef = useRef<HTMLUListElement>(null)
  const [compactViewport, setCompactViewport] = useState(false)

  useEffect(() => {
    const media = window.matchMedia('(max-width: 900px)')
    const syncViewport = () => setCompactViewport(media.matches)
    syncViewport()

    media.addEventListener('change', syncViewport)
    return () => media.removeEventListener('change', syncViewport)
  }, [])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!navListRef.current) return
      const items = Array.from(
        navListRef.current.querySelectorAll<HTMLElement>('[role="menuitem"]'),
      )
      const current = items.findIndex((el) => el === document.activeElement)
      if (current === -1) return
      handleArrowNav(e, items, current, { orientation: 'vertical', wrap: true })
    },
    [],
  )

  const transitionStyle = reducedMotion
    ? undefined
    : { transition: `width ${transitions.dockSlide}` }
  const effectiveCollapsed = compactViewport || railCollapsed

  return (
    <nav
      aria-label="Main navigation"
      role="navigation"
      className={clsx(
        'relative flex shrink-0 flex-col bg-[var(--surface-shell)] border-r border-[var(--border-subtle)]',
        'h-screen overflow-hidden',
      )}
      style={{
        width: effectiveCollapsed ? workspaceLayout.rail.collapsed : railWidth,
        zIndex: 'var(--z-rail)',
        ...transitionStyle,
      }}
    >
      {/* Brand mark */}
      <div
        className="flex items-center shrink-0 border-b border-[var(--border-subtle)]"
        style={{ height: 56, padding: `0 var(--space-4)` }}
      >
        <span
          className="font-[family-name:var(--font-display)] text-[var(--text-primary)] select-none whitespace-nowrap overflow-hidden"
          style={{ fontWeight: 'var(--weight-bold)', fontSize: 'var(--text-lg)' }}
        >
          {effectiveCollapsed ? 'C' : 'Cathode'}
        </span>
      </div>

      {/* Nav items */}
      <ul
        ref={navListRef}
        role="menu"
        className="flex-1 overflow-y-auto"
        style={{ padding: `var(--space-2) 0` }}
        onKeyDown={handleKeyDown}
      >
        {navItems.map((item) => (
          <li key={item.path} role="none">
            <NavLink
              to={item.path}
              role="menuitem"
              tabIndex={0}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-[var(--space-3)] relative',
                  'text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
                  'outline-none focus-visible:shadow-[var(--focus-ring)]',
                  'rounded-[var(--radius-md)]',
                  isActive && 'text-[var(--text-primary)] bg-[var(--accent-primary-muted)]',
                  !reducedMotion && 'transition-colors duration-150',
                )
              }
              style={{
                height: 44,
                padding: effectiveCollapsed ? '0' : `0 var(--space-4)`,
                margin: `0 var(--space-2)`,
                justifyContent: effectiveCollapsed ? 'center' : 'flex-start',
              }}
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span
                      className="absolute left-0 top-1/2 -translate-y-1/2 rounded-r-[var(--radius-sm)]"
                      style={{
                        width: 3,
                        height: 24,
                        backgroundColor: 'var(--accent-primary)',
                      }}
                    />
                  )}
                  <span className="shrink-0 flex items-center justify-center" style={{ width: 20, height: 20 }}>
                    {item.icon}
                  </span>
                  {!effectiveCollapsed && (
                    <span
                      className="font-[family-name:var(--font-body)] whitespace-nowrap overflow-hidden"
                      style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)' }}
                    >
                      {item.label}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>

      {/* Collapse toggle */}
      <div
        className="shrink-0 border-t border-[var(--border-subtle)] flex items-center"
        style={{ height: 48, padding: `0 var(--space-2)` }}
      >
        <button
          onClick={toggleRail}
          aria-label={
            compactViewport
              ? 'Navigation compacted for narrow window'
              : railCollapsed
                ? 'Expand navigation'
                : 'Collapse navigation'
          }
          disabled={compactViewport}
          className={clsx(
            'flex items-center justify-center w-full rounded-[var(--radius-md)]',
            'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]',
            'hover:bg-[var(--surface-panel-glass)]',
            'outline-none focus-visible:shadow-[var(--focus-ring)]',
            'disabled:cursor-default disabled:opacity-50 disabled:hover:bg-transparent disabled:hover:text-[var(--text-tertiary)]',
            !reducedMotion && 'transition-colors duration-150',
          )}
          style={{ height: 36 }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              transform: effectiveCollapsed ? 'rotate(0deg)' : 'rotate(180deg)',
              transition: reducedMotion ? 'none' : `transform ${transitions.dockSlide}`,
            }}
          >
            <path d="M6 3L11 8L6 13" />
          </svg>
        </button>
      </div>

      {!effectiveCollapsed && !compactViewport && (
        <ResizeHandle
          orientation="vertical"
          label="Resize navigation rail"
          value={railWidth}
          min={workspaceLayout.rail.min}
          max={workspaceLayout.rail.max}
          onChange={setRailWidth}
          className="absolute right-[-7px] top-[56px] bottom-[48px] z-[var(--z-floating)]"
        />
      )}
    </nav>
  )
}
