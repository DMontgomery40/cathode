// Remotion-free stand-in for the live composition player. Vite's `remotion-player-surface`
// alias resolves here when the optional Remotion packages are not installed, so the lazy
// chunk loaded by PlayerSurface contains only the placeholder and never references Remotion.
export { default } from './RemotionUnavailable.tsx'
