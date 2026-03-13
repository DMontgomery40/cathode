import { forwardRef, useId, type InputHTMLAttributes } from 'react'
import { clsx } from 'clsx'

interface SliderProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'size'> {
  label: string
  error?: string
  displayValue?: string
}

export const Slider = forwardRef<HTMLInputElement, SliderProps>(
  function Slider({ label, error, displayValue, className, id: idProp, ...rest }, ref) {
    const autoId = useId()
    const id = idProp ?? autoId
    const errorId = `${id}-error`

    return (
      <div className="flex flex-col gap-[var(--space-1)]">
        <div className="flex items-center justify-between">
          <label
            htmlFor={id}
            className="font-[family-name:var(--font-body)] text-[var(--text-secondary)]"
            style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)' }}
          >
            {label}
          </label>
          {displayValue != null && (
            <span
              className="font-[family-name:var(--font-mono)] text-[var(--text-primary)]"
              style={{ fontSize: 'var(--text-sm)' }}
              aria-hidden="true"
            >
              {displayValue}
            </span>
          )}
        </div>
        <input
          ref={ref}
          id={id}
          type="range"
          aria-invalid={!!error}
          aria-describedby={error ? errorId : undefined}
          className={clsx(
            'w-full cursor-pointer accent-[var(--accent-primary)]',
            'outline-none focus-visible:shadow-[var(--focus-ring)] rounded-[var(--radius-sm)]',
            className,
          )}
          style={{ height: 6 }}
          {...rest}
        />
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
