import { useCallback } from 'react'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { DropZone } from '../../components/primitives/DropZone.tsx'
import { useUploadFootage } from '../../lib/api/hooks.ts'
import { getApiErrorMessage } from '../../lib/api/errors.ts'

interface FootageEntry {
  id?: string
  label?: string
  kind?: string
  path?: string
  review_status?: string
}

interface FootageUploadProps {
  project: string
  footageManifest?: FootageEntry[]
  footageSummary?: string | null
}

export function FootageUpload({ project, footageManifest = [], footageSummary }: FootageUploadProps) {
  const upload = useUploadFootage(project)

  const handleFiles = useCallback((files: File[]) => {
    upload.mutate(files)
  }, [upload])

  const isNew = project === 'new'

  return (
    <GlassPanel variant="default" padding="lg" rounded="lg">
      <h3
        className="font-[family-name:var(--font-display)] text-[var(--text-primary)] m-0"
        style={{
          fontSize: 'var(--text-lg)',
          fontWeight: 'var(--weight-semibold)',
          marginBottom: 'var(--space-4)',
        }}
      >
        Footage Library
      </h3>

      <DropZone
        label={isNew ? 'Save project first to upload clips or stills' : 'Drop clips or stills here for the live-demo / mixed-media path'}
        accept="video/*,image/*"
        onFiles={handleFiles}
        disabled={isNew || upload.isPending}
        pending={upload.isPending}
        error={upload.error ? getApiErrorMessage(upload.error, 'Footage upload failed.') : null}
        browseLabel="Browse footage"
        hint="MP4, MOV, WebM, PNG, JPG, or WebP"
        testId="brief-footage-dropzone"
      />

      {footageManifest.length > 0 && (
        <div className="mt-[var(--space-4)] flex flex-col gap-[var(--space-2)]">
          {footageManifest.map((entry, index) => (
            <div
              key={entry.id ?? `${entry.path ?? 'footage'}-${index}`}
              className="flex items-center justify-between gap-[var(--space-3)] rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-3)] py-[var(--space-2)]"
            >
              <div className="min-w-0">
                <div className="truncate text-[var(--text-primary)]" style={{ fontSize: 'var(--text-sm)' }}>
                  {entry.label || entry.id || entry.path || 'Footage'}
                </div>
                <div className="truncate text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)' }}>
                  {entry.kind || 'reference'}
                </div>
              </div>
              <span
                className="rounded-full border border-[var(--border-subtle)] bg-[var(--surface-panel-glass)] px-[var(--space-2)] py-[var(--space-1)] text-[var(--text-secondary)]"
                style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}
              >
                {entry.review_status || 'accept'}
              </span>
            </div>
          ))}
        </div>
      )}

      {footageSummary && (
        <p
          className="text-[var(--text-secondary)] m-0"
          style={{
            fontSize: 'var(--text-sm)',
            marginTop: 'var(--space-3)',
            lineHeight: 'var(--leading-normal)',
          }}
        >
          {footageSummary}
        </p>
      )}
    </GlassPanel>
  )
}
