import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'

interface RenderSettingsProps {
  outputFilename: string
  onOutputFilenameChange: (v: string) => void
  fps: number
  onFpsChange: (v: number) => void
  renderBackend: string
  renderBackendReason?: string | null
  textRenderMode: string
  onTextRenderModeChange: (v: string) => void
  textRenderModeDisabled?: boolean
  renderProfile?: Record<string, unknown> | null
}

export function RenderSettings({
  outputFilename,
  onOutputFilenameChange,
  fps,
  onFpsChange,
  renderBackend,
  renderBackendReason,
  textRenderMode,
  onTextRenderModeChange,
  textRenderModeDisabled = false,
  renderProfile,
}: RenderSettingsProps) {
  const aspect = renderProfile?.aspect_ratio as string | undefined
  const resolution = renderProfile?.resolution as string | undefined
  const textStrategyCopy = textRenderMode === 'deterministic_overlay'
    ? "Cathode overlays the scene's on-screen text during Remotion renders. Rebuild visuals if you want generated images to stop baking their own copy."
    : 'Generated visuals and footage own the visible copy, and Remotion avoids adding a second generic text layer.'

  return (
    <GlassPanel variant="default" padding="md">
      <h3
        className="text-[var(--text-secondary)] m-0"
        style={{
          fontSize: 'var(--text-xs)',
          fontWeight: 'var(--weight-medium)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          marginBottom: 'var(--space-4)',
        }}
      >
        Render Settings
      </h3>

      <div className="flex flex-col gap-[var(--space-3)]">
        {/* Output filename */}
        <div className="flex flex-col gap-[var(--space-1)]">
          <label
            htmlFor="output-filename"
            className="text-[var(--text-tertiary)]"
            style={{ fontSize: 'var(--text-xs)' }}
          >
            Output filename
          </label>
          <input
            id="output-filename"
            type="text"
            value={outputFilename}
            onChange={(e) => onOutputFilenameChange(e.target.value)}
            className="w-full bg-[var(--surface-stage)] text-[var(--text-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-md)] outline-none focus-visible:shadow-[var(--focus-ring)]"
            style={{
              fontSize: 'var(--text-sm)',
              padding: `var(--space-2) var(--space-3)`,
              fontFamily: 'var(--font-mono)',
            }}
            placeholder="output.mp4"
          />
        </div>

        {/* FPS */}
        <div className="flex flex-col gap-[var(--space-1)]">
          <label
            htmlFor="fps-select"
            className="text-[var(--text-tertiary)]"
            style={{ fontSize: 'var(--text-xs)' }}
          >
            Frames per second
          </label>
          <select
            id="fps-select"
            value={fps}
            onChange={(e) => onFpsChange(Number(e.target.value))}
            className="w-full bg-[var(--surface-stage)] text-[var(--text-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-md)] outline-none focus-visible:shadow-[var(--focus-ring)]"
            style={{
              fontSize: 'var(--text-sm)',
              padding: `var(--space-2) var(--space-3)`,
            }}
          >
            <option value={24}>24 fps</option>
            <option value={30}>30 fps</option>
            <option value={60}>60 fps</option>
          </select>
        </div>

        <div className="flex flex-col gap-[var(--space-1)]">
          <label
            htmlFor="text-render-mode-select"
            className="text-[var(--text-tertiary)]"
            style={{ fontSize: 'var(--text-xs)' }}
          >
            Text strategy
          </label>
          <select
            id="text-render-mode-select"
            value={textRenderMode}
            onChange={(e) => onTextRenderModeChange(e.target.value)}
            disabled={textRenderModeDisabled}
            className="w-full bg-[var(--surface-stage)] text-[var(--text-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-md)] outline-none focus-visible:shadow-[var(--focus-ring)]"
            style={{
              fontSize: 'var(--text-sm)',
              padding: `var(--space-2) var(--space-3)`,
            }}
          >
            <option value="visual_authored">Visual-authored text</option>
            <option value="deterministic_overlay">Deterministic overlay</option>
          </select>
          <p className="m-0 text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
            {textStrategyCopy}
          </p>
        </div>

        {/* Read-only profile info */}
        {(aspect || resolution) && (
          <div className="flex gap-[var(--space-4)]" style={{ marginTop: 'var(--space-2)' }}>
            {aspect && (
              <div className="flex flex-col gap-[var(--space-1)]">
                <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  Aspect Ratio
                </span>
                <span
                  className="text-[var(--text-secondary)] font-[family-name:var(--font-mono)]"
                  style={{ fontSize: 'var(--text-sm)' }}
                >
                  {aspect}
                </span>
              </div>
            )}
            {resolution && (
              <div className="flex flex-col gap-[var(--space-1)]">
                <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                  Resolution
                </span>
                <span
                  className="text-[var(--text-secondary)] font-[family-name:var(--font-mono)]"
                  style={{ fontSize: 'var(--text-sm)' }}
                >
                  {resolution}
                </span>
              </div>
            )}
          </div>
        )}

        <div className="flex flex-col gap-[var(--space-1)]" style={{ marginTop: 'var(--space-2)' }}>
          <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
            Resolved render backend
          </span>
          <span
            className="text-[var(--text-secondary)] font-[family-name:var(--font-mono)]"
            style={{ fontSize: 'var(--text-sm)' }}
          >
            {renderBackend}
          </span>
          {renderBackendReason ? (
            <p className="m-0 text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
              {renderBackendReason}
            </p>
          ) : null}
        </div>
      </div>
    </GlassPanel>
  )
}
