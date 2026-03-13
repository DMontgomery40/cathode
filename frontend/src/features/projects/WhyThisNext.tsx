import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { Badge } from '../../components/primitives/Badge.tsx'
import type { Plan } from '../../lib/schemas/plan.ts'
import { hasProjectMediaPath } from '../../lib/media-url.ts'
import { sceneHasPreview, sceneHasRenderableVisual } from '../../lib/scene-media.ts'

interface WhyThisNextProps {
  plan: Plan | undefined
}

export function WhyThisNext({ plan }: WhyThisNextProps) {
  if (!plan || !plan.scenes.length) {
    return null
  }

  const scenes = plan.scenes
  const projectName = typeof plan.meta?.project_name === 'string' ? plan.meta.project_name : ''
  const renderBackend = typeof plan.meta?.render_profile === 'object' && plan.meta.render_profile
    ? String((plan.meta.render_profile as Record<string, unknown>).render_backend || 'ffmpeg')
    : 'ffmpeg'
  const missingImages = scenes.filter((s) => !sceneHasRenderableVisual(projectName, s, renderBackend)).length
  const missingAudio = scenes.filter((s) => !hasProjectMediaPath(projectName, s.audio_path)).length
  const missingPreviews = scenes.filter((s) => !sceneHasPreview(projectName, s)).length
  const hasVideo = hasProjectMediaPath(projectName, typeof plan.meta?.video_path === 'string' ? plan.meta.video_path : null)

  const items: { label: string; variant: 'success' | 'warning' | 'active' | 'default' }[] = []

  if (missingImages > 0) {
    items.push({ label: `${missingImages} scene${missingImages > 1 ? 's' : ''} need visuals`, variant: 'warning' })
  } else {
    items.push({ label: 'All scene visuals ready', variant: 'success' })
  }

  if (missingAudio > 0) {
    items.push({ label: `${missingAudio} scene${missingAudio > 1 ? 's' : ''} need audio`, variant: 'warning' })
  } else {
    items.push({ label: 'All audio generated', variant: 'success' })
  }

  if (missingPreviews > 0 && missingImages === 0 && missingAudio === 0) {
    items.push({ label: `${missingPreviews} scene${missingPreviews > 1 ? 's' : ''} need previews`, variant: 'active' })
  }

  if (missingImages === 0 && missingAudio === 0) {
    if (hasVideo) {
      items.push({ label: 'Video rendered', variant: 'success' })
    } else {
      items.push({ label: 'Ready to render', variant: 'active' })
    }
  }

  return (
    <GlassPanel variant="default" padding="lg" rounded="lg">
      <h3
        className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0"
        style={{
          fontSize: 'var(--text-lg)',
          fontWeight: 'var(--weight-semibold)',
          marginBottom: 'var(--space-3)',
        }}
      >
        Status
      </h3>
      <ul className="list-none p-0 m-0 flex flex-col gap-[var(--space-2)]">
        {items.map((item, i) => (
          <li key={i} className="flex items-center gap-[var(--space-2)]">
            <Badge variant={item.variant} size="sm">
              {item.label}
            </Badge>
          </li>
        ))}
      </ul>
    </GlassPanel>
  )
}
