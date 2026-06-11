import { useNavigate } from 'react-router-dom'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { Badge } from '../../components/primitives/Badge.tsx'
import type { ProjectSummary } from '../../lib/api/projects.ts'
import type { JobStatus } from '../../lib/api/jobs.ts'
import { projectMediaUrl } from '../../lib/media-url.ts'
import { projectModeFromSummary } from '../../lib/project-mode.ts'

interface ProjectCardProps {
  project: ProjectSummary
}

function formatProjectDate(iso?: string | null): string | null {
  if (!iso) return null
  const date = new Date(iso)
  if (Number.isNaN(date.valueOf())) return null
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function statusVariant(status: string): 'default' | 'success' | 'active' | 'warning' | 'danger' {
  switch (status) {
    case 'Queued':
    case 'Running':
      return 'active'
    case 'Rendered':
    case 'Completed':
      return 'success'
    case 'Partial':
    case 'Cancelled':
      return 'warning'
    case 'Failed':
    case 'Error':
      return 'danger'
    default:
      return 'default'
  }
}

function projectStatus(project: ProjectSummary): { label: string; variant: ReturnType<typeof statusVariant> } {
  const latest = project.jobs?.latest_status as JobStatus | null | undefined
  if (latest === 'queued') return { label: 'Queued', variant: statusVariant('Queued') }
  if (latest === 'running') return { label: 'Running', variant: statusVariant('Running') }
  if (latest === 'failed') return { label: 'Failed', variant: statusVariant('Failed') }
  if (latest === 'partial_success') return { label: 'Partial', variant: statusVariant('Partial') }
  if (latest === 'cancelled') return { label: 'Cancelled', variant: statusVariant('Cancelled') }
  if (project.has_video) return { label: 'Rendered', variant: statusVariant('Rendered') }
  if (latest === 'succeeded') return { label: 'Completed', variant: statusVariant('Completed') }
  if (latest === 'error') return { label: 'Error', variant: statusVariant('Error') }
  if (project.scene_count > 0) return { label: 'Draft', variant: statusVariant('Draft') }
  return { label: 'Empty', variant: statusVariant('Empty') }
}

export function ProjectCard({ project }: ProjectCardProps) {
  const navigate = useNavigate()

  const status = projectStatus(project)
  const projectMode = projectModeFromSummary(project)
  const createdLabel = formatProjectDate(project.created_utc || project.updated_utc)

  const target = project.scene_count > 0
    ? `/projects/${encodeURIComponent(project.name)}/scenes`
    : (project.jobs?.counts?.total ?? 0) > 0
      ? `/projects/${encodeURIComponent(project.name)}/queue`
    : `/projects/${encodeURIComponent(project.name)}/brief`
  const thumbnailUrl = projectMediaUrl(project.name, project.thumbnail_path)
  // The server falls back to a video asset (scene clip or final render) when a
  // project has no still images; render those with <video> so the first frame
  // shows instead of a broken <img>.
  const thumbnailIsVideo = /\.(mp4|mov|webm|m4v)$/i.test(project.thumbnail_path ?? '')
  const jobCount = project.jobs?.counts?.total ?? 0

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
        {thumbnailUrl && thumbnailIsVideo ? (
          <video
            src={`${thumbnailUrl}#t=0.1`}
            muted
            playsInline
            preload="metadata"
            aria-label={`${project.name} thumbnail`}
            className="w-full h-full object-cover pointer-events-none"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />
        ) : thumbnailUrl ? (
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
          <Badge variant={status.variant} size="sm">
            {status.label}
          </Badge>
        </div>
        {projectMode.id === 'vertical_short' ? (
          <div className="mt-[var(--space-2)]">
            <Badge variant="active" size="sm">
              {projectMode.badge}
            </Badge>
          </div>
        ) : null}
        <p
          className="text-[var(--text-tertiary)] m-0"
          style={{
            fontSize: 'var(--text-xs)',
            marginTop: 'var(--space-1)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {project.scene_count > 0
            ? `${project.scene_count} ${project.scene_count === 1 ? 'scene' : 'scenes'}`
            : jobCount > 0
              ? `${jobCount} ${jobCount === 1 ? 'job' : 'jobs'}`
              : 'No scenes yet'}
        </p>
        {createdLabel ? (
          <p
            className="text-[var(--text-tertiary)] m-0"
            style={{
              fontSize: '10px',
              marginTop: 'var(--space-1)',
            }}
          >
            Created {createdLabel}
          </p>
        ) : null}
      </div>
    </GlassPanel>
  )
}
