export function BackgroundMesh() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0"
      style={{
        zIndex: 'var(--z-base)',
        backgroundColor: 'var(--surface-void)',
        backgroundImage: [
          'radial-gradient(ellipse 80% 60% at 15% 20%, rgba(var(--accent-primary-rgb), 0.07) 0%, transparent 70%)',
          'radial-gradient(ellipse 70% 50% at 75% 45%, rgba(var(--focus-rgb), 0.035) 0%, transparent 65%)',
          'radial-gradient(ellipse 90% 40% at 40% 85%, rgba(var(--accent-primary-hover-rgb), 0.06) 0%, transparent 60%)',
          'repeating-linear-gradient(90deg, transparent, transparent 79px, rgba(var(--text-primary-rgb), 0.024) 79px, rgba(var(--text-primary-rgb), 0.024) 80px)',
          'repeating-linear-gradient(0deg, transparent, transparent 79px, rgba(var(--text-primary-rgb), 0.024) 79px, rgba(var(--text-primary-rgb), 0.024) 80px)',
        ].join(', '),
      }}
    />
  )
}
