import { useCallback, useEffect, useRef, useState } from 'react'
import { clsx } from 'clsx'
import { useReducedMotion, transitions } from '../motion'
import { workspaceLayout } from './constants'

interface ResizeHandleProps {
  orientation: 'vertical' | 'horizontal'
  label: string
  value: number
  min: number
  max: number
  onChange: (next: number) => void
  onReset?: () => void
  direction?: 1 | -1
  controls?: string
  className?: string
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

export function ResizeHandle({
  orientation,
  label,
  value,
  min,
  max,
  onChange,
  onReset,
  direction = 1,
  controls,
  className,
}: ResizeHandleProps) {
  const reducedMotion = useReducedMotion()
  const dragState = useRef<{ startPoint: number; startValue: number } | null>(null)
  const [dragging, setDragging] = useState(false)

  const commitDelta = useCallback(
    (delta: number, startValue = value) => {
      onChange(clamp(Math.round(startValue + (delta * direction)), min, max))
    },
    [direction, max, min, onChange, value],
  )

  useEffect(() => {
    if (!dragging) return undefined

    const handlePointerMove = (event: PointerEvent) => {
      const state = dragState.current
      if (!state) return
      const point = orientation === 'vertical' ? event.clientX : event.clientY
      commitDelta(point - state.startPoint, state.startValue)
    }

    const stopDragging = () => {
      dragState.current = null
      setDragging(false)
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', stopDragging)
    window.addEventListener('pointercancel', stopDragging)

    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', stopDragging)
      window.removeEventListener('pointercancel', stopDragging)
    }
  }, [commitDelta, dragging, orientation])

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault()
      dragState.current = {
        startPoint: orientation === 'vertical' ? event.clientX : event.clientY,
        startValue: value,
      }
      setDragging(true)
    },
    [orientation, value],
  )

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      const step = event.shiftKey ? workspaceLayout.stepLarge : workspaceLayout.step
      const decreaseKeys = orientation === 'vertical' ? ['ArrowLeft'] : ['ArrowUp']
      const increaseKeys = orientation === 'vertical' ? ['ArrowRight'] : ['ArrowDown']

      if (decreaseKeys.includes(event.key)) {
        event.preventDefault()
        onChange(clamp(value - (step * direction), min, max))
        return
      }

      if (increaseKeys.includes(event.key)) {
        event.preventDefault()
        onChange(clamp(value + (step * direction), min, max))
        return
      }

      if (event.key === 'Home') {
        event.preventDefault()
        onChange(min)
        return
      }

      if (event.key === 'End') {
        event.preventDefault()
        onChange(max)
        return
      }

      if ((event.key === 'Enter' || event.key === ' ') && onReset) {
        event.preventDefault()
        onReset()
      }
    },
    [direction, max, min, onChange, onReset, orientation, value],
  )

  return (
    <div
      role="separator"
      tabIndex={0}
      aria-label={label}
      aria-orientation={orientation}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={Math.round(value)}
      aria-controls={controls}
      onPointerDown={handlePointerDown}
      onDoubleClick={onReset}
      onKeyDown={handleKeyDown}
      className={clsx(
        'workspace-resize-handle',
        orientation === 'vertical'
          ? 'workspace-resize-handle--vertical'
          : 'workspace-resize-handle--horizontal',
        dragging && 'is-dragging',
        className,
      )}
      style={{
        transition: dragging || reducedMotion
          ? 'none'
          : `opacity ${transitions.focusPulse}, background-color ${transitions.focusPulse}`,
      }}
      title={`${label}. Drag to resize, use arrow keys for nudges, Home/End for extremes, Enter to reset.`}
    >
      <span className="workspace-resize-handle__grip" aria-hidden="true" />
    </div>
  )
}
