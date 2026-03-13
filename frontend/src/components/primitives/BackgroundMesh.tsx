export function BackgroundMesh() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0"
      style={{
        zIndex: 'var(--z-base)',
        backgroundColor: 'var(--surface-void)',
        backgroundImage: [
          // Warm teal radial, top-left
          'radial-gradient(ellipse 80% 60% at 15% 20%, rgba(91, 138, 130, 0.05) 0%, transparent 70%)',
          // Brass radial, center-right
          'radial-gradient(ellipse 70% 50% at 75% 45%, rgba(200, 169, 110, 0.04) 0%, transparent 65%)',
          // Deeper teal radial, bottom
          'radial-gradient(ellipse 90% 40% at 40% 85%, rgba(91, 138, 130, 0.03) 0%, transparent 60%)',
          // Vertical grid lines
          'repeating-linear-gradient(90deg, transparent, transparent 79px, rgba(240, 236, 228, 0.024) 79px, rgba(240, 236, 228, 0.024) 80px)',
          // Horizontal grid lines
          'repeating-linear-gradient(0deg, transparent, transparent 79px, rgba(240, 236, 228, 0.024) 79px, rgba(240, 236, 228, 0.024) 80px)',
        ].join(', '),
      }}
    />
  )
}
