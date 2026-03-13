import { useCallback, useMemo, useRef, useState } from 'react'
import { clsx } from 'clsx'
import { DropZone as AriaDropZone } from 'react-aria-components'
import { Button } from './Button.tsx'
import {
  acceptedFileTypesForPicker,
  filesFromDropItems,
  splitAcceptedFiles,
  uploadRejectionMessage,
} from '../../lib/uploads.ts'

interface DropZoneProps {
  label: string
  accept?: string
  multiple?: boolean
  onFiles: (files: File[]) => void
  hint?: string
  disabled?: boolean
  className?: string
  actionLabel?: string
  browseLabel?: string
  pending?: boolean
  error?: string | null
  testId?: string
}

export function DropZone({
  label,
  accept,
  multiple = true,
  onFiles,
  hint,
  disabled,
  className,
  actionLabel = 'Choose files',
  browseLabel,
  pending = false,
  error,
  testId,
}: DropZoneProps) {
  const [errorText, setErrorText] = useState('')
  const inputRef = useRef<HTMLInputElement | null>(null)
  const acceptedFileTypes = useMemo(() => acceptedFileTypesForPicker(accept) ?? [], [accept])
  const acceptAttr = acceptedFileTypes.length > 0 ? acceptedFileTypes.join(',') : undefined

  const commitFiles = useCallback((incoming: File[]) => {
    const { accepted, rejected } = splitAcceptedFiles(incoming, accept)
    if (rejected.length > 0) {
      setErrorText(uploadRejectionMessage(rejected, accept))
    } else {
      setErrorText('')
    }

    if (accepted.length > 0) {
      onFiles(accepted)
    }
  }, [accept, onFiles])

  const handleSelection = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) {
      return
    }
    commitFiles(Array.from(files))
  }, [commitFiles])

  const handleDrop = useCallback(async (event: { items: Iterable<{ kind?: string; getFile?: () => Promise<File> }> }) => {
    const files = await filesFromDropItems(event.items)
    if (files.length > 0) {
      commitFiles(files)
    }
  }, [commitFiles])

  const activeError = error ?? errorText

  return (
    <AriaDropZone
      aria-label={label}
      data-testid={testId}
      isDisabled={disabled || pending}
      onDrop={handleDrop}
      className={({ isDropTarget, isFocusVisible }) => clsx(
        'flex flex-col items-center justify-center gap-[var(--space-3)]',
        'rounded-[var(--radius-lg)] border-2 border-dashed',
        'transition-colors duration-150',
        isDropTarget
          ? 'border-[var(--accent-primary)] bg-[var(--accent-primary-muted)]'
          : 'border-[var(--border-subtle)] bg-[var(--surface-stage)] hover:border-[var(--border-default)]',
        isFocusVisible && 'shadow-[var(--focus-ring)]',
        (disabled || pending) && 'opacity-50',
        className,
      )}
      style={{ padding: `var(--space-6) var(--space-4)` }}
    >
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-[var(--text-tertiary)]"
        aria-hidden="true"
      >
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>

      <div className="flex flex-col items-center gap-[var(--space-1)] text-center">
        <span
          className="font-[family-name:var(--font-body)] text-[var(--text-secondary)]"
          style={{ fontSize: 'var(--text-sm)' }}
        >
          {pending ? 'Uploading files…' : label}
        </span>
        {hint && (
          <span
            className="text-[var(--text-tertiary)]"
            style={{ fontSize: 'var(--text-xs)' }}
          >
            {hint}
          </span>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={acceptAttr}
        multiple={multiple}
        tabIndex={-1}
        aria-hidden="true"
        className="sr-only"
        onChange={(event) => {
          handleSelection(event.currentTarget.files)
          event.currentTarget.value = ''
        }}
      />

      <Button
        type="button"
        variant="secondary"
        size="sm"
        disabled={disabled || pending}
        onClick={() => {
          if (!disabled && !pending) {
            inputRef.current?.click()
          }
        }}
      >
        {browseLabel || actionLabel}
      </Button>

      <span className="sr-only">You can also paste files here.</span>

      {activeError && (
        <p
          role="alert"
          className="m-0 text-center text-[var(--signal-warning)]"
          style={{ fontSize: 'var(--text-xs)' }}
        >
          {activeError}
        </p>
      )}
    </AriaDropZone>
  )
}
