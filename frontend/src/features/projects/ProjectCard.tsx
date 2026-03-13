import { useNavigate } from 'react-router-dom'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { Badge } from '../../components/primitives/Badge.tsx'
import type { ProjectSummary } from '../../lib/api/projects.ts'
import { projectMediaUrl } from '../../lib/media-url.ts'

interface ProjectCardProps {
  project: ProjectSummary
}

export function ProjectCard({ project }: ProjectCardProps) {
  const navigate = useNavigate()

  const statusVariant = project.has_video ? 'success' : project.scene_count > 0 ? 'active' : 'default'
  const statusLabel = project.has_video ? 'Rendered' : project.scene_count > 0 ? 'In Progress' : 'Empty'

  const target = project.scene_count > 0
    ? `/projects/${encodeURIComponent(project.name)}/scenes`
    : `/projects/${encodeURIComponent(project.name)}/brief`
  const thumbnailUrl = projectMediaUrl(project.name, project.thumbnail_path)

  return (
    <GlassPanel
      as="button"
      type="button"
      variant="elevated"
      padding="none"
      rounded="lg"
      className="block text-left cursor-pointer w-full outline-none focus-visible:shadow-[var(--focus-ring)] transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--border-default)]"
      onClick={() => navigate(target)}
    >
      {/* Thumbnail area */}
      <div
        className="w-full bg-[var(--surface-stage)] flex items-center justify-center overflow-hidden rounded-t-[var(--radius-lg)]"
        style={{ height: 140 }}
      >
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={`${project.name} thumbnail`}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />
        ) : (
          <svg
            width="32"
            height="32"
            viewBox="0 0 32 32"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            className="text-[var(--text-tertiary)]"
            aria-hidden="true"
          >
            <rect x="4" y="6" width="24" height="20" rx="3" />
            <path d="M12 13L19 16.5L12 20V13Z" />
          </svg>
        )}
      </div>

      {/* Info */}
      <div style={{ padding: 'var(--space-4)' }}>
        <div className="flex items-start justify-between gap-[var(--space-2)]">
          <h3
            className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0 truncate"
            style={{
              fontSize: 'var(--text-base)',
              fontWeight: 'var(--weight-semibold)',
              lineHeight: 'var(--leading-snug)',
            }}
          >
            {project.name}
          </h3>
          <Badge variant={statusVariant} size="sm">
            {statusLabel}
          </Badge>
        </div>
        <p
          className="text-[var(--text-tertiary)] m-0"
          style={{
            fontSize: 'var(--text-xs)',
            marginTop: 'var(--space-1)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {project.scene_count} {project.scene_count === 1 ? 'scene' : 'scenes'}
        </p>
      </div>
    </GlassPanel>
  )
}
