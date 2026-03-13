import React from 'react'
import {
  AbsoluteFill,
  Audio,
  Composition,
  Freeze,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  registerRoot,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion'

type MotionTemplateId = 'kinetic_title' | 'bullet_stack' | 'quote_focus'

type RemotionScene = {
  uid: string
  sceneType: 'image' | 'video' | 'motion'
  title: string
  narration: string
  onScreenText: string[]
  durationInFrames: number
  audioUrl?: string | null
  imageUrl?: string | null
  videoUrl?: string | null
  trimBeforeFrames?: number
  trimAfterFrames?: number
  playbackRate?: number
  holdFrames?: number
  playFrames?: number
  motion?: {
    templateId?: MotionTemplateId | string
    props?: {
      headline?: string
      body?: string
      kicker?: string
      bullets?: string[]
      accent?: string
    }
    rationale?: string
  }
}

type CathodeRenderProps = {
  width?: number
  height?: number
  fps?: number
  totalDurationInFrames?: number
  scenes?: RemotionScene[]
}

const FALLBACK_PROPS: Required<CathodeRenderProps> = {
  width: 1664,
  height: 928,
  fps: 24,
  totalDurationInFrames: 120,
  scenes: [
    {
      uid: 'fallback',
      sceneType: 'motion',
      title: 'Cathode Motion',
      narration: 'Fallback motion scene',
      onScreenText: ['Fallback motion scene'],
      durationInFrames: 120,
      motion: {
        templateId: 'kinetic_title',
        props: {
          headline: 'Cathode Motion',
          body: 'Fallback motion scene',
          kicker: 'Remotion',
          bullets: ['Prompts', 'Agents', 'Render'],
          accent: '',
        },
      },
    },
  ],
}

const shellStyle: React.CSSProperties = {
  background: 'radial-gradient(circle at 20% 18%, rgba(255,144,96,0.22), transparent 38%), linear-gradient(135deg, #05070d 0%, #0d1320 52%, #17151e 100%)',
}

const chromeStyle: React.CSSProperties = {
  position: 'absolute',
  inset: 0,
  backgroundImage:
    'linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)',
  backgroundSize: '48px 48px',
  maskImage: 'linear-gradient(to bottom, rgba(0,0,0,0.7), transparent 88%)',
}

function FrameShell({ children }: { children: React.ReactNode }) {
  return (
    <AbsoluteFill style={shellStyle}>
      <AbsoluteFill style={chromeStyle} />
      <AbsoluteFill style={{ inset: 28, border: '1px solid rgba(255,255,255,0.08)', borderRadius: 28, overflow: 'hidden' }}>
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  )
}

function KineticTitleTemplate({
  headline,
  body,
  kicker,
}: {
  headline: string
  body: string
  kicker: string
}) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const reveal = spring({
    frame,
    fps,
    config: {
      damping: 22,
      stiffness: 110,
      mass: 0.8,
    },
  })

  return (
    <AbsoluteFill
      style={{
        padding: 88,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        color: '#fff7f0',
      }}
    >
      <div
        style={{
          alignSelf: 'flex-start',
          padding: '10px 16px',
          borderRadius: 999,
          background: 'rgba(255,255,255,0.08)',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          fontSize: 22,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
        }}
      >
        {kicker}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: '72%' }}>
        <div
          style={{
            fontFamily: 'Georgia, Times, serif',
            fontSize: 112,
            lineHeight: 0.92,
            transform: `translateY(${interpolate(reveal, [0, 1], [48, 0])}px) scale(${interpolate(reveal, [0, 1], [0.94, 1])})`,
            opacity: reveal,
          }}
        >
          {headline}
        </div>
        {body ? (
          <div
            style={{
              fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
              fontSize: 34,
              lineHeight: 1.25,
              color: 'rgba(255, 245, 236, 0.8)',
              maxWidth: '82%',
              opacity: interpolate(reveal, [0.2, 1], [0, 1]),
            }}
          >
            {body}
          </div>
        ) : null}
      </div>
      <div
        style={{
          position: 'absolute',
          right: 72,
          top: 112,
          width: 260,
          height: 260,
          borderRadius: '50%',
          background: 'radial-gradient(circle at 35% 35%, rgba(255,194,113,0.75), rgba(255,102,71,0.16) 48%, transparent 72%)',
          filter: 'blur(2px)',
          opacity: interpolate(reveal, [0, 1], [0.2, 0.95]),
        }}
      />
    </AbsoluteFill>
  )
}

function BulletStackTemplate({
  headline,
  body,
  bullets,
}: {
  headline: string
  body: string
  bullets: string[]
}) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()

  return (
    <AbsoluteFill style={{ padding: 88, color: '#f7efe6' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 28, width: '62%' }}>
        <div
          style={{
            fontFamily: 'Georgia, Times, serif',
            fontSize: 92,
            lineHeight: 0.94,
          }}
        >
          {headline}
        </div>
        {body ? (
          <div
            style={{
              fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
              fontSize: 32,
              lineHeight: 1.24,
              color: 'rgba(255,244,234,0.82)',
            }}
          >
            {body}
          </div>
        ) : null}
      </div>
      <div
        style={{
          position: 'absolute',
          right: 84,
          top: 144,
          width: 470,
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        {bullets.slice(0, 4).map((bullet, index) => {
          const localFrame = frame - index * 8
          const reveal = spring({
            frame: Math.max(localFrame, 0),
            fps,
            config: { damping: 16, stiffness: 110, mass: 0.9 },
          })
          return (
            <div
              key={`${bullet}-${index}`}
              style={{
                padding: '20px 22px',
                borderRadius: 22,
                background: 'rgba(7, 12, 22, 0.8)',
                border: '1px solid rgba(255,255,255,0.08)',
                fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
                fontSize: 28,
                lineHeight: 1.18,
                transform: `translateX(${interpolate(reveal, [0, 1], [44, 0])}px)`,
                opacity: reveal,
              }}
            >
              {bullet}
            </div>
          )
        })}
      </div>
    </AbsoluteFill>
  )
}

function QuoteFocusTemplate({
  headline,
  body,
  kicker,
}: {
  headline: string
  body: string
  kicker: string
}) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const reveal = spring({
    frame,
    fps,
    config: {
      damping: 24,
      stiffness: 90,
      mass: 1,
    },
  })

  return (
    <AbsoluteFill
      style={{
        padding: 96,
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff8f1',
      }}
    >
      <div
        style={{
          maxWidth: '74%',
          padding: '46px 52px',
          borderRadius: 30,
          background: 'rgba(4, 7, 15, 0.78)',
          border: '1px solid rgba(255,255,255,0.08)',
          transform: `scale(${interpolate(reveal, [0, 1], [0.92, 1])})`,
          opacity: reveal,
          boxShadow: '0 24px 80px rgba(0,0,0,0.34)',
        }}
      >
        <div
          style={{
            fontFamily: 'Georgia, Times, serif',
            fontSize: 84,
            lineHeight: 0.96,
          }}
        >
          {headline}
        </div>
        {body ? (
          <div
            style={{
              marginTop: 28,
              fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
              fontSize: 32,
              lineHeight: 1.24,
              color: 'rgba(255,245,236,0.8)',
            }}
          >
            {body}
          </div>
        ) : null}
        <div
          style={{
            marginTop: 30,
            display: 'inline-flex',
            paddingTop: 18,
            borderTop: '1px solid rgba(255,255,255,0.12)',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            fontSize: 22,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: '#f3d7af',
          }}
        >
          {kicker}
        </div>
      </div>
    </AbsoluteFill>
  )
}

function MotionTemplateRenderer({ scene }: { scene: RemotionScene }) {
  const templateId = (scene.motion?.templateId || 'kinetic_title') as MotionTemplateId
  const props = scene.motion?.props ?? {}
  const headline = props.headline || scene.onScreenText[0] || scene.title || 'Motion beat'
  const body = props.body || scene.onScreenText.slice(1, 3).join(' ') || scene.narration
  const kicker = props.kicker || scene.title || 'Cathode'
  const bullets = props.bullets ?? scene.onScreenText.slice(0, 4)

  switch (templateId) {
    case 'bullet_stack':
      return <BulletStackTemplate headline={headline} body={body} bullets={bullets} />
    case 'quote_focus':
      return <QuoteFocusTemplate headline={headline} body={body} kicker={kicker} />
    case 'kinetic_title':
    default:
      return <KineticTitleTemplate headline={headline} body={body} kicker={kicker} />
  }
}

function SceneVisual({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const zoom = interpolate(frame, [0, Math.max(scene.durationInFrames - 1, 1)], [1.02, 1.08])

  if (scene.sceneType === 'video' && scene.videoUrl) {
    const playFrames = Math.max(scene.playFrames ?? scene.durationInFrames, 1)
    const holdFrames = Math.max(scene.holdFrames ?? 0, 0)
    const sharedProps = {
      src: scene.videoUrl,
      muted: true,
      trimBefore: scene.trimBeforeFrames ?? 0,
      trimAfter: scene.trimAfterFrames ?? 0,
      playbackRate: scene.playbackRate ?? 1,
      style: {
        width: '100%',
        height: '100%',
        objectFit: 'cover' as const,
      },
    }

    return (
      <AbsoluteFill>
        <Sequence from={0} durationInFrames={playFrames}>
          <OffthreadVideo {...sharedProps} />
        </Sequence>
        {holdFrames > 0 ? (
          <Sequence from={playFrames} durationInFrames={holdFrames}>
            <Freeze frame={Math.max(playFrames - 1, 0)}>
              <OffthreadVideo {...sharedProps} />
            </Freeze>
          </Sequence>
        ) : null}
      </AbsoluteFill>
    )
  }

  if (scene.sceneType === 'image' && scene.imageUrl) {
    return (
      <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
        <Img
          src={scene.imageUrl}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${zoom})`,
          }}
        />
      </AbsoluteFill>
    )
  }

  return <MotionTemplateRenderer scene={scene} />
}

function SceneLayer({ scene }: { scene: RemotionScene }) {
  return (
    <FrameShell>
      <SceneVisual scene={scene} />
      {scene.audioUrl ? <Audio src={scene.audioUrl} /> : null}
    </FrameShell>
  )
}

function CathodeRender({ scenes = FALLBACK_PROPS.scenes }: CathodeRenderProps) {
  let offset = 0

  return (
    <AbsoluteFill style={{ backgroundColor: '#03050a' }}>
      {scenes.map((scene) => {
        const duration = Math.max(1, scene.durationInFrames || 1)
        const sequence = (
          <Sequence key={scene.uid} from={offset} durationInFrames={duration}>
            <SceneLayer scene={scene} />
          </Sequence>
        )
        offset += duration
        return sequence
      })}
    </AbsoluteFill>
  )
}

const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="CathodeRender"
        component={CathodeRender}
        defaultProps={FALLBACK_PROPS}
        width={FALLBACK_PROPS.width}
        height={FALLBACK_PROPS.height}
        fps={FALLBACK_PROPS.fps}
        durationInFrames={FALLBACK_PROPS.totalDurationInFrames}
        calculateMetadata={({ props }) => {
          const safeProps = props as CathodeRenderProps
          return {
            width: safeProps.width || FALLBACK_PROPS.width,
            height: safeProps.height || FALLBACK_PROPS.height,
            fps: safeProps.fps || FALLBACK_PROPS.fps,
            durationInFrames: Math.max(
              1,
              safeProps.totalDurationInFrames
                || safeProps.scenes?.reduce((sum, scene) => sum + Math.max(1, scene.durationInFrames || 1), 0)
                || FALLBACK_PROPS.totalDurationInFrames,
            ),
          }
        }}
      />
    </>
  )
}

registerRoot(RemotionRoot)
