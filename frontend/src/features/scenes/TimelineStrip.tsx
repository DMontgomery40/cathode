import { useRef, useState, useCallback } from 'react'
import { clsx } from 'clsx'
import { useUIStore } from '../../stores/ui.ts'
import { handleArrowNav } from '../../design-system/a11y/index.ts'
import type { Scene } from '../../lib/schemas/plan.ts'
import { sceneHasPreview, sceneHasRenderableVisual, sceneVisualUrl } from '../../lib/scene-media.ts'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'

interface TimelineStripProps {
  scenes: Scene[]
  project: string
  renderBackend?: string | null
  panelHeight: number
  layoutMode: 'rail' | 'grid'
  actions?: React.ReactNode
  onReorder: (scenes: Scene[]) => void
  onAddScene: () => void
  onDeleteScene: (uid: string) => void
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function AssetDots({ scene, project, renderBackend }: { scene: Scene; project: string; renderBackend?: string | null }) {
  return (
    <div className="flex items-center gap-[var(--space-1)]" aria-label="Asset status">
      <span
        className={clsx(
          'inline-block rounded-full',
          sceneHasRenderableVisual(project, scene, renderBackend)
            ? 'bg-[var(--signal-success)]'
            : 'bg-[var(--text-tertiary)]',
        )}
        style={{ width: 5, height: 5 }}
        title={sceneHasRenderableVisual(project, scene, renderBackend) ? 'Has visual' : 'No visual'}
      />
      <span
        className={clsx(
          'inline-block rounded-full',
          scene.audio_path
            ? 'bg-[var(--signal-success)]'
            : 'bg-[var(--text-tertiary)]',
        )}
        style={{ width: 5, height: 5 }}
        title={scene.audio_path ? 'Has audio' : 'No audio'}
      />
      <span
        className={clsx(
          'inline-block rounded-full',
          sceneHasPreview(project, scene)
            ? 'bg-[var(--signal-success)]'
            : 'bg-[var(--text-tertiary)]',
        )}
        style={{ width: 5, height: 5 }}
        title={sceneHasPreview(project, scene) ? 'Has preview' : 'No preview'}
      />
    </div>
  )
}

export function TimelineStrip({
  scenes,
  project,
  renderBackend,
  panelHeight,
  layoutMode,
  actions,
  onReorder,
  onAddScene,
  onDeleteScene,
}: TimelineStripProps) {
  const { selectedSceneId, setSelectedScene } = useUIStore()
  const [dragIdx, setDragIdx] = useState<number | null>(null)
  const [dropIdx, setDropIdx] = useState<number | null>(null)
  const cardRefs = useRef<(HTMLButtonElement | null)[]>([])
  const compactRail = layoutMode === 'rail' && panelHeight <= 170
  const cardWidth = Math.round(clamp(panelHeight * (compactRail ? 1.72 : 1.24), 170, 292))
  const thumbHeight = Math.round(
    clamp(
      compactRail ? panelHeight - 30 : panelHeight * 0.42,
      compactRail ? 88 : 56,
      compactRail ? 138 : 112,
    ),
  )
  const cardMinHeight = Math.round(
    clamp(
      compactRail ? thumbHeight + 16 : panelHeight - 26,
      compactRail ? 112 : 98,
      compactRail ? 164 : 188,
    ),
  )

  const handleDragStart = useCallback(
    (e: React.DragEvent, idx: number) => {
      setDragIdx(idx)
      e.dataTransfer.effectAllowed = 'move'
      e.dataTransfer.setData('text/plain', String(idx))
    },
    [],
  )

  const handleDragOver = useCallback(
    (e: React.DragEvent, idx: number) => {
      e.preventDefault()
      e.dataTransfer.dropEffect = 'move'
      setDropIdx(idx)
    },
    [],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent, targetIdx: number) => {
      e.preventDefault()
      if (dragIdx === null || dragIdx === targetIdx) {
        setDragIdx(null)
        setDropIdx(null)
        return
      }
      const next = [...scenes]
      const [moved] = next.splice(dragIdx, 1)
      next.splice(targetIdx, 0, moved)
      onReorder(next)
      setDragIdx(null)
      setDropIdx(null)
    },
    [dragIdx, scenes, onReorder],
  )

  const handleDragEnd = useCallback(() => {
    setDragIdx(null)
    setDropIdx(null)
  }, [])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const items = cardRefs.current.filter(Boolean) as HTMLButtonElement[]
      const curIdx = items.findIndex((el) => el === document.activeElement)
      if (curIdx < 0) return

      if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault()
        const scene = scenes[curIdx]
        if (scene) onDeleteScene(scene.uid)
        return
      }

      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        const scene = scenes[curIdx]
        if (scene) setSelectedScene(scene.uid)
        return
      }

      handleArrowNav(e, items, curIdx, {
        orientation: layoutMode === 'grid' ? 'both' : 'horizontal',
      })
    },
    [layoutMode, scenes, onDeleteScene, setSelectedScene],
  )

  return (
    <GlassPanel
      variant="default"
      padding="sm"
      rounded="lg"
      className={clsx('scene-timeline-strip', compactRail && 'scene-timeline-strip--compact')}
      role="region"
      aria-label="Scene timeline panel"
    >
      <div className="scene-timeline-strip__head">
        <div className="scene-timeline-strip__meta min-w-0">
          <div className="scene-timeline-strip__title-row">
            <div
              className="text-[var(--text-primary)]"
              style={{
                fontSize: 'var(--text-sm)',
                fontWeight: 'var(--weight-medium)',
                fontFamily: 'var(--font-display)',
              }}
            >
              Timeline
            </div>
            {compactRail && (
              <div
                className="text-[var(--text-tertiary)]"
                style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
              >
                {scenes.length} scenes
              </div>
            )}
          </div>
          {!compactRail && (
            <div
              className="scene-timeline-strip__copy text-[var(--text-tertiary)]"
              style={{
                fontSize: 'var(--text-xs)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              Drag to reorder. Stretch for gallery view.
            </div>
          )}
        </div>
        <div className="scene-timeline-strip__actions">
          {actions}
          {!compactRail && (
            <div
              className="rounded-full border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-secondary)]"
              style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
            >
              {scenes.length} scenes
            </div>
          )}
        </div>
      </div>

      <div
        className="scene-timeline-strip__surface"
        data-layout={layoutMode}
        role="listbox"
        aria-label="Scene timeline"
        aria-orientation="horizontal"
        onKeyDown={handleKeyDown}
        style={{ scrollbarWidth: 'thin', paddingBottom: 'var(--space-1)' }}
      >
        {scenes.map((scene, idx) => {
          const thumb = sceneVisualUrl(project, scene)
          const isSelected = selectedSceneId === scene.uid
          const isDragging = dragIdx === idx
          const isDropTarget = dropIdx === idx && dragIdx !== idx

          return (
            <button
              key={scene.uid}
              ref={(el) => { cardRefs.current[idx] = el }}
              role="option"
              aria-selected={isSelected}
              draggable
              onDragStart={(e) => handleDragStart(e, idx)}
              onDragOver={(e) => handleDragOver(e, idx)}
              onDrop={(e) => handleDrop(e, idx)}
              onDragEnd={handleDragEnd}
              onClick={() => setSelectedScene(scene.uid)}
              className={clsx(
                'flex-shrink-0 flex flex-col rounded-[var(--radius-md)] border cursor-pointer',
                'outline-none transition-all duration-[150ms]',
                'focus-visible:shadow-[var(--focus-ring)]',
                'hover:bg-[var(--surface-elevated)]',
                isSelected
                  ? 'border-[var(--border-accent)] shadow-[0_0_8px_rgba(200,169,110,0.2)]'
                  : 'border-[var(--border-subtle)]',
                isDragging && 'opacity-40',
                isDropTarget && 'border-[var(--accent-secondary)] border-dashed',
                'scene-timeline-card',
              )}
              data-layout={layoutMode}
              style={{
                width: layoutMode === 'rail' ? cardWidth : undefined,
                minHeight: cardMinHeight,
                background: isSelected
                  ? 'var(--surface-elevated)'
                  : 'var(--surface-panel-glass)',
              }}
            >
              <div
                className={clsx(
                  'relative w-full overflow-hidden',
                  compactRail ? 'rounded-[var(--radius-md)]' : 'rounded-t-[var(--radius-md)]',
                )}
                style={{ height: thumbHeight, background: 'var(--surface-void)' }}
              >
                {thumb ? (
                  <img
                    src={thumb}
                    alt=""
                    className="h-full w-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center">
                    <span
                      className="text-[var(--text-tertiary)]"
                      style={{ fontSize: 'var(--text-xs)' }}
                    >
                      No visual
                    </span>
                  </div>
                )}
                <span
                  className="absolute top-[var(--space-1)] right-[var(--space-1)] rounded-[var(--radius-sm)] bg-[var(--surface-void)]/80 text-[var(--text-secondary)]"
                  style={{
                    fontSize: '10px',
                    padding: '1px 4px',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  {scene.scene_type ?? 'image'}
                </span>
                {compactRail && (
                  <div className="scene-timeline-card__overlay">
                    <span
                      className="scene-timeline-card__overlay-title"
                      style={{
                        fontSize: 'var(--text-xs)',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      {scene.id != null ? `#${scene.id}` : `#${idx + 1}`}
                      {scene.title ? ` ${scene.title}` : ''}
                    </span>
                    <AssetDots scene={scene} project={project} renderBackend={renderBackend} />
                  </div>
                )}
              </div>

              {!compactRail && (
                <div
                  className="flex flex-col gap-[var(--space-1)] min-w-0"
                  style={{ padding: `var(--space-2) var(--space-2)` }}
                >
                  <div className="flex items-start justify-between gap-[var(--space-2)]">
                    <span
                      className="text-[var(--text-secondary)]"
                      style={{
                        fontSize: 'var(--text-xs)',
                        fontFamily: 'var(--font-mono)',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                      }}
                    >
                      {scene.id != null ? `#${scene.id}` : `#${idx + 1}`}
                      {scene.title ? ` ${scene.title}` : ''}
                    </span>
                    <AssetDots scene={scene} project={project} renderBackend={renderBackend} />
                  </div>
                </div>
              )}
            </button>
          )
        })}

        <button
          onClick={onAddScene}
          className={clsx(
            'flex items-center justify-center rounded-[var(--radius-md)]',
            'border border-dashed border-[var(--border-subtle)]',
            'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]',
            'hover:border-[var(--border-default)] hover:bg-[var(--surface-elevated)]',
            'outline-none focus-visible:shadow-[var(--focus-ring)]',
            'cursor-pointer transition-colors duration-[150ms]',
            'scene-timeline-card',
          )}
          data-layout={layoutMode}
          style={{ width: layoutMode === 'rail' ? 92 : undefined, minHeight: cardMinHeight }}
          aria-label="Add scene"
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          >
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
      </div>
    </GlassPanel>
  )
}
