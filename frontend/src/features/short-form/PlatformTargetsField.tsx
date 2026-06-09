import { useId } from 'react'
import type { ShortFormOption } from '../../lib/api/hooks.ts'

const FIELD_HELP = 'Platform targets are saved into the short-form brief and request preview for storyboard guidance. They do not create separate exports; the render remains one 9:16 MP4.'

const PLATFORM_DESCRIPTIONS: Record<string, string> = {
  tiktok: 'Adds TikTok as a target. The director biases the hook, caption density, and mobile-safe framing for a fast cold-feed watch.',
  'instagram-reels': 'Adds Instagram Reels as a target. The director biases polish, readability, and payoff clarity for Reels.',
  'youtube-shorts': 'Adds YouTube Shorts as a target. The director biases context, retention, and payoff clarity for Shorts.',
}

function platformTargetDescription(option: ShortFormOption): string {
  return option.description || PLATFORM_DESCRIPTIONS[option.value] || FIELD_HELP
}

function updatePlatformTargets(values: string[] | undefined, value: string, checked: boolean): string[] {
  const current = new Set(values ?? [])
  if (checked) {
    current.add(value)
  } else if (current.size > 1) {
    current.delete(value)
  }
  return [...current]
}

interface PlatformTargetsFieldProps {
  options: ShortFormOption[]
  value: string[] | undefined
  onChange: (nextValue: string[]) => void
}

export function PlatformTargetsField({ options, value, onChange }: PlatformTargetsFieldProps) {
  const helpId = useId()
  const selected = value ?? []

  return (
    <div>
      <div className="flex items-center gap-[var(--space-2)]">
        <p className="workspace-eyebrow m-0">Platforms</p>
        <span
          aria-label={FIELD_HELP}
          className="inline-flex h-[18px] w-[18px] cursor-help select-none items-center justify-center rounded-full border border-[var(--border-subtle)] text-[var(--text-tertiary)]"
          role="img"
          style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}
          title={FIELD_HELP}
        >
          ?
        </span>
      </div>
      <p id={helpId} className="workspace-panel-copy m-0 mt-[var(--space-1)]">
        {FIELD_HELP}
      </p>
      <div className="mt-[var(--space-2)] flex flex-wrap gap-[var(--space-3)]">
        {options.map((platform) => {
          const checked = selected.includes(platform.value)
          const isLastSelected = checked && selected.length <= 1
          const description = platformTargetDescription(platform)
          const title = isLastSelected
            ? `${description} At least one platform target must remain selected.`
            : description

          return (
            <label
              key={platform.value}
              className="flex items-center gap-[var(--space-2)] text-[var(--text-secondary)]"
              style={{ fontSize: 'var(--text-sm)' }}
              title={title}
            >
              <input
                type="checkbox"
                aria-describedby={helpId}
                aria-label={platform.label}
                checked={checked}
                disabled={isLastSelected}
                onChange={(event) => onChange(updatePlatformTargets(selected, platform.value, event.target.checked))}
              />
              <span>{platform.label}</span>
              <span
                aria-hidden="true"
                className="inline-flex h-[16px] w-[16px] cursor-help select-none items-center justify-center rounded-full border border-[var(--border-subtle)] text-[var(--text-tertiary)]"
                style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}
                title={title}
              >
                ?
              </span>
            </label>
          )
        })}
      </div>
    </div>
  )
}
