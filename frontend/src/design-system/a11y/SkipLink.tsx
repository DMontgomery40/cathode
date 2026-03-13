export function SkipLink({ targetId = 'main-content', label = 'Skip to main content' }: {
  targetId?: string
  label?: string
}) {
  return (
    <a
      href={`#${targetId}`}
      className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:rounded-md focus:bg-[var(--accent-primary)] focus:text-[var(--text-inverse)] focus:outline-none font-[family-name:var(--font-body)]"
    >
      {label}
    </a>
  )
}
