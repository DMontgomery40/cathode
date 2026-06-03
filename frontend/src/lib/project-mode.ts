import type { ProjectSummary } from './api/projects'
import type { Plan } from './schemas/plan'

export interface ProjectModeSummary {
  id: 'standard' | 'vertical_short'
  label: string
  shortLabel: string
  badge: string
  aspect: string
  frame: string
  locksFps: boolean
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {}
}

function renderFrame(renderProfile: Record<string, unknown>, fallbackAspect: string): { aspect: string; frame: string } {
  const aspect = String(renderProfile.aspect_ratio || fallbackAspect).trim() || fallbackAspect
  const width = Number(renderProfile.width)
  const height = Number(renderProfile.height)
  const frame = Number.isFinite(width) && width > 0 && Number.isFinite(height) && height > 0
    ? `${aspect} ${width}x${height}`
    : aspect
  return { aspect, frame }
}

export function projectModeFromPlan(plan: Plan | null | undefined): ProjectModeSummary {
  const meta = recordValue(plan?.meta)
  const brief = recordValue(meta.brief)
  const renderProfile = recordValue(meta.render_profile)
  const isVerticalShort = brief.short_form_format === 'vertical_short' || meta.pipeline_mode === 'short_form_vertical_v1'
  const { aspect, frame } = renderFrame(renderProfile, isVerticalShort ? '9:16' : '16:9')

  if (isVerticalShort) {
    return {
      id: 'vertical_short',
      label: 'Vertical short',
      shortLabel: 'Short',
      badge: `Vertical short ${frame}`,
      aspect,
      frame,
      locksFps: true,
    }
  }

  return {
    id: 'standard',
    label: 'Standard explainer',
    shortLabel: 'Standard',
    badge: `Standard ${frame}`,
    aspect,
    frame,
    locksFps: false,
  }
}

export function projectModeFromSummary(project: ProjectSummary): ProjectModeSummary {
  const isVerticalShort = project.short_form_format === 'vertical_short' || project.pipeline_mode === 'short_form_vertical_v1'
  const aspect = String(project.render_aspect_ratio || (isVerticalShort ? '9:16' : '16:9'))

  if (isVerticalShort) {
    return {
      id: 'vertical_short',
      label: 'Vertical short',
      shortLabel: 'Short',
      badge: `Vertical short ${aspect}`,
      aspect,
      frame: aspect,
      locksFps: true,
    }
  }

  return {
    id: 'standard',
    label: 'Standard explainer',
    shortLabel: 'Standard',
    badge: `Standard ${aspect}`,
    aspect,
    frame: aspect,
    locksFps: false,
  }
}
