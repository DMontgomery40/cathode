import { useRef, useState, useCallback } from 'react'
import { clsx } from 'clsx'
import type { Scene } from '../../lib/schemas/plan.ts'
import { scenePreviewUrl, sceneVisualUrl } from '../../lib/scene-media.ts'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { Button } from '../../components/primitives/Button.tsx'
import { describeRejectedFiles, splitAcceptedFiles } from '../../lib/uploads.ts'

interface MediaStageProps {
  scene: Scene | null
  project: string
  actions?: React.ReactNode
  onUpload: (file: File) => void
  uploadPending?: boolean
  uploadError?: string | null
  compactActions?: boolean
}

export function MediaStage({ scene, project, actions, onUpload, uploadPending, uploadError, compactActions }: MediaStageProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [speed, setSpeed] = useState(1)
  const [dragOver, setDragOver] = useState(false)
  const [localUploadError, setLocalUploadError] = useState<string | null>(null)

  const commitFiles = useCallback((incoming: File[]) => {
    const { accepted, rejected } = splitAcceptedFiles(incoming, 'image/*,video/*', { multiple: false })
    setLocalUploadError(describeRejectedFiles(rejected, 'image/*,video/*'))
    if (accepted[0]) {
      onUpload(accepted[0])
    }
  }, [onUpload])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      if (uploadPending) return
      commitFiles(Array.from(e.dataTransfer.files))
    },
    [commitFiles, uploadPending],
  )

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (uploadPending) return
      commitFiles(Array.from(e.target.files ?? []))
      e.target.value = ''
    },
    [commitFiles, uploadPending],
  )

  const togglePlay = useCallback(() => {
    const v = videoRef.current
    if (!v) return
    if (v.paused) {
      void v.play()
      setPlaying(true)
    } else {
      v.pause()
      setPlaying(false)
    }
  }, [])

  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const v = videoRef.current
    if (!v) return
    const t = Number(e.target.value)
    v.currentTime = t
    setCurrentTime(t)
  }, [])

  const handleSpeed = useCallback((s: number) => {
    setSpeed(s)
    if (videoRef.current) videoRef.current.playbackRate = s
  }, [])

  const formatTime = (t: number) => {
    const m = Math.floor(t / 60)
    const s = Math.floor(t % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  const isMotionScene = scene?.scene_type === 'motion'
  const visualUrl = sceneVisualUrl(project, scene)
  const previewUrl = scenePreviewUrl(project, scene)
  const hasVideoVisual = scene
    ? (typeof scene.video_exists === 'boolean' ? scene.video_exists : Boolean(scene.video_path))
    : false
  const hasImageVisual = scene
    ? (typeof scene.image_exists === 'boolean' ? scene.image_exists : Boolean(scene.image_path))
    : false
  const stageLabel = scene?.scene_type === 'video' || scene?.scene_type === 'motion' ? 'Motion stage' : 'Visual stage'
  const uploadHintId = !scene || !visualUrl ? 'media-stage-hint' : undefined
  const activeUploadError = uploadError ?? localUploadError

  return (
    <GlassPanel
      variant="floating"
      padding="sm"
      rounded="xl"
      className="flex h-full min-h-0 flex-col overflow-hidden"
      role="region"
      aria-label="Media stage"
    >
      <input
        ref={fileRef}
        type="file"
        accept="image/*,video/*"
        className="hidden"
        onChange={handleFileSelect}
      />

      <div className="flex items-center justify-between gap-[var(--space-3)] px-[var(--space-2)] pb-[var(--space-3)]">
        <div className="min-w-0">
          <div
            className="text-[var(--text-primary)]"
            style={{
              fontSize: 'var(--text-sm)',
              fontWeight: 'var(--weight-medium)',
              fontFamily: 'var(--font-display)',
            }}
          >
            {stageLabel}
          </div>
          <div
            className="text-[var(--text-tertiary)]"
            style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)' }}
          >
            {scene ? 'Media-first preview surface for the selected scene.' : 'Drop media onto the stage or open it from the inspector.'}
          </div>
        </div>
        <div className="flex items-center gap-[var(--space-2)]">
          {actions}
          <Button
            type="button"
            variant={compactActions ? 'ghost' : 'secondary'}
            size="sm"
            disabled={uploadPending}
            onClick={() => fileRef.current?.click()}
            aria-label={uploadPending ? 'Uploading media' : 'Upload media'}
            title={uploadPending ? 'Uploading media' : 'Upload media'}
          >
            {compactActions ? (
              <>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M7 10.75V3.5" />
                  <path d="M4.5 6L7 3.5L9.5 6" />
                  <path d="M3 11.5H11" />
                </svg>
                <span className="sr-only">{uploadPending ? 'Uploading…' : 'Upload media'}</span>
              </>
            ) : (
              uploadPending ? 'Uploading…' : 'Upload media'
            )}
          </Button>
          {scene && (
            <div
              className="rounded-full border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-secondary)]"
              style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
            >
              {scene.scene_type ?? 'image'}
            </div>
          )}
        </div>
      </div>

      <div
        className={clsx(
          'relative flex min-h-0 flex-1 flex-col rounded-[var(--radius-xl)] border border-[var(--border-subtle)] bg-[var(--surface-void)]',
          'overflow-hidden',
          dragOver && 'border-[var(--accent-secondary)] border-dashed',
        )}
        tabIndex={!scene || !visualUrl ? 0 : -1}
        aria-describedby={uploadHintId}
        onDragOver={(e) => {
          e.preventDefault()
          if (uploadPending) return
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onKeyDown={(event) => {
          if ((event.key === 'Enter' || event.key === ' ') && !visualUrl) {
            event.preventDefault()
            fileRef.current?.click()
          }
        }}
        onClick={() => {
          if (!uploadPending && !visualUrl && !isMotionScene) fileRef.current?.click()
        }}
      >
        {dragOver && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-[var(--surface-void)]/82 backdrop-blur-[var(--glass-blur)]">
            <span
              className="text-[var(--text-secondary)]"
              style={{ fontSize: 'var(--text-lg)', fontFamily: 'var(--font-display)' }}
            >
              Drop file to replace the stage
            </span>
          </div>
        )}

        {!scene && (
          <div className="flex h-full flex-col items-center justify-center gap-[var(--space-3)] px-[var(--space-6)] text-center">
            <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-sm)' }}>
              Select a scene to preview
            </span>
          </div>
        )}

        {scene && !visualUrl && !isMotionScene && (
          <div className="flex h-full cursor-pointer flex-col items-center justify-center gap-[var(--space-3)] px-[var(--space-6)] text-center">
            <svg
              width="40"
              height="40"
              viewBox="0 0 40 40"
              fill="none"
              stroke="var(--text-tertiary)"
              strokeWidth="1.5"
              strokeLinecap="round"
            >
              <rect x="4" y="8" width="32" height="24" rx="3" />
              <path d="M14 28L18 20L22 24L26 18L32 28" />
              <circle cx="14" cy="16" r="2" />
            </svg>
            <span className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-sm)' }}>
              {uploadPending ? 'Uploading media…' : 'Drop an image or video here, or use the upload button'}
            </span>
            <span
              id="media-stage-hint"
              className="text-[var(--text-tertiary)]"
              style={{ fontSize: 'var(--text-xs)', maxWidth: '24rem' }}
            >
              This drop zone also works from the keyboard and respects image/video file types.
            </span>
          </div>
        )}

        {scene && isMotionScene && !previewUrl && (
          <div className="flex h-full flex-col justify-between px-[var(--space-6)] py-[var(--space-6)]">
            <div className="flex flex-col gap-[var(--space-3)]">
              <span
                className="text-[var(--text-tertiary)]"
                style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em', textTransform: 'uppercase' }}
              >
                Motion template
              </span>
              <div
                className="rounded-[var(--radius-xl)] border border-[var(--border-subtle)] bg-[linear-gradient(135deg,rgba(255,150,110,0.18),rgba(32,56,92,0.28))]"
                style={{ padding: 'var(--space-6)' }}
              >
                <div
                  className="text-[var(--text-primary)] font-[family-name:var(--font-display)]"
                  style={{ fontSize: 'var(--text-xl)', lineHeight: 'var(--leading-tight)' }}
                >
                  {scene.motion?.props?.headline as string || scene.title || 'Motion scene'}
                </div>
                <div
                  className="mt-[var(--space-3)] text-[var(--text-secondary)]"
                  style={{ fontSize: 'var(--text-sm)', maxWidth: '38rem' }}
                >
                  {scene.motion?.props?.body as string || scene.narration || 'Generate a preview to see the motion composition with the current template and audio timing.'}
                </div>
              </div>
            </div>
            <div className="text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
              Motion scenes preview through Remotion. Choose a template in the inspector, then generate a preview.
            </div>
          </div>
        )}

        {activeUploadError && (
          <div
            className="absolute left-[var(--space-4)] right-[var(--space-4)] top-[var(--space-4)] z-10 rounded-[var(--radius-md)] border border-[rgba(200,90,90,0.25)] bg-[rgba(200,90,90,0.12)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--signal-danger)]"
            style={{ fontSize: 'var(--text-xs)' }}
            role="alert"
          >
            {activeUploadError}
          </div>
        )}

        {scene && hasImageVisual && !hasVideoVisual && !isMotionScene && visualUrl && (
          <div className="flex min-h-0 flex-1 items-center justify-center p-[var(--space-4)]">
            <img
              src={visualUrl ?? undefined}
              alt={scene.title || 'Scene image'}
              className="max-h-full max-w-full object-contain"
            />
          </div>
        )}

        {scene && (hasVideoVisual || previewUrl) && (
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex min-h-0 flex-1 items-center justify-center p-[var(--space-4)] pb-[var(--space-3)]">
              <video
                ref={videoRef}
                src={previewUrl ?? visualUrl ?? undefined}
                className="max-h-full max-w-full object-contain"
                onTimeUpdate={() => setCurrentTime(videoRef.current?.currentTime ?? 0)}
                onLoadedMetadata={() => setDuration(videoRef.current?.duration ?? 0)}
                onEnded={() => setPlaying(false)}
              />
            </div>

            <div
              className="flex items-center gap-[var(--space-3)] border-t border-[var(--border-subtle)] bg-[var(--surface-overlay)]/72"
              style={{ padding: `var(--space-3) var(--space-4)` }}
            >
              <button
                onClick={togglePlay}
                className="rounded-[var(--radius-sm)] p-[var(--space-1)] text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                aria-label={playing ? 'Pause' : 'Play'}
              >
                {playing ? (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <rect x="3" y="2" width="4" height="12" rx="1" />
                    <rect x="9" y="2" width="4" height="12" rx="1" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M4 2L14 8L4 14V2Z" />
                  </svg>
                )}
              </button>
              <input
                type="range"
                min={0}
                max={duration || 1}
                step={0.1}
                value={currentTime}
                onChange={handleSeek}
                className="flex-1 accent-[var(--accent-primary)]"
                aria-label="Seek"
              />
              <span
                className="text-[var(--text-secondary)] font-[family-name:var(--font-mono)]"
                style={{ fontSize: 'var(--text-xs)', whiteSpace: 'nowrap' }}
              >
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>
              <select
                value={speed}
                onChange={(e) => handleSpeed(Number(e.target.value))}
                className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] text-[var(--text-secondary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                style={{ fontSize: 'var(--text-xs)', padding: '2px 4px' }}
                aria-label="Playback speed"
              >
                <option value={0.5}>0.5x</option>
                <option value={1}>1x</option>
                <option value={1.5}>1.5x</option>
                <option value={2}>2x</option>
              </select>
            </div>
          </div>
        )}

        {scene && visualUrl && (
          <div
            className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-[var(--surface-void)]/88 via-[var(--surface-void)]/45 to-transparent"
            style={{
              padding: `var(--space-8) var(--space-4) var(--space-4)`,
              bottom: hasVideoVisual || previewUrl ? '60px' : '0',
            }}
          >
            {scene.title && (
              <div
                className="text-[var(--text-primary)] font-[family-name:var(--font-display)]"
                style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)' }}
              >
                {scene.title}
              </div>
            )}
            {scene.narration && (
              <div
                className="text-[var(--text-secondary)]"
                style={{
                  fontSize: 'var(--text-xs)',
                  marginTop: 'var(--space-1)',
                  maxWidth: '44rem',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                }}
              >
                {scene.narration}
              </div>
            )}
          </div>
        )}
      </div>
    </GlassPanel>
  )
}
