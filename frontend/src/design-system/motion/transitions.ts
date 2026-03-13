export const easings = {
  /** Smooth content entrance */
  enterSoft: 'cubic-bezier(0.22, 1, 0.36, 1)',
  /** Rail/panel slide transitions */
  dockSlide: 'cubic-bezier(0.16, 1, 0.3, 1)',
  /** Subtle focus/attention pulse */
  focusPulse: 'cubic-bezier(0.4, 0, 0.2, 1)',
  /** Timeline scene shifting */
  timelineShift: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
  /** Status indicator settling */
  statusSettle: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
} as const

export const durations = {
  instant: '75ms',
  fast: '150ms',
  normal: '250ms',
  relaxed: '350ms',
  slow: '500ms',
  dramatic: '700ms',
} as const

export const transitions = {
  enterSoft: `${durations.normal} ${easings.enterSoft}`,
  dockSlide: `${durations.relaxed} ${easings.dockSlide}`,
  focusPulse: `${durations.fast} ${easings.focusPulse}`,
  timelineShift: `${durations.normal} ${easings.timelineShift}`,
  statusSettle: `${durations.normal} ${easings.statusSettle}`,
} as const
