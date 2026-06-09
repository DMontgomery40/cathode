type FallbackRenderScene = {
  uid: string
  sceneType: 'image' | 'video' | 'motion'
  title: string
  narration: string
  onScreenText: string[]
  durationInFrames: number
  motion?: {
    templateId?: string
    props?: Record<string, unknown>
  }
}

type FallbackRenderProps = {
  width: number
  height: number
  fps: number
  textRenderMode: string
  totalDurationInFrames: number
  scenes: FallbackRenderScene[]
}

export const FALLBACK_PROPS = {
  width: 1664,
  height: 928,
  fps: 24,
  textRenderMode: 'visual_authored',
  totalDurationInFrames: 120,
  scenes: [
    {
      uid: 'fallback',
      sceneType: 'motion',
      title: 'betTube Studio Motion',
      narration: 'Fallback motion scene',
      onScreenText: ['Fallback motion scene'],
      durationInFrames: 120,
      motion: {
        templateId: 'kinetic_title',
        props: {
          headline: 'betTube Studio Motion',
          body: 'Fallback motion scene',
          kicker: 'Remotion',
          bullets: ['Briefs', 'Assets', 'Render'],
          accent: '',
        },
      },
    },
  ],
} satisfies FallbackRenderProps
