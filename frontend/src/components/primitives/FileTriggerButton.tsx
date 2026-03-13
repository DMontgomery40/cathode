import { useRef } from 'react'
import { Button } from './Button'
import { describeRejectedFiles, getAcceptedFileTypes, splitAcceptedFiles } from '../../lib/uploads'

interface FileTriggerButtonProps {
  accept?: string
  multiple?: boolean
  disabled?: boolean
  onFiles: (files: File[]) => void
  onError?: (message: string | null) => void
  children: React.ReactNode
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

export function FileTriggerButton({
  accept,
  multiple = false,
  disabled,
  onFiles,
  onError,
  children,
  variant = 'secondary',
  size = 'sm',
}: FileTriggerButtonProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const acceptedFileTypes = getAcceptedFileTypes(accept) ?? []
  const acceptAttr = acceptedFileTypes.length > 0 ? acceptedFileTypes.join(',') : undefined

  const handleSelection = (files: FileList | null) => {
    const incoming = Array.from(files ?? [])
    const { accepted, rejected } = splitAcceptedFiles(incoming, acceptedFileTypes, { multiple })
    onError?.(describeRejectedFiles(rejected, acceptedFileTypes))
    if (accepted.length > 0) {
      onFiles(accepted)
    }
  }

  return (
    <>
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
        variant={variant}
        size={size}
        disabled={disabled}
        onClick={() => {
          if (!disabled) {
            inputRef.current?.click()
          }
        }}
      >
        {children}
      </Button>
    </>
  )
}
