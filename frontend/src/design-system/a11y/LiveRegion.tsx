import { useEffect, useRef } from 'react'

interface LiveRegionProps {
  message: string
  politeness?: 'polite' | 'assertive'
  clearAfterMs?: number
}

/** Announce dynamic content changes to screen readers */
export function LiveRegion({ message, politeness = 'polite', clearAfterMs = 5000 }: LiveRegionProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current || !message) return
    ref.current.textContent = message
    if (clearAfterMs > 0) {
      const timer = setTimeout(() => {
        if (ref.current) ref.current.textContent = ''
      }, clearAfterMs)
      return () => clearTimeout(timer)
    }
  }, [message, clearAfterMs])

  return (
    <div
      ref={ref}
      role="status"
      aria-live={politeness}
      aria-atomic="true"
      className="sr-only"
    />
  )
}
