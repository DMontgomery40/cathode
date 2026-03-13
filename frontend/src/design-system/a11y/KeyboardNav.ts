/** Arrow-key navigation helper for list/grid widgets */
export function handleArrowNav(
  e: React.KeyboardEvent,
  items: HTMLElement[],
  currentIndex: number,
  options: { orientation?: 'horizontal' | 'vertical' | 'both'; wrap?: boolean } = {}
): number | null {
  const { orientation = 'vertical', wrap = true } = options
  const len = items.length
  if (len === 0) return null

  let nextIndex: number | null = null

  const isVert = orientation === 'vertical' || orientation === 'both'
  const isHoriz = orientation === 'horizontal' || orientation === 'both'

  if (e.key === 'ArrowDown' && isVert) {
    nextIndex = wrap ? (currentIndex + 1) % len : Math.min(currentIndex + 1, len - 1)
  } else if (e.key === 'ArrowUp' && isVert) {
    nextIndex = wrap ? (currentIndex - 1 + len) % len : Math.max(currentIndex - 1, 0)
  } else if (e.key === 'ArrowRight' && isHoriz) {
    nextIndex = wrap ? (currentIndex + 1) % len : Math.min(currentIndex + 1, len - 1)
  } else if (e.key === 'ArrowLeft' && isHoriz) {
    nextIndex = wrap ? (currentIndex - 1 + len) % len : Math.max(currentIndex - 1, 0)
  } else if (e.key === 'Home') {
    nextIndex = 0
  } else if (e.key === 'End') {
    nextIndex = len - 1
  }

  if (nextIndex !== null) {
    e.preventDefault()
    items[nextIndex]?.focus()
  }

  return nextIndex
}
