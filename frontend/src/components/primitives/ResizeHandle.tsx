import { useRef } from 'react'
import { clsx } from 'clsx'
import { transitions, useReducedMotion } from '../../design-system/motion'

interface ResizeHandleProps {
  orientation: 'horizontal' | 'vertical'
  label: string
  controls?: string
  value: number
  min: number
  max: number
  step?: number
  onResizeDelta: (delta: number) => void
  onJump?: (nextValue: number) => void
  onReset?: () => void
  className?: string
}

export function ResizeHandle({
  orientation,
  label,
  controls,
  value,
  min,
  max,
  step = 24,
  onResizeDelta,
  onJump,
  onReset,
  className,
}: ResizeHandleProps) {
  const reducedMotion = useReducedMotion()
  const pointerIdRef = useRef<number | null>(null)
  const lastPositionRef = useRef<number | null>(null)

  const endDrag = () => {
    pointerIdRef.current = null
    lastPositionRef.current = null
    window.removeEventListener('pointermove', handleWindowPointerMove)
    window.removeEventListener('pointerup', handleWindowPointerUp)
  }

  const handleWindowPointerMove = (event: PointerEvent) => {
    if (pointerIdRef.current !== event.pointerId) return
    const position = orientation === 'vertical' ? event.clientX : event.clientY
    const previous = lastPositionRef.current ?? position
    const delta = position - previous
    lastPositionRef.current = position
    onResizeDelta(delta)
  }

  const handleWindowPointerUp = (event: PointerEvent) => {
    if (pointerIdRef.current !== event.pointerId) return
    endDrag()
  }

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    pointerIdRef.current = event.pointerId
    lastPositionRef.current = orientation === 'vertical' ? event.clientX : event.clientY
    window.addEventListener('pointermove', handleWindowPointerMove)
    window.addEventListener('pointerup', handleWindowPointerUp)
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const amount = event.shiftKey ? step * 2 : step

    if (orientation === 'vertical') {
      if (event.key === 'ArrowLeft') {
        event.preventDefault()
        onResizeDelta(-amount)
        return
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault()
        onResizeDelta(amount)
        return
      }
    } else {
      if (event.key === 'ArrowUp') {
        event.preventDefault()
        onResizeDelta(-amount)
        return
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        onResizeDelta(amount)
        return
      }
    }

    if (event.key === 'Home' && onJump) {
      event.preventDefault()
      onJump(min)
      return
    }

    if (event.key === 'End' && onJump) {
      event.preventDefault()
      onJump(max)
      return
    }

    if ((event.key === 'Enter' || event.key === ' ') && onReset) {
      event.preventDefault()
      onReset()
    }
  }

  return (
    <div
      role="separator"
      tabIndex={0}
      aria-label={label}
      aria-controls={controls}
      aria-orientation={orientation}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={Math.round(value)}
      title={`${label}. Drag to resize, use arrow keys for fine adjustment, press Enter to reset.`}
      onPointerDown={handlePointerDown}
      onDoubleClick={onReset}
      onKeyDown={handleKeyDown}
      className={clsx(
        'group relative flex shrink-0 items-center justify-center select-none outline-none touch-none',
        'focus-visible:shadow-[var(--focus-ring)]',
        orientation === 'vertical'
          ? 'h-full w-[var(--workspace-splitter-size)] cursor-col-resize'
          : 'w-full h-[var(--workspace-splitter-size)] cursor-row-resize',
        className,
      )}
      style={{
        transition: reducedMotion ? 'none' : `background-color ${transitions.focusPulse}`,
      }}
    >
      <span
        aria-hidden="true"
        className={clsx(
          'pointer-events-none rounded-full border border-[var(--border-default)] bg-[var(--surface-panel-glass)]',
          'shadow-[var(--glass-highlight)]',
          'group-hover:border-[var(--border-accent)] group-hover:bg-[var(--surface-elevated)]',
          orientation === 'vertical' ? 'h-16 w-2.5' : 'h-2.5 w-16',
        )}
        style={{
          transition: reducedMotion
            ? 'none'
            : `transform ${transitions.focusPulse}, background-color ${transitions.focusPulse}, border-color ${transitions.focusPulse}`,
        }}
      />
    </div>
  )
}
