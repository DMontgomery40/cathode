import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { projectMediaUrl } from '../../lib/media-url.ts'

interface ArtifactShelfProps {
  videoPath: string | null | undefined
  videoExists?: boolean
  project: string
}

export function ArtifactShelf({ videoPath, videoExists, project }: ArtifactShelfProps) {
  if (!videoPath) {
    return (
      <GlassPanel variant="inset" padding="lg" className="flex items-center justify-center" style={{ minHeight: 200 }}>
        <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-sm)' }}>
          No rendered video yet
        </span>
      </GlassPanel>
    )
  }

  const filename = videoPath.split('/').pop() ?? 'output.mp4'
  const videoUrl = videoExists === false ? null : projectMediaUrl(project, videoPath)

  if (!videoUrl) {
    return (
      <GlassPanel variant="inset" padding="lg" className="flex items-center justify-center" style={{ minHeight: 200 }}>
        <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-sm)' }}>
          Render metadata points at a missing or invalid video
        </span>
      </GlassPanel>
    )
  }

  return (
    <GlassPanel variant="inset" padding="md">
      <h3
        className="text-[var(--text-secondary)] m-0"
        style={{
          fontSize: 'var(--text-xs)',
          fontWeight: 'var(--weight-medium)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          marginBottom: 'var(--space-3)',
        }}
      >
        Output
      </h3>

      <div className="flex flex-col gap-[var(--space-3)]">
        <video
          controls
          src={videoUrl}
          className="w-full rounded-[var(--radius-md)]"
          style={{ maxHeight: 400 }}
        />

        <div className="flex items-center justify-between">
          <span
            className="text-[var(--text-secondary)] font-[family-name:var(--font-mono)]"
            style={{ fontSize: 'var(--text-xs)' }}
          >
            {filename}
          </span>
          <a
            href={videoUrl}
            download={filename}
            className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)] no-underline outline-none focus-visible:shadow-[var(--focus-ring)]"
            style={{
              padding: `var(--space-2) var(--space-3)`,
              fontSize: 'var(--text-xs)',
              fontWeight: 'var(--weight-medium)',
            }}
          >
            Download
          </a>
        </div>
      </div>
    </GlassPanel>
  )
}
