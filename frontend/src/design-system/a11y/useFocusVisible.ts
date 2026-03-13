import { useEffect, useRef, useState } from 'react'

/** Track whether the user is navigating via keyboard */
export function useFocusVisible() {
  const [isFocusVisible, setIsFocusVisible] = useState(false)
  const ref = useRef<HTMLElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const onFocus = () => {
      // :focus-visible polyfill logic
      if (el.matches(':focus-visible')) {
        setIsFocusVisible(true)
      }
    }
    const onBlur = () => setIsFocusVisible(false)

    el.addEventListener('focus', onFocus)
    el.addEventListener('blur', onBlur)
    return () => {
      el.removeEventListener('focus', onFocus)
      el.removeEventListener('blur', onBlur)
    }
  }, [])

  return { ref, isFocusVisible }
}
