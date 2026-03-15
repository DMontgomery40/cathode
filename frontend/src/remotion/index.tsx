import React from 'react'
import {
  AbsoluteFill,
  Audio,
  Composition,
  Freeze,
  Img,
  OffthreadVideo,
  Series,
  Sequence,
  interpolate,
  registerRoot,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion'
import { TransitionSeries, linearTiming } from '@remotion/transitions'
import { fade } from '@remotion/transitions/fade'
import { wipe } from '@remotion/transitions/wipe'
import { Canvas } from '@react-three/fiber'
import { Float } from '@react-three/drei'

type MotionTemplateId = 'kinetic_title' | 'bullet_stack' | 'quote_focus' | 'three_data_stage' | 'surreal_tableau_3d'

type RemotionScene = {
  uid: string
  sceneType: 'image' | 'video' | 'motion'
  title: string
  narration: string
  onScreenText: string[]
  durationInFrames: number
  sequenceDurationInFrames?: number
  audioUrl?: string | null
  imageUrl?: string | null
  videoUrl?: string | null
  videoAudioSource?: 'clip' | 'narration' | string
  trimBeforeFrames?: number
  trimAfterFrames?: number
  playbackRate?: number
  holdFrames?: number
  playFrames?: number
  requiresRemotion?: boolean
  textLayerKind?: 'none' | 'captions' | 'software_demo_focus' | string
  composition?: {
    family?: string
    mode?: 'none' | 'overlay' | 'native' | string
    props?: Record<string, unknown>
    transitionAfter?: {
      kind?: string
      durationInFrames?: number
    } | null
    data?: Record<string, unknown> | unknown[] | null
    rationale?: string
  }
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

export type CathodeRenderProps = {
  width?: number
  height?: number
  fps?: number
  textRenderMode?: 'visual_authored' | 'deterministic_overlay' | string
  totalDurationInFrames?: number
  scenes?: RemotionScene[]
}

export const FALLBACK_PROPS: Required<CathodeRenderProps> = {
  width: 1664,
  height: 928,
  fps: 24,
  textRenderMode: 'visual_authored',
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

const BUILTIN_TEXT_LAYER_FAMILIES = new Set(['software_demo_focus'])

const getSceneDurationInFrames = (scene: RemotionScene) => Math.max(1, scene.durationInFrames || 1)

const getSequenceDurationInFrames = (scene: RemotionScene) => {
  const baseDuration = getSceneDurationInFrames(scene)
  return Math.max(baseDuration, scene.sequenceDurationInFrames || 0)
}

function resolveTextLayerKind(scene: RemotionScene, textRenderMode: string) {
  const explicit = String(scene.textLayerKind || '').trim()
  if (explicit) {
    return explicit
  }

  const compositionMode = String(scene.composition?.mode || 'none')
  const family = String(scene.composition?.family || '')
  const headline = String((scene.composition?.props as Record<string, unknown> | undefined)?.headline || '').trim()
  if (scene.sceneType !== 'motion' && BUILTIN_TEXT_LAYER_FAMILIES.has(family) && (scene.onScreenText.length > 0 || headline)) {
    return family
  }
  if (scene.sceneType === 'motion' || scene.onScreenText.length === 0) {
    return 'none'
  }
  if (compositionMode === 'overlay') {
    return 'captions'
  }
  if (textRenderMode === 'deterministic_overlay' && scene.sceneType === 'image') {
    return 'captions'
  }
  return 'none'
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

const captionContainerStyle: React.CSSProperties = {
  position: 'absolute',
  left: 72,
  right: 72,
  bottom: 56,
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
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

function SceneCaptions({ title, lines }: { title: string; lines: string[] }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const fade = spring({
    frame,
    fps,
    config: {
      damping: 18,
      stiffness: 120,
      mass: 0.9,
    },
  })

  return (
    <div style={{ ...captionContainerStyle, opacity: fade }}>
      {title ? (
        <div
          style={{
            display: 'inline-flex',
            alignSelf: 'flex-start',
            padding: '8px 14px',
            borderRadius: 999,
            background: 'rgba(8, 10, 18, 0.76)',
            color: '#f8e8d0',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            fontSize: 24,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          {title}
        </div>
      ) : null}
      {lines.slice(0, 3).map((line, index) => (
        <div
          key={`${line}-${index}`}
          style={{
            display: 'inline-flex',
            alignSelf: 'flex-start',
            maxWidth: '78%',
            padding: '12px 18px',
            borderRadius: 18,
            background: 'rgba(4, 7, 14, 0.78)',
            color: '#f5f1ea',
            fontFamily: 'Georgia, Times, serif',
            fontSize: 38,
            lineHeight: 1.08,
            transform: `translateY(${interpolate(fade, [0, 1], [18 + index * 6, 0])}px)`,
          }}
        >
          {line}
        </div>
      ))}
    </div>
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

function SoftwareDemoOverlay({ scene }: { scene: RemotionScene }) {
  const props = (scene.composition?.props ?? {}) as Record<string, unknown>
  const headline = String(props.headline || scene.title || scene.onScreenText[0] || 'Software proof')
  const normalizedHeadline = headline.trim().replace(/\s+/g, ' ').toLowerCase()
  const notes = scene.onScreenText
    .filter((note, index) => {
      if (index !== 0) {
        return true
      }
      return note.trim().replace(/\s+/g, ' ').toLowerCase() !== normalizedHeadline
    })
    .slice(0, 3)

  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <div
        style={{
          position: 'absolute',
          inset: 46,
          borderRadius: 30,
          border: '1px solid rgba(255,255,255,0.12)',
          boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.04)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 64,
          top: 64,
          display: 'inline-flex',
          padding: '10px 16px',
          borderRadius: 999,
          background: 'rgba(7, 11, 20, 0.84)',
          color: '#f3d7af',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          fontSize: 20,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
        }}
      >
        {headline}
      </div>
      {notes.length > 0 && (
        <div
          style={{
            position: 'absolute',
            right: 68,
            top: 124,
            width: 360,
            display: 'flex',
            flexDirection: 'column',
            gap: 14,
          }}
        >
          {notes.map((note, index) => (
            <div
              key={`${note}-${index}`}
              style={{
                padding: '18px 20px',
                borderRadius: 20,
                background: 'rgba(5, 9, 18, 0.84)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: '#f7efe6',
                fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
                fontSize: 24,
                lineHeight: 1.15,
              }}
            >
              {note}
            </div>
          ))}
        </div>
      )}
    </AbsoluteFill>
  )
}

function ThreeDataStage({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const reveal = spring({
    frame,
    fps,
    config: {
      damping: 18,
      stiffness: 90,
      mass: 0.9,
    },
  })
  const data = scene.composition?.data
  const dataPoints = Array.isArray((data as Record<string, unknown> | undefined)?.data_points)
    ? (((data as Record<string, unknown>).data_points as unknown[]) ?? []).map((item) => String(item))
    : scene.onScreenText.slice(0, 4)
  const bars = (dataPoints.length > 0 ? dataPoints : ['First', 'Second', 'Third']).slice(0, 4)
  const headline = String((scene.composition?.props as Record<string, unknown> | undefined)?.headline || scene.title || 'Data stage')
  const cameraY = interpolate(reveal, [0, 1], [1.4, 2.8])
  const rotationY = interpolate(frame, [0, Math.max(scene.durationInFrames - 1, 1)], [-0.35, 0.18])

  return (
    <AbsoluteFill style={{ background: 'radial-gradient(circle at 50% 20%, rgba(88,142,255,0.18), transparent 28%), linear-gradient(180deg, #04070d 0%, #0b1220 48%, #090c12 100%)' }}>
      <div style={{ position: 'absolute', inset: 0 }}>
        <Canvas camera={{ position: [0, cameraY, 8], fov: 42 }}>
          <color attach="background" args={['#04070d']} />
          <ambientLight intensity={1.5} />
          <directionalLight position={[4, 8, 6]} intensity={2.2} color="#f8d0a0" />
          <directionalLight position={[-5, 4, 3]} intensity={1.1} color="#7ea3ff" />
          <group rotation={[0, rotationY, 0]} position={[0, -1.6, 0]}>
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
              <planeGeometry args={[20, 20]} />
              <meshStandardMaterial color="#101622" />
            </mesh>
            {bars.map((label, index) => {
              const height = 1.8 + (bars.length - index) * 0.7
              const x = (index - (bars.length - 1) / 2) * 2.2
              return (
                <Float key={`${label}-${index}`} speed={1.2 + index * 0.15} rotationIntensity={0.06} floatIntensity={0.3}>
                  <mesh position={[x, height / 2, index * -0.25]}>
                    <boxGeometry args={[1.4, height, 1.4]} />
                    <meshStandardMaterial color={index === 0 ? '#f3d7af' : index % 2 === 0 ? '#6f9bff' : '#ff8a62'} metalness={0.55} roughness={0.25} />
                  </mesh>
                </Float>
              )
            })}
          </group>
        </Canvas>
      </div>
      <AbsoluteFill style={{ padding: 72, justifyContent: 'space-between', pointerEvents: 'none' }}>
        <div
          style={{
            color: '#fff7f0',
            fontFamily: 'Georgia, Times, serif',
            fontSize: 88,
            lineHeight: 0.94,
            maxWidth: '58%',
          }}
        >
          {headline}
        </div>
        <div style={{ display: 'flex', gap: 18 }}>
          {bars.map((label, index) => (
            <div
              key={`${label}-label-${index}`}
              style={{
                flex: 1,
                padding: '18px 20px',
                borderRadius: 20,
                background: 'rgba(5, 9, 18, 0.82)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: '#f7efe6',
                fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
                fontSize: 22,
                lineHeight: 1.12,
              }}
            >
              {label}
            </div>
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  )
}

function SurrealTableau3D({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const reveal = spring({
    frame,
    fps,
    config: {
      damping: 18,
      stiffness: 88,
      mass: 1,
    },
  })
  const props = (scene.composition?.props ?? {}) as Record<string, unknown>
  const headline = String(props.headline || scene.title || 'Dream tableau')
  const body = String(props.body || scene.narration || '')
  const leftSubject = String(props.leftSubject || scene.onScreenText[0] || scene.title || 'Hero form')
  const rightSubject = String(props.rightSubject || scene.onScreenText[1] || 'Counterpoint')
  const environment = String(props.environment || 'surreal cinematic void')
  const orbit = interpolate(frame, [0, Math.max(scene.durationInFrames - 1, 1)], [-0.28, 0.3])
  const cameraZ = interpolate(reveal, [0, 1], [10.5, 8.2])

  return (
    <AbsoluteFill style={{ background: 'radial-gradient(circle at 50% 18%, rgba(255,190,120,0.16), transparent 30%), linear-gradient(180deg, #04060c 0%, #0b1020 56%, #09070f 100%)' }}>
      <div style={{ position: 'absolute', inset: 0 }}>
        <Canvas camera={{ position: [0, 1.2, cameraZ], fov: 40 }}>
          <color attach="background" args={['#05070d']} />
          <ambientLight intensity={1.4} />
          <directionalLight position={[4, 7, 6]} intensity={2} color="#ffd6aa" />
          <directionalLight position={[-6, 3, 2]} intensity={1.1} color="#7aa6ff" />
          <group rotation={[0.08, orbit, 0]} position={[0, -0.5, 0]}>
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.9, 0]}>
              <planeGeometry args={[18, 18]} />
              <meshStandardMaterial color="#0d1320" />
            </mesh>
            <Float speed={1.1} rotationIntensity={0.08} floatIntensity={0.35}>
              <mesh position={[-2.2, 0.3, -0.4]} scale={1.25}>
                <sphereGeometry args={[1.15, 48, 48]} />
                <meshStandardMaterial color="#ff9c72" emissive="#532117" emissiveIntensity={0.45} metalness={0.4} roughness={0.18} />
              </mesh>
            </Float>
            <Float speed={1.35} rotationIntensity={0.12} floatIntensity={0.28}>
              <mesh position={[2.4, 0.55, 0.3]} rotation={[0.9, 0.2, 0]}>
                <torusKnotGeometry args={[0.92, 0.28, 160, 24]} />
                <meshStandardMaterial color="#86a7ff" emissive="#182347" emissiveIntensity={0.5} metalness={0.52} roughness={0.22} />
              </mesh>
            </Float>
            <mesh position={[0, 0.25, -1.9]} scale={[4.8, 2.2, 0.2]}>
              <boxGeometry args={[1, 1, 1]} />
              <meshStandardMaterial color="#1a1730" emissive="#221d3f" emissiveIntensity={0.22} transparent opacity={0.72} />
            </mesh>
          </group>
        </Canvas>
      </div>
      <AbsoluteFill style={{ padding: 72, justifyContent: 'space-between', pointerEvents: 'none' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18, maxWidth: '58%', opacity: reveal }}>
          <div
            style={{
              color: '#fff6ee',
              fontFamily: 'Georgia, Times, serif',
              fontSize: 92,
              lineHeight: 0.92,
            }}
          >
            {headline}
          </div>
          {body ? (
            <div
              style={{
                color: 'rgba(255,245,236,0.82)',
                fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
                fontSize: 30,
                lineHeight: 1.2,
                maxWidth: '82%',
              }}
            >
              {body}
            </div>
          ) : null}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
          {[leftSubject, rightSubject].map((label, index) => (
            <div
              key={`${label}-${index}`}
              style={{
                padding: '18px 20px',
                borderRadius: 22,
                background: 'rgba(7, 10, 18, 0.82)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: '#f6efe6',
                fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
                fontSize: 24,
                lineHeight: 1.14,
              }}
            >
              {label}
            </div>
          ))}
        </div>
        <div
          style={{
            position: 'absolute',
            right: 72,
            top: 78,
            color: '#f4d8b1',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            fontSize: 20,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          {environment}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  )
}

function MotionTemplateRenderer({ scene }: { scene: RemotionScene }) {
  const templateId = (
    scene.composition?.family
    || scene.motion?.templateId
    || 'kinetic_title'
  ) as MotionTemplateId | 'kinetic_statements'
  const props = (scene.composition?.props ?? scene.motion?.props ?? {}) as Record<string, unknown>
  const headline = String(props.headline || scene.onScreenText[0] || scene.title || 'Motion beat')
  const body = String(props.body || scene.onScreenText.slice(1, 3).join(' ') || scene.narration || '')
  const kicker = String(props.kicker || scene.title || 'Cathode')
  const bullets = (props.bullets as string[] | undefined) ?? scene.onScreenText.slice(0, 4)

  switch (templateId) {
    case 'bullet_stack':
      return <BulletStackTemplate headline={headline} body={body} bullets={bullets} />
    case 'quote_focus':
      return <QuoteFocusTemplate headline={headline} body={body} kicker={kicker} />
    case 'three_data_stage':
      return <ThreeDataStage scene={scene} />
    case 'surreal_tableau_3d':
      return <SurrealTableau3D scene={scene} />
    case 'kinetic_statements':
    case 'kinetic_title':
    default:
      return <KineticTitleTemplate headline={headline} body={body} kicker={kicker} />
  }
}

function StaticOrMotionSceneVisual({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const zoom = interpolate(frame, [0, Math.max(scene.durationInFrames - 1, 1)], [1.02, 1.08])
  const family = String(scene.composition?.family || scene.motion?.templateId || '')
  const mode = String(scene.composition?.mode || (scene.sceneType === 'motion' ? 'native' : 'none'))
  const isMediaOverlayFamily = scene.sceneType !== 'motion' && BUILTIN_TEXT_LAYER_FAMILIES.has(family)

  if (mode === 'native' && family && !isMediaOverlayFamily) {
    return <MotionTemplateRenderer scene={scene} />
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

  if (isMediaOverlayFamily) {
    return <AbsoluteFill />
  }

  return <MotionTemplateRenderer scene={scene} />
}

function VideoSceneVisual({
  scene,
  extensionFrames,
}: {
  scene: RemotionScene
  extensionFrames: number
}) {
  if (!scene.videoUrl) {
    return <MotionTemplateRenderer scene={scene} />
  }

  const baseDuration = getSceneDurationInFrames(scene)
  const playFrames = Math.max(1, Math.min(scene.playFrames ?? baseDuration, baseDuration))
  const holdFrames = Math.max(baseDuration - playFrames, 0)
  const freezeFrame = Math.max(playFrames - 1, 0)
  const audibleDuringPlayback = scene.videoAudioSource === 'clip'
  const videoStyle = {
    width: '100%',
    height: '100%',
    objectFit: 'cover' as const,
  }
  const audibleProps = {
    src: scene.videoUrl,
    muted: !audibleDuringPlayback,
    trimBefore: scene.trimBeforeFrames ?? 0,
    trimAfter: scene.trimAfterFrames ?? 0,
    playbackRate: scene.playbackRate ?? 1,
    style: videoStyle,
  }
  const silentProps = {
    ...audibleProps,
    muted: true,
  }

  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={playFrames}>
        <OffthreadVideo {...audibleProps} />
      </Sequence>
      {holdFrames > 0 ? (
        <Sequence from={playFrames} durationInFrames={holdFrames}>
          <Freeze frame={freezeFrame}>
            <OffthreadVideo {...silentProps} />
          </Freeze>
        </Sequence>
      ) : null}
      {extensionFrames > 0 ? (
        <Sequence from={baseDuration} durationInFrames={extensionFrames}>
          <Freeze frame={freezeFrame}>
            <OffthreadVideo {...silentProps} />
          </Freeze>
        </Sequence>
      ) : null}
    </AbsoluteFill>
  )
}

function SceneVisual({ scene }: { scene: RemotionScene }) {
  const baseDuration = getSceneDurationInFrames(scene)
  const extensionFrames = Math.max(getSequenceDurationInFrames(scene) - baseDuration, 0)

  if (scene.sceneType === 'video') {
    return <VideoSceneVisual scene={scene} extensionFrames={extensionFrames} />
  }

  if (extensionFrames <= 0) {
    return <StaticOrMotionSceneVisual scene={scene} />
  }

  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={baseDuration}>
        <StaticOrMotionSceneVisual scene={scene} />
      </Sequence>
      <Sequence from={baseDuration} durationInFrames={extensionFrames}>
        <Freeze frame={Math.max(baseDuration - 1, 0)}>
          <StaticOrMotionSceneVisual scene={scene} />
        </Freeze>
      </Sequence>
    </AbsoluteFill>
  )
}

function SceneAudio({ scene }: { scene: RemotionScene }) {
  if (!scene.audioUrl) {
    return null
  }

  return (
    <Sequence from={0} durationInFrames={getSceneDurationInFrames(scene)}>
      <Audio src={scene.audioUrl} />
    </Sequence>
  )
}

function SceneLayer({
  scene,
  textRenderMode,
}: {
  scene: RemotionScene
  textRenderMode: string
}) {
  const textLayerKind = resolveTextLayerKind(scene, textRenderMode)

  return (
    <FrameShell>
      <SceneVisual scene={scene} />
      <SceneAudio scene={scene} />
      {textLayerKind === 'software_demo_focus' ? <SoftwareDemoOverlay scene={scene} /> : null}
      {textLayerKind === 'captions' ? <SceneCaptions title={scene.title} lines={scene.onScreenText} /> : null}
    </FrameShell>
  )
}

function resolveTransitionPresentation(kind: string): any {
  const normalized = String(kind || '').trim().toLowerCase()
  if (normalized === 'wipe') {
    return wipe()
  }
  return fade()
}

export function CathodeRender({
  scenes = FALLBACK_PROPS.scenes,
  textRenderMode = FALLBACK_PROPS.textRenderMode,
}: CathodeRenderProps) {
  const hasTransitions = scenes.some((scene) => scene.composition?.transitionAfter?.kind)

  if (hasTransitions) {
    return (
      <AbsoluteFill style={{ backgroundColor: '#03050a' }}>
        <TransitionSeries>
          {scenes.map((scene, index) => (
            <React.Fragment key={scene.uid}>
              <TransitionSeries.Sequence durationInFrames={getSequenceDurationInFrames(scene)}>
                <SceneLayer scene={scene} textRenderMode={textRenderMode} />
              </TransitionSeries.Sequence>
              {index < scenes.length - 1 && scene.composition?.transitionAfter?.kind ? (
                <TransitionSeries.Transition
                  timing={linearTiming({
                    durationInFrames: Math.max(1, scene.composition?.transitionAfter?.durationInFrames || 20),
                  })}
                  presentation={resolveTransitionPresentation(scene.composition.transitionAfter.kind)}
                />
              ) : null}
            </React.Fragment>
          ))}
        </TransitionSeries>
      </AbsoluteFill>
    )
  }

  return (
    <AbsoluteFill style={{ backgroundColor: '#03050a' }}>
      <Series>
        {scenes.map((scene) => (
          <Series.Sequence key={scene.uid} durationInFrames={getSequenceDurationInFrames(scene)}>
            <SceneLayer scene={scene} textRenderMode={textRenderMode} />
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  )
}

export const RemotionRoot: React.FC = () => {
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
