import { useCallback } from 'react'
import { GlassPanel } from '../../components/primitives/GlassPanel.tsx'
import { DropZone } from '../../components/primitives/DropZone.tsx'
import { useUploadStyleRefs } from '../../lib/api/hooks.ts'
import { getApiErrorMessage } from '../../lib/api/errors.ts'
import { projectMediaUrl } from '../../lib/media-url.ts'

interface StyleRefUploadProps {
  project: string
  styleRefs?: string[]
  styleSummary?: string | null
}

export function StyleRefUpload({ project, styleRefs = [], styleSummary }: StyleRefUploadProps) {
  const upload = useUploadStyleRefs(project)

  const handleFiles = useCallback(
    (files: File[]) => {
      upload.mutate(files)
    },
    [upload],
  )

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
        Style References
      </h3>

      <DropZone
        label={isNew ? 'Save project first to upload style references' : 'Drop images here or click to upload'}
        accept="image/*"
        onFiles={handleFiles}
        disabled={isNew || upload.isPending}
        pending={upload.isPending}
        error={upload.error ? getApiErrorMessage(upload.error, 'Style reference upload failed.') : null}
        browseLabel="Browse style refs"
        hint="PNG, JPG, or WebP"
        testId="brief-style-dropzone"
      />

      {styleRefs.length > 0 && (
        <div
          className="grid grid-cols-3 gap-[var(--space-2)]"
          style={{ marginTop: 'var(--space-4)' }}
        >
          {styleRefs.map((ref, i) => (
            <img
              key={i}
              src={projectMediaUrl(project, ref) ?? undefined}
              alt={`Style reference ${i + 1}`}
              className="w-full aspect-square object-cover rounded-[var(--radius-md)] border border-[var(--border-subtle)]"
            />
          ))}
        </div>
      )}

      {styleSummary && (
        <p
          className="text-[var(--text-secondary)] m-0"
          style={{
            fontSize: 'var(--text-sm)',
            marginTop: 'var(--space-3)',
            lineHeight: 'var(--leading-normal)',
          }}
        >
          {styleSummary}
        </p>
      )}
    </GlassPanel>
  )
}
