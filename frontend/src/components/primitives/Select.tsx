import { forwardRef, useId, type SelectHTMLAttributes } from 'react'
import { clsx } from 'clsx'

interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  label: string
  options: SelectOption[]
  error?: string
  hint?: string
  placeholder?: string
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  function Select({ label, options, error, hint, placeholder, className, id: idProp, ...rest }, ref) {
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
        <select
          ref={ref}
          id={id}
          aria-invalid={!!error}
          aria-describedby={clsx(error && errorId, hint && hintId) || undefined}
          className={clsx(
            'w-full rounded-[var(--radius-md)] border bg-[var(--surface-stage)] text-[var(--text-primary)]',
            'font-[family-name:var(--font-body)]',
            'outline-none focus-visible:shadow-[var(--focus-ring)]',
            'cursor-pointer transition-colors duration-150',
            'appearance-none',
            error
              ? 'border-[var(--signal-danger)]'
              : 'border-[var(--border-subtle)] hover:border-[var(--border-default)]',
            className,
          )}
          style={{
            padding: `var(--space-2) var(--space-3)`,
            paddingRight: 'var(--space-8)',
            fontSize: 'var(--text-sm)',
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='12' height='12' viewBox='0 0 12 12' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M3 4.5L6 7.5L9 4.5' stroke='%23a8a29e' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
            backgroundRepeat: 'no-repeat',
            backgroundPosition: 'right var(--space-3) center',
          }}
          {...rest}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          ))}
        </select>
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
