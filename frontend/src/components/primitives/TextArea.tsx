import { forwardRef, useId, type TextareaHTMLAttributes } from 'react'
import { clsx } from 'clsx'

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string
  error?: string
  hint?: string
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  function TextArea({ label, error, hint, className, id: idProp, rows = 4, ...rest }, ref) {
    const autoId = useId()
    const id = idProp ?? autoId
    const errorId = `${id}-error`
    const hintId = `${id}-hint`

    return (
      <div className="flex flex-col gap-[var(--space-1)]">
        <label
          htmlFor={id}
          className="font-[family-name:var(--font-body)] text-[var(--text-secondary)]"
          style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)' }}
        >
          {label}
        </label>
        <textarea
          ref={ref}
          id={id}
          rows={rows}
          aria-invalid={!!error}
          aria-describedby={clsx(error && errorId, hint && hintId) || undefined}
          className={clsx(
            'w-full rounded-[var(--radius-md)] border bg-[var(--surface-stage)] text-[var(--text-primary)]',
            'font-[family-name:var(--font-body)] placeholder:text-[var(--text-tertiary)]',
            'outline-none focus-visible:shadow-[var(--focus-ring)]',
            'resize-y transition-colors duration-150',
            error
              ? 'border-[var(--signal-danger)]'
              : 'border-[var(--border-subtle)] hover:border-[var(--border-default)]',
            className,
          )}
          style={{
            padding: `var(--space-2) var(--space-3)`,
            fontSize: 'var(--text-sm)',
          }}
          {...rest}
        />
        {hint && !error && (
          <p
            id={hintId}
            className="text-[var(--text-tertiary)] m-0"
            style={{ fontSize: 'var(--text-xs)' }}
          >
            {hint}
          </p>
        )}
        {error && (
          <p
            id={errorId}
            role="alert"
            className="text-[var(--signal-danger)] m-0"
            style={{ fontSize: 'var(--text-xs)' }}
          >
            {error}
          </p>
        )}
      </div>
    )
  },
)
