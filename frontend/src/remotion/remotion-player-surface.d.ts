// Ambient declaration for the `remotion-player-surface` import specifier used by
// PlayerSurface.tsx. The specifier is resolved at build time by a Vite alias to either
// RemotionPlayerSurface.tsx (when Remotion is installed) or RemotionPlayerSurface.stub.tsx
// (when it is not). This declaration lets TypeScript type-check the lazy import without
// requiring the optional Remotion packages to be present.
declare module 'remotion-player-surface' {
  import type { ComponentType } from 'react'

  const RemotionPlayerSurface: ComponentType<{
    manifest: Record<string, unknown> | null | undefined
    className?: string
    height?: number
  }>

  export default RemotionPlayerSurface
}
