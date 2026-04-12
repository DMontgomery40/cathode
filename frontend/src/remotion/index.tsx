import React, { useMemo } from 'react'
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
import { fitText, fitTextOnNLines } from '@remotion/layout-utils'
import { ThreeCanvas } from '@remotion/three'
import { Float } from '@react-three/drei'
import { AdditiveBlending, BackSide } from 'three'

// ─── Typographic System ───
// Shared font stacks and roles used across all template compositions.
// ThreeDataStage established the reference; these constants unify the rest.

const FONT_HEADLINE = 'Georgia, "Times New Roman", serif'
const FONT_BODY = '"Inter", "SF Pro Text", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif'
const FONT_DATA = 'ui-monospace, SFMono-Regular, Menlo, monospace'
const FONT_CAPTION = '"SF Pro Text", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif'

// Maximum font sizes for fitText clamping (prevents comically large text on short strings)
const HEADLINE_MAX_SIZE = 112
const SUBHEADLINE_MAX_SIZE = 84
const BODY_SIZE = 30
const BODY_LINE_HEIGHT = 1.45
const CAPTION_SIZE = 20
const CAPTION_LETTER_SPACING = '0.08em'
const LABEL_SIZE = 18

// Responsive headline: fits text to a given width, capped at maxSize.
function useHeadlineFontSize(
  text: string,
  withinWidth: number,
  maxSize: number = HEADLINE_MAX_SIZE,
): number {
  return useMemo(() => {
    if (!text.trim()) return maxSize
    try {
      const { fontSize } = fitText({
        text,
        withinWidth,
        fontFamily: FONT_HEADLINE,
        fontWeight: 'bold',
      })
      return Math.min(fontSize, maxSize)
    } catch {
      // fitText can throw in SSR if no DOM is available; fall back gracefully
      return maxSize
    }
  }, [text, withinWidth, maxSize])
}

// Responsive body text: fits multi-line text, capped at BODY_SIZE.
function useBodyFontSize(
  text: string,
  withinWidth: number,
  maxLines: number = 3,
  maxSize: number = BODY_SIZE + 6,
): number {
  return useMemo(() => {
    if (!text.trim()) return BODY_SIZE
    try {
      const { fontSize } = fitTextOnNLines({
        text,
        maxBoxWidth: withinWidth,
        maxLines,
        fontFamily: FONT_BODY,
      })
      return Math.min(fontSize, maxSize)
    } catch {
      return BODY_SIZE
    }
  }, [text, withinWidth, maxLines, maxSize])
}

// Responsive data value text: single-line fit for metric values, region labels, etc.
function useDataFontSize(
  text: string,
  withinWidth: number,
  maxSize: number = 52,
  fontFamily: string = FONT_DATA,
): number {
  return useMemo(() => {
    if (!text.trim()) return maxSize
    try {
      const { fontSize } = fitText({ text, withinWidth, fontFamily, fontWeight: '700' })
      return Math.min(fontSize, maxSize)
    } catch {
      return maxSize
    }
  }, [text, withinWidth, maxSize, fontFamily])
}

// Responsive caption text: multi-line fit for captions and labels.
function useCaptionFontSize(
  text: string,
  withinWidth: number,
  maxLines: number = 2,
  maxSize: number = CAPTION_SIZE + 4,
): number {
  return useMemo(() => {
    if (!text.trim()) return CAPTION_SIZE
    try {
      const { fontSize } = fitTextOnNLines({ text, maxBoxWidth: withinWidth, maxLines, fontFamily: FONT_CAPTION })
      return Math.min(fontSize, maxSize)
    } catch {
      return CAPTION_SIZE
    }
  }, [text, withinWidth, maxLines, maxSize])
}

// Style override props from scene composition — allows director to control visual parameters.
type StyleOverrides = {
  textScale: number
  accentColor: string | null
  padding: number
  brightness: number | null
  saturation: number | null
}

function useStyleOverrides(
  scene: RemotionScene,
  defaults: { padding?: number; brightness?: number; saturation?: number } = {},
): StyleOverrides {
  const p = scene.composition?.props as Record<string, unknown> | undefined
  const textScale = Math.max(0.5, Math.min(2.0, Number(p?.textScale) || 1.0))
  const accentColor = typeof p?.accentColor === 'string' ? p.accentColor : null
  const padding = typeof p?.padding === 'number' ? p.padding : (defaults.padding ?? 88)
  const brightness = typeof p?.brightness === 'number' ? p.brightness : (defaults.brightness ?? null)
  const saturation = typeof p?.saturation === 'number' ? p.saturation : (defaults.saturation ?? null)
  return { textScale, accentColor, padding, brightness, saturation }
}

type MotionTemplateId =
  | 'kinetic_title'
  | 'bullet_stack'
  | 'quote_focus'
  | 'three_data_stage'
  | 'surreal_tableau_3d'
  | 'cover_hook'
  | 'orientation'
  | 'synthesis_summary'
  | 'closing_cta'
  | 'clinical_explanation'
  | 'metric_improvement'
  | 'brain_region_focus'
  | 'metric_comparison'
  | 'timeline_progression'
  | 'analogy_metaphor'

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
    manifestation?: 'authored_image' | 'native_remotion' | 'source_video' | string
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
    props?: Record<string, unknown>
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

function trimOverlayCopy(value: unknown) {
  return String(value || '').trim()
}

function resolveManifestation(scene: RemotionScene) {
  const explicit = String(scene.composition?.manifestation || '').trim()
  if (explicit) {
    return explicit
  }
  if (scene.sceneType === 'video') {
    return 'source_video'
  }
  if (scene.sceneType === 'motion') {
    return 'native_remotion'
  }
  return 'authored_image'
}

const getSceneDurationInFrames = (scene: RemotionScene) => Math.max(1, scene.durationInFrames || 1)

const getSequenceDurationInFrames = (scene: RemotionScene) => {
  const baseDuration = getSceneDurationInFrames(scene)
  return Math.max(baseDuration, scene.sequenceDurationInFrames || 0)
}

function resolveTextLayerKind(scene: RemotionScene) {
  const explicit = String(scene.textLayerKind || '').trim()
  if (explicit) {
    return explicit
  }

  const manifestation = resolveManifestation(scene)
  const compositionMode = String(scene.composition?.mode || 'none')
  const family = String(scene.composition?.family || '')
  const props = (scene.composition?.props as Record<string, unknown> | undefined) || {}
  const headline = trimOverlayCopy(props.headline)
  const body = trimOverlayCopy(props.body)
  const hasCopy = scene.onScreenText.length > 0 || Boolean(headline) || Boolean(body)
  if (manifestation !== 'native_remotion' && BUILTIN_TEXT_LAYER_FAMILIES.has(family) && hasCopy) {
    return family
  }
  if (manifestation === 'native_remotion' || !hasCopy) {
    return 'none'
  }
  if (compositionMode === 'native' && family) {
    return 'none'
  }
  if (compositionMode === 'overlay') {
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
            fontFamily: FONT_DATA,
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
            fontFamily: FONT_HEADLINE,
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

  // 72% of 1664 (canvas) - 2*88 (padding) = ~1070px available
  const headlineSize = useHeadlineFontSize(headline, 1070, HEADLINE_MAX_SIZE)
  const bodySize = useBodyFontSize(body, 880, 3)

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
          fontFamily: FONT_DATA,
          fontSize: CAPTION_SIZE + 2,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
        }}
      >
        {kicker}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: '72%' }}>
        <div
          style={{
            fontFamily: FONT_HEADLINE,
            fontSize: headlineSize,
            lineHeight: 0.92,
            fontWeight: 'bold',
            transform: `translateY(${interpolate(reveal, [0, 1], [48, 0])}px) scale(${interpolate(reveal, [0, 1], [0.94, 1])})`,
            opacity: reveal,
          }}
        >
          {headline}
        </div>
        {body ? (
          <div
            style={{
              fontFamily: FONT_BODY,
              fontSize: bodySize,
              lineHeight: BODY_LINE_HEIGHT,
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

  // 62% of (1664 - 2*88) = ~922px
  const headlineSize = useHeadlineFontSize(headline, 922, 92)
  const bodySize = useBodyFontSize(body, 922, 3)

  return (
    <AbsoluteFill style={{ padding: 88, color: '#f7efe6' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 28, width: '62%' }}>
        <div
          style={{
            fontFamily: FONT_HEADLINE,
            fontSize: headlineSize,
            lineHeight: 0.94,
            fontWeight: 'bold',
          }}
        >
          {headline}
        </div>
        {body ? (
          <div
            style={{
              fontFamily: FONT_BODY,
              fontSize: bodySize,
              lineHeight: BODY_LINE_HEIGHT,
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
                fontFamily: FONT_BODY,
                fontSize: BODY_SIZE,
                lineHeight: BODY_LINE_HEIGHT,
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

  // 74% of (1664 - 2*96) - 2*52 (card padding) = ~984px
  const headlineSize = useHeadlineFontSize(headline, 984, SUBHEADLINE_MAX_SIZE)
  const bodySize = useBodyFontSize(body, 984, 4)

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
            fontFamily: FONT_HEADLINE,
            fontSize: headlineSize,
            lineHeight: 0.96,
            fontWeight: 'bold',
          }}
        >
          {headline}
        </div>
        {body ? (
          <div
            style={{
              marginTop: 28,
              fontFamily: FONT_BODY,
              fontSize: bodySize,
              lineHeight: BODY_LINE_HEIGHT,
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
            fontFamily: FONT_DATA,
            fontSize: CAPTION_SIZE + 2,
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

// ─── Shared background image primitive for template compositions ───

function CompositionBackgroundImage({
  src,
  reveal,
  brightness = 0.45,
  saturation = 0.85,
  scrimGradient = 'linear-gradient(135deg, rgba(3,5,10,0.88) 0%, rgba(3,5,10,0.5) 50%, transparent 80%)',
  panScale,
}: {
  src: string
  reveal: number
  brightness?: number
  saturation?: number
  scrimGradient?: string
  panScale?: number
}) {
  return (
    <AbsoluteFill style={{ overflow: 'hidden' }}>
      <Img
        src={src}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          opacity: interpolate(reveal, [0, 1], [0.5, 0.75]),
          filter: `brightness(${brightness}) saturate(${saturation})`,
          transform: panScale ? `scale(${panScale})` : undefined,
        }}
      />
      <AbsoluteFill style={{ background: scrimGradient }} />
    </AbsoluteFill>
  )
}

// ─── Shared scene prop helper ───

function sceneStr(scene: RemotionScene, key: string, fallback: string = ''): string {
  const p = scene.composition?.props as Record<string, unknown> | undefined
  const v = p?.[key]
  return typeof v === 'string' ? v : fallback
}

function sceneArr(scene: RemotionScene, key: string): string[] {
  const p = scene.composition?.props as Record<string, unknown> | undefined
  const v = p?.[key]
  return Array.isArray(v) ? v.map(String) : []
}

// ─── Template: cover_hook ───

function CoverHookTemplate({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps, durationInFrames } = useVideoConfig()
  const reveal = spring({ frame, fps, config: { damping: 22, stiffness: 110, mass: 0.8 } })
  const panScale = interpolate(frame, [0, Math.max(durationInFrames - 1, 1)], [1.0, 1.06])
  const overrides = useStyleOverrides(scene, { brightness: 0.38, saturation: 0.75 })

  const headline = sceneStr(scene, 'headline', scene.onScreenText[0] || scene.title || '')
  const subtitle = sceneStr(scene, 'subtitle', scene.onScreenText[1] || '')
  const kicker = sceneStr(scene, 'kicker', scene.title || '')

  // 72% of (1664 - 2*padding) ~ 1070px at default padding
  const headlineSize = useHeadlineFontSize(headline, 1070, 96 * overrides.textScale)
  const subtitleSize = useBodyFontSize(subtitle, 880, 3)

  return (
    <AbsoluteFill style={{ color: '#f7efe6' }}>
      {scene.imageUrl && (
        <CompositionBackgroundImage
          src={scene.imageUrl}
          reveal={reveal}
          brightness={overrides.brightness ?? 0.38}
          saturation={overrides.saturation ?? 0.75}
          panScale={panScale}
          scrimGradient="linear-gradient(155deg, rgba(3,5,10,0.96) 0%, rgba(3,5,10,0.78) 35%, rgba(3,5,10,0.3) 65%, rgba(3,5,10,0.15) 100%)"
        />
      )}
      <AbsoluteFill style={{ padding: overrides.padding, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        {/* Kicker pill with glass styling */}
        <div
          style={{
            alignSelf: 'flex-start',
            padding: '10px 20px',
            borderRadius: 999,
            background: 'rgba(255,255,255,0.06)',
            backdropFilter: 'blur(12px) saturate(1.4)',
            WebkitBackdropFilter: 'blur(12px) saturate(1.4)',
            border: '1px solid rgba(255,255,255,0.1)',
            fontFamily: FONT_DATA,
            fontSize: CAPTION_SIZE + 2,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: overrides.accentColor || '#5eead4',
            opacity: interpolate(reveal, [0, 0.3], [0, 1]),
            transform: `translateY(${interpolate(reveal, [0, 0.3], [-12, 0])}px)`,
          }}
        >
          {kicker}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: '72%' }}>
          <div
            style={{
              fontFamily: FONT_HEADLINE,
              fontSize: headlineSize,
              lineHeight: 0.94,
              fontWeight: 'bold',
              transform: `translateY(${interpolate(reveal, [0, 1], [48, 0])}px) scale(${interpolate(reveal, [0, 1], [0.94, 1])})`,
              opacity: reveal,
              textShadow: '0 4px 40px rgba(0,0,0,0.5)',
            }}
          >
            {headline}
          </div>
          {subtitle ? (
            <div
              style={{
                fontFamily: FONT_BODY,
                fontSize: subtitleSize,
                lineHeight: BODY_LINE_HEIGHT,
                color: 'rgba(247,239,230,0.75)',
                maxWidth: '82%',
                opacity: interpolate(reveal, [0.15, 1], [0, 1]),
                transform: `translateY(${interpolate(reveal, [0.15, 1], [20, 0])}px)`,
              }}
            >
              {subtitle}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  )
}

// ─── Template: orientation ───

function OrientationTemplate({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const overrides = useStyleOverrides(scene, { brightness: 0.3, saturation: 0.65 })
  const headline = sceneStr(scene, 'headline', scene.onScreenText[0] || scene.title || 'What We Will Explore')
  const items = sceneArr(scene, 'items')
  const effectiveItems = items.length > 0 ? items : scene.onScreenText.slice(1, 7)

  const headReveal = spring({ frame, fps, config: { damping: 20, stiffness: 110, mass: 0.8 } })

  // 38% of (1664 - 2*padding) - gap = ~530px
  const headlineSize = useHeadlineFontSize(headline, 530, 72 * overrides.textScale)

  return (
    <AbsoluteFill style={{ color: '#f7efe6', background: 'radial-gradient(circle at 15% 20%, rgba(94,234,212,0.06), transparent 40%), linear-gradient(180deg, #03050a 0%, #0a0f1a 100%)' }}>
      {scene.imageUrl && (
        <CompositionBackgroundImage src={scene.imageUrl} reveal={headReveal} brightness={overrides.brightness ?? 0.3} saturation={overrides.saturation ?? 0.65} />
      )}
      <AbsoluteFill style={{ padding: overrides.padding, display: 'flex', flexDirection: 'row', gap: 56 }}>
        {/* Left column: headline + decorative element */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24, width: '38%', justifyContent: 'center' }}>
          <div
            style={{
              fontFamily: FONT_HEADLINE,
              fontSize: headlineSize,
              lineHeight: 0.94,
              fontWeight: 'bold',
              transform: `translateY(${interpolate(headReveal, [0, 1], [32, 0])}px)`,
              opacity: headReveal,
            }}
          >
            {headline}
          </div>
          {/* Subtle info line */}
          <div
            style={{
              fontFamily: FONT_DATA,
              fontSize: LABEL_SIZE - 2,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: 'rgba(94,234,212,0.5)',
              opacity: interpolate(headReveal, [0.3, 0.8], [0, 1]),
            }}
          >
            {effectiveItems.length} {effectiveItems.length === 1 ? 'topic' : 'topics'}
          </div>
        </div>
        {/* Right column: roadmap items */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, position: 'relative', justifyContent: 'center' }}>
          {effectiveItems.slice(0, 6).map((item, i) => {
            const localFrame = frame - 10 - i * 7
            const itemReveal = spring({
              frame: Math.max(localFrame, 0),
              fps,
              config: { damping: 16, stiffness: 110, mass: 0.9 },
            })
            return (
              <div
                key={`${item}-${i}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 20,
                  transform: `translateX(${interpolate(itemReveal, [0, 1], [28, 0])}px)`,
                  opacity: itemReveal,
                }}
              >
                <div
                  style={{
                    padding: '16px 22px',
                    fontFamily: FONT_BODY,
                    fontSize: BODY_SIZE - 4,
                    lineHeight: BODY_LINE_HEIGHT,
                    flex: 1,
                  }}
                >
                  {item}
                </div>
              </div>
            )
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  )
}

// ─── Template: synthesis_summary ───

function SynthesisSummaryTemplate({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const overrides = useStyleOverrides(scene, { brightness: 0.3 })
  const headline = sceneStr(scene, 'headline', scene.title || 'Summary')
  const p = scene.composition?.props as Record<string, unknown> | undefined
  const rawCols = (p?.columns ?? []) as Array<{
    title?: string; accent?: string; items?: Array<{ label?: string; icon?: string } | string>
  }>

  const headReveal = spring({ frame, fps, config: { damping: 20, stiffness: 100, mass: 0.8 } })
  // ~1488px available width
  const headlineSize = useHeadlineFontSize(headline, 1400, 64 * overrides.textScale)
  const accentColors: Record<string, string> = {
    teal: overrides.accentColor || '#5eead4',
    amber: '#fbbf24',
    blue: '#60a5fa',
    green: '#4ade80',
  }

  return (
    <AbsoluteFill style={{ padding: overrides.padding, color: '#f7efe6' }}>
      {scene.imageUrl && (
        <CompositionBackgroundImage src={scene.imageUrl} reveal={headReveal} brightness={overrides.brightness ?? 0.3} />
      )}
      <AbsoluteFill style={{ padding: overrides.padding, display: 'flex', flexDirection: 'column', gap: 32 }}>
        <div
          style={{
            fontFamily: FONT_HEADLINE,
            fontSize: headlineSize,
            lineHeight: 0.96,
            fontWeight: 'bold',
            opacity: headReveal,
            transform: `translateY(${interpolate(headReveal, [0, 1], [24, 0])}px)`,
          }}
        >
          {headline}
        </div>
        <div style={{ display: 'flex', gap: 20, flex: 1, alignItems: 'stretch' }}>
          {rawCols.map((col, ci) => {
            const colReveal = spring({
              frame: Math.max(frame - 10 - ci * 12, 0),
              fps,
              config: { damping: 18, stiffness: 100, mass: 0.9 },
            })
            const accent = accentColors[col.accent || 'teal'] || '#5eead4'
            const items = (col.items || []).map((it) =>
              typeof it === 'string' ? { label: it, icon: undefined } : { label: it.label || '', icon: it.icon }
            )
            return (
              <div
                key={ci}
                style={{
                  flex: 1,
                  padding: '28px 24px',
                  transform: `scale(${interpolate(colReveal, [0, 1], [0.92, 1])})`,
                  opacity: colReveal,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 16,
                }}
              >
                <div
                  style={{
                    fontFamily: FONT_DATA,
                    fontSize: CAPTION_SIZE,
                    letterSpacing: CAPTION_LETTER_SPACING,
                    textTransform: 'uppercase',
                    color: accent,
                    fontWeight: 700,
                  }}
                >
                  {col.title || `Column ${ci + 1}`}
                </div>
                {items.map((it, ii) => {
                  const itemReveal = spring({
                    frame: Math.max(frame - 16 - ci * 12 - ii * 6, 0),
                    fps,
                    config: { damping: 16, stiffness: 110, mass: 0.9 },
                  })
                  return (
                    <div
                      key={ii}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: 10,
                        opacity: itemReveal,
                        transform: `translateY(${interpolate(itemReveal, [0, 1], [12, 0])}px)`,
                      }}
                    >
                      <span
                        style={{
                          fontFamily: FONT_BODY,
                          fontSize: BODY_SIZE - 6,
                          lineHeight: BODY_LINE_HEIGHT,
                        }}
                      >
                        {it.label}
                      </span>
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  )
}

// ─── Template: closing_cta ───

function ClosingCtaTemplate({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const reveal = spring({ frame, fps, config: { damping: 22, stiffness: 110, mass: 0.8 } })
  const overrides = useStyleOverrides(scene, { brightness: 0.38, saturation: 0.9 })

  const headline = sceneStr(scene, 'headline', scene.onScreenText[0] || scene.title || '')
  const kicker = sceneStr(scene, 'kicker', '')
  const caption = sceneStr(scene, 'caption', '')
  const bullets = sceneArr(scene, 'bullets')
  const effectiveBullets = bullets.length > 0 ? bullets : scene.onScreenText.slice(1, 5)

  // 80% of (1664 - 2*padding) = ~1190px centered
  const headlineSize = useHeadlineFontSize(headline, 1190, 80 * overrides.textScale)

  return (
    <AbsoluteFill style={{ color: '#fff7f0' }}>
      {scene.imageUrl && (
        <CompositionBackgroundImage
          src={scene.imageUrl}
          reveal={reveal}
          brightness={overrides.brightness ?? 0.38}
          saturation={overrides.saturation ?? 0.9}
          scrimGradient="radial-gradient(ellipse at 50% 50%, rgba(3,5,10,0.85) 0%, rgba(3,5,10,0.6) 60%, transparent 100%)"
        />
      )}
      <AbsoluteFill
        style={{
          padding: overrides.padding,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 24,
        }}
      >
        {kicker ? (
          <div
            style={{
              padding: '8px 16px',
              borderRadius: 999,
              background: 'rgba(255,255,255,0.08)',
              fontFamily: FONT_DATA,
              fontSize: CAPTION_SIZE,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              opacity: interpolate(reveal, [0, 0.3], [0, 1]),
            }}
          >
            {kicker}
          </div>
        ) : null}
        <div
          style={{
            fontFamily: FONT_HEADLINE,
            fontSize: headlineSize,
            lineHeight: 0.96,
            fontWeight: 'bold',
            textAlign: 'center',
            maxWidth: '80%',
            transform: `scale(${interpolate(reveal, [0, 1], [0.88, 1])})`,
            opacity: reveal,
          }}
        >
          {headline}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 8 }}>
          {effectiveBullets.map((item, i) => {
            const itemReveal = spring({
              frame: Math.max(frame - 12 - i * 10, 0),
              fps,
              config: { damping: 16, stiffness: 110, mass: 0.9 },
            })
            return (
              <div
                key={`${item}-${i}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  opacity: itemReveal,
                  transform: `translateY(${interpolate(itemReveal, [0, 1], [16, 0])}px)`,
                }}
              >
                <span
                  style={{
                    fontFamily: FONT_BODY,
                    fontSize: BODY_SIZE,
                    lineHeight: BODY_LINE_HEIGHT,
                  }}
                >
                  {item}
                </span>
              </div>
            )
          })}
        </div>
        {caption ? (
          <div
            style={{
              marginTop: 12,
              fontFamily: FONT_CAPTION,
              fontSize: BODY_SIZE - 4,
              color: 'rgba(255,245,236,0.6)',
              opacity: interpolate(reveal, [0.4, 1], [0, 1]),
            }}
          >
            {caption}
          </div>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  )
}

// ─── Template: clinical_explanation ───

function ClinicalExplanationTemplate({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const reveal = spring({ frame, fps, config: { damping: 20, stiffness: 100, mass: 0.9 } })
  const overrides = useStyleOverrides(scene, { brightness: 0.42, saturation: 0.85 })

  const headline = sceneStr(scene, 'headline', scene.onScreenText[0] || scene.title || '')
  const body = sceneStr(scene, 'body', scene.onScreenText.slice(1, 3).join(' ') || '')
  const caption = sceneStr(scene, 'caption', '')

  // 52% of (1664 - 2*padding) = ~773px
  const headlineSize = useHeadlineFontSize(headline, 773, 72 * overrides.textScale)
  const bodySize = useBodyFontSize(body, 773, 4)
  const p = scene.composition?.props as Record<string, unknown> | undefined
  const labels = (p?.labels ?? []) as Array<{ text?: string; region?: string }>

  return (
    <AbsoluteFill style={{ color: '#f7efe6' }}>
      {scene.imageUrl && (
        <CompositionBackgroundImage
          src={scene.imageUrl}
          reveal={reveal}
          brightness={overrides.brightness ?? 0.42}
          saturation={overrides.saturation ?? 0.85}
          scrimGradient="linear-gradient(90deg, rgba(3,5,10,0.92) 0%, rgba(3,5,10,0.6) 50%, transparent 70%)"
        />
      )}
      <AbsoluteFill style={{ padding: overrides.padding, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
        <div style={{ maxWidth: '52%', display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div
            style={{
              fontFamily: FONT_HEADLINE,
              fontSize: headlineSize,
              lineHeight: 0.94,
              fontWeight: 'bold',
              transform: `translateX(${interpolate(reveal, [0, 1], [-32, 0])}px)`,
              opacity: reveal,
            }}
          >
            {headline}
          </div>
          {body ? (
            <div
              style={{
                fontFamily: FONT_BODY,
                fontSize: bodySize,
                lineHeight: BODY_LINE_HEIGHT,
                color: 'rgba(255,244,234,0.82)',
                opacity: interpolate(reveal, [0.15, 1], [0, 1]),
              }}
            >
              {body}
            </div>
          ) : null}
          {caption ? (
            <div
              style={{
                fontFamily: FONT_DATA,
                fontSize: LABEL_SIZE,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: overrides.accentColor || '#5eead4',
                opacity: interpolate(reveal, [0.3, 1], [0, 1]),
              }}
            >
              {caption}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
      {/* Floating label text over the image side (no chrome -- background provides visual pills) */}
      {labels.map((lbl, i) => {
        const lblReveal = spring({
          frame: Math.max(frame - 14 - i * 12, 0),
          fps,
          config: { damping: 18, stiffness: 100, mass: 0.9 },
        })
        const regionPos: Record<string, React.CSSProperties> = {
          'top-left': { top: 120, right: 420 },
          'top-center': { top: 120, right: 240 },
          'top-right': { top: 120, right: 100 },
          'center-left': { top: 320, right: 420 },
          'center': { top: 320, right: 260 },
          'center-right': { top: 320, right: 100 },
          'bottom-left': { top: 520, right: 420 },
          'bottom-center': { top: 520, right: 260 },
          'bottom-right': { top: 520, right: 100 },
        }
        const pos = regionPos[lbl.region || 'center'] || regionPos['center']
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              ...pos,
              padding: '8px 16px',
              fontFamily: FONT_BODY,
              fontSize: CAPTION_SIZE,
              color: overrides.accentColor || '#5eead4',
              transform: `scale(${interpolate(lblReveal, [0, 1], [0.8, 1])})`,
              opacity: lblReveal,
            }}
          >
            {lbl.text || ''}
          </div>
        )
      })}
    </AbsoluteFill>
  )
}

// ─── Template: metric_improvement ───

function MetricImprovementTemplate({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const reveal = spring({ frame, fps, config: { damping: 20, stiffness: 100, mass: 0.9 } })
  const overrides = useStyleOverrides(scene, { brightness: 0.35 })

  const p = scene.composition?.props as Record<string, unknown> | undefined
  const headline = sceneStr(scene, 'headline', scene.title || '')
  // centered layout, ~1400px
  const headlineSize = useHeadlineFontSize(headline, 1400, 56 * overrides.textScale)
  const metricName = sceneStr(scene, 'metric_name', '')
  const before = (p?.before ?? {}) as { value?: string; label?: string }
  const after = (p?.after ?? {}) as { value?: string; label?: string }
  const delta = sceneStr(scene, 'delta', '')
  const caption = sceneStr(scene, 'caption', '')
  const direction = sceneStr(scene, 'direction', 'improvement')
  const stages = (p?.stages ?? []) as Array<{ value?: string; label?: string }>

  const panels = stages.length >= 2 ? stages : [before, after].filter(s => s.value)
  const isImprovement = direction === 'improvement'
  const accentTeal = overrides.accentColor || '#5eead4'
  const deltaColor = isImprovement ? accentTeal : direction === 'decline' ? '#f87171' : '#fbbf24'

  // Split panel values into numeric part (large) and qualifier (small).
  // Values come as "6.9 µV (below target)" — display "6.9 µV" large, "(below target)" small.
  const splitPanelValue = (v: string) => {
    const m = v.match(/^([^(]+?)(\s*\(.*\)\s*)$/)
    return m ? { num: m[1].trim(), qual: m[2].trim() } : { num: v, qual: '' }
  }
  const panelParts = panels.map(p => splitPanelValue(p.value || ''))
  const longestPanelNum = panelParts.reduce((a, b) => (b.num.length > a.length ? b.num : a), '')
  const panelValueSize = useDataFontSize(longestPanelNum, 320, 52 * overrides.textScale)
  const metricNameSize = useDataFontSize(metricName, 600, (CAPTION_SIZE + 2) * overrides.textScale)
  const deltaSize = useDataFontSize(delta, 400, (BODY_SIZE - 6) * overrides.textScale)
  const captionSize = useCaptionFontSize(caption, 1200, 2, (BODY_SIZE - 6) * overrides.textScale)

  return (
    <AbsoluteFill style={{ color: '#f7efe6' }}>
      {scene.imageUrl && (
        <CompositionBackgroundImage src={scene.imageUrl} reveal={reveal} brightness={overrides.brightness ?? 0.35} />
      )}
      <AbsoluteFill style={{ padding: overrides.padding, display: 'flex', flexDirection: 'column', gap: 28, alignItems: 'center', justifyContent: 'center' }}>
        <div
          style={{
            fontFamily: FONT_HEADLINE,
            fontSize: headlineSize,
            lineHeight: 0.96,
            fontWeight: 'bold',
            textAlign: 'center',
            opacity: reveal,
            transform: `translateY(${interpolate(reveal, [0, 1], [20, 0])}px)`,
          }}
        >
          {headline}
        </div>
        {metricName ? (
          <div
            style={{
              fontFamily: FONT_DATA,
              fontSize: metricNameSize,
              letterSpacing: CAPTION_LETTER_SPACING,
              textTransform: 'uppercase',
              color: accentTeal,
              opacity: interpolate(reveal, [0.1, 0.6], [0, 1]),
            }}
          >
            {metricName}
          </div>
        ) : null}
        <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
          {panels.map((panel, pi) => {
            const panelReveal = spring({
              frame: Math.max(frame - 6 - pi * 12, 0),
              fps,
              config: { damping: 18, stiffness: 100, mass: 0.9 },
            })
            return (
              <React.Fragment key={pi}>
                <div
                  style={{
                    padding: '32px 40px',
                    textAlign: 'center',
                    minWidth: 180,
                    transform: `scale(${interpolate(panelReveal, [0, 1], [0.88, 1])})`,
                    opacity: panelReveal,
                  }}
                >
                  <div style={{ fontFamily: FONT_DATA, fontSize: panelValueSize, lineHeight: 1, fontWeight: 700 }}>
                    {panelParts[pi].num || '\u2014'}
                  </div>
                  {panelParts[pi].qual ? (
                    <div style={{ marginTop: 6, fontFamily: FONT_CAPTION, fontSize: CAPTION_SIZE - 2, color: 'rgba(255,244,234,0.5)' }}>
                      {panelParts[pi].qual}
                    </div>
                  ) : null}
                  {panel.label ? (
                    <div
                      style={{
                        marginTop: 8,
                        fontFamily: FONT_CAPTION,
                        fontSize: CAPTION_SIZE + 2,
                        color: 'rgba(255,244,234,0.6)',
                      }}
                    >
                      {panel.label}
                    </div>
                  ) : null}
                </div>
              </React.Fragment>
            )
          })}
        </div>
        {delta ? (
          <div
            style={{
              fontFamily: FONT_DATA,
              fontSize: deltaSize,
              color: deltaColor,
              fontWeight: 700,
              opacity: interpolate(reveal, [0.3, 1], [0, 1]),
            }}
          >
            {delta}
          </div>
        ) : null}
        {caption ? (
          <div
            style={{
              fontFamily: FONT_CAPTION,
              fontSize: captionSize,
              color: 'rgba(255,244,234,0.6)',
              opacity: interpolate(reveal, [0.4, 1], [0, 1]),
            }}
          >
            {caption}
          </div>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  )
}

// ─── Template: brain_region_focus ───

function BrainRegionFocusTemplate({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const reveal = spring({ frame, fps, config: { damping: 20, stiffness: 100, mass: 0.9 } })
  const overrides = useStyleOverrides(scene, { brightness: 0.5, saturation: 0.9 })

  const headline = sceneStr(scene, 'headline', scene.title || '')
  const caption = sceneStr(scene, 'caption', '')
  const headlineSize = useHeadlineFontSize(headline, 1400, 60 * overrides.textScale)
  const p = scene.composition?.props as Record<string, unknown> | undefined
  const regions = (p?.regions ?? []) as Array<{ name?: string; value?: string; status?: string }>

  // fitText: compute from longest region name and value (hooks can't be in .map)
  const longestRegionName = regions.reduce((a, b) => ((b.name || '').length > a.length ? b.name || '' : a), '')
  const longestRegionValue = regions.reduce((a, b) => ((b.value || '').length > a.length ? b.value || '' : a), '')
  const regionNameSize = useDataFontSize(longestRegionName, 200, 34 * overrides.textScale, FONT_BODY)
  const regionValueSize = useDataFontSize(longestRegionValue, 180, 30 * overrides.textScale)

  // Pixel coordinates mapped to the actual brain_region_focus_topdown.png image (1664x928).
  // The image shows a frontal brain view centered at ~(832, 400).
  // Brain spans roughly x:380-1280, y:100-720.
  // Coordinates place label anchors on the anatomical region in the actual image.
  const regionPositions: Record<string, { top: number; left: number }> = {
    // Lobe-level regions (placed at lobe centers in the image)
    frontal:          { top: 200, left: 832 },   // upper-center, frontal lobe mass
    prefrontal:       { top: 140, left: 832 },   // very top of visible brain, forehead area
    central:          { top: 310, left: 832 },   // mid-brain, central sulcus area
    parietal:         { top: 420, left: 832 },   // lower-center, behind central
    'central-parietal': { top: 365, left: 832 }, // between central and parietal
    temporal:         { top: 380, left: 480 },   // left temporal lobe (side of brain)
    occipital:        { top: 580, left: 832 },   // bottom-back, lowest visible lobe
    // Individual 10-20 electrodes (placed at anatomical positions)
    fp1: { top: 135, left: 680 },  // left frontal pole
    fp2: { top: 135, left: 984 },  // right frontal pole
    f3:  { top: 210, left: 620 },  // left frontal
    f4:  { top: 210, left: 1044 }, // right frontal
    fz:  { top: 195, left: 832 },  // midline frontal
    c3:  { top: 310, left: 560 },  // left central
    c4:  { top: 310, left: 1104 }, // right central
    cz:  { top: 290, left: 832 },  // vertex / midline central
    t3:  { top: 350, left: 430 },  // left temporal
    t4:  { top: 350, left: 1234 }, // right temporal
    p3:  { top: 430, left: 620 },  // left parietal
    p4:  { top: 430, left: 1044 }, // right parietal
    pz:  { top: 420, left: 832 },  // midline parietal
    o1:  { top: 560, left: 700 },  // left occipital
    o2:  { top: 560, left: 964 },  // right occipital
    oz:  { top: 580, left: 832 },  // midline occipital
  }

  const statusColors: Record<string, string> = {
    improved: overrides.accentColor || '#5eead4',
    stable: '#60a5fa',
    declined: '#fbbf24',
    flagged: '#f87171',
  }

  return (
    <AbsoluteFill style={{ color: '#f7efe6' }}>
      {scene.imageUrl && (
        <CompositionBackgroundImage
          src={scene.imageUrl}
          reveal={reveal}
          brightness={overrides.brightness ?? 0.5}
          saturation={overrides.saturation ?? 0.9}
          scrimGradient="linear-gradient(180deg, rgba(3,5,10,0.7) 0%, rgba(3,5,10,0.3) 40%, rgba(3,5,10,0.3) 60%, rgba(3,5,10,0.7) 100%)"
        />
      )}
      <AbsoluteFill style={{ padding: overrides.padding }}>
        <div
          style={{
            fontFamily: FONT_HEADLINE,
            fontSize: headlineSize,
            lineHeight: 0.96,
            fontWeight: 'bold',
            opacity: reveal,
            transform: `translateY(${interpolate(reveal, [0, 1], [20, 0])}px)`,
          }}
        >
          {headline}
        </div>
      </AbsoluteFill>
      {/* region labels */}
      {regions.map((reg, i) => {
        const regionReveal = spring({
          frame: Math.max(frame - 12 - i * 10, 0),
          fps,
          config: { damping: 16, stiffness: 100, mass: 0.9 },
        })
        const nameKey = (reg.name || '').toLowerCase().replace(/[\s_-]+/g, '-').replace(/-/g, '')
        const pos = Object.entries(regionPositions).find(([k]) =>
          nameKey.includes(k) || k.includes(nameKey)
        )?.[1] || { top: 340 + i * 70, left: 780 }
        const color = statusColors[reg.status || 'stable'] || '#60a5fa'

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              top: pos.top,
              left: pos.left,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              transform: `scale(${interpolate(regionReveal, [0, 1], [0.7, 1])})`,
              opacity: regionReveal,
            }}
          >
            <div
              style={{
                padding: '10px 20px',
              }}
            >
              <div
                style={{
                  fontFamily: FONT_BODY,
                  fontSize: regionNameSize,
                  fontWeight: 600,
                  color: '#fff',
                }}
              >
                {reg.name || ''}
              </div>
              {reg.value ? (
                <div
                  style={{
                    fontFamily: FONT_DATA,
                    fontSize: regionValueSize,
                    color,
                    marginTop: 4,
                  }}
                >
                  {reg.value}
                </div>
              ) : null}
            </div>
          </div>
        )
      })}
      {caption ? (
        <div
          style={{
            position: 'absolute',
            bottom: overrides.padding,
            left: overrides.padding,
            fontFamily: FONT_CAPTION,
            fontSize: CAPTION_SIZE + 2,
            color: 'rgba(255,244,234,0.6)',
            opacity: interpolate(reveal, [0.5, 1], [0, 1]),
          }}
        >
          {caption}
        </div>
      ) : null}
    </AbsoluteFill>
  )
}

// ─── Template: metric_comparison ───

function MetricComparisonTemplate({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const reveal = spring({ frame, fps, config: { damping: 20, stiffness: 100, mass: 0.9 } })
  const overrides = useStyleOverrides(scene, { brightness: 0.35 })

  const headline = sceneStr(scene, 'headline', scene.title || '')
  const caption = sceneStr(scene, 'caption', '')
  const headlineSize = useHeadlineFontSize(headline, 1400, 60 * overrides.textScale)
  const p = scene.composition?.props as Record<string, unknown> | undefined
  const left = (p?.left ?? {}) as { title?: string; accent?: string; items?: string[] }
  const right = (p?.right ?? {}) as { title?: string; accent?: string; items?: string[] }

  const accentColors: Record<string, string> = {
    teal: overrides.accentColor || '#5eead4', amber: '#fbbf24', blue: '#60a5fa', green: '#4ade80',
  }
  const leftColor = accentColors[left.accent || 'amber'] || '#fbbf24'
  const rightColor = accentColors[right.accent || 'teal'] || (overrides.accentColor || '#5eead4')

  // fitText: compute from longest item across both sides (hooks can't be in .map)
  const allItems = [...(left.items || []), ...(right.items || [])]
  const longestItem = allItems.reduce((a, b) => (b.length > a.length ? b : a), '')
  const sideItemSize = Math.max(
    useCaptionFontSize(longestItem, 680, 3, (BODY_SIZE - 2) * overrides.textScale),
    16,
  )

  const renderSide = (side: typeof left, color: string, fromX: number) => (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div
        style={{
          fontFamily: FONT_DATA,
          fontSize: CAPTION_SIZE,
          letterSpacing: CAPTION_LETTER_SPACING,
          textTransform: 'uppercase',
          color,
          fontWeight: 700,
        }}
      >
        {side.title || ''}
      </div>
      {(side.items || []).map((item, i) => {
        const itemReveal = spring({
          frame: Math.max(frame - 12 - i * 8, 0),
          fps,
          config: { damping: 16, stiffness: 110, mass: 0.9 },
        })
        return (
          <div
            key={i}
            style={{
              padding: '14px 18px',
              fontFamily: FONT_BODY,
              fontSize: sideItemSize,
              lineHeight: BODY_LINE_HEIGHT,
              transform: `translateX(${interpolate(itemReveal, [0, 1], [fromX, 0])}px)`,
              opacity: itemReveal,
            }}
          >
            {item}
          </div>
        )
      })}
    </div>
  )

  return (
    <AbsoluteFill style={{ color: '#f7efe6' }}>
      {scene.imageUrl && (
        <CompositionBackgroundImage src={scene.imageUrl} reveal={reveal} brightness={overrides.brightness ?? 0.35} />
      )}
      <AbsoluteFill style={{ padding: overrides.padding, display: 'flex', flexDirection: 'column', gap: 32 }}>
        <div
          style={{
            fontFamily: FONT_HEADLINE,
            fontSize: headlineSize,
            lineHeight: 0.96,
            fontWeight: 'bold',
            opacity: reveal,
            transform: `translateY(${interpolate(reveal, [0, 1], [20, 0])}px)`,
          }}
        >
          {headline}
        </div>
        <div style={{ display: 'flex', gap: 24, flex: 1 }}>
          {renderSide(left, leftColor, -24)}
          {renderSide(right, rightColor, 24)}
        </div>
        {caption ? (
          <div
            style={{
              fontFamily: FONT_CAPTION,
              fontSize: CAPTION_SIZE + 2,
              color: 'rgba(255,244,234,0.6)',
              opacity: interpolate(reveal, [0.5, 1], [0, 1]),
              textAlign: 'center',
            }}
          >
            {caption}
          </div>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  )
}

// ─── Template: timeline_progression ───

function TimelineProgressionTemplate({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const reveal = spring({ frame, fps, config: { damping: 20, stiffness: 100, mass: 0.9 } })
  const overrides = useStyleOverrides(scene, { brightness: 0.3 })

  const headline = sceneStr(scene, 'headline', scene.title || '')
  const headlineSize = useHeadlineFontSize(headline, 1400, 60 * overrides.textScale)
  const spanLabel = sceneStr(scene, 'span_label', '')
  const caption = sceneStr(scene, 'caption', '')
  const p = scene.composition?.props as Record<string, unknown> | undefined
  type TimelineMarker = { label?: string; date?: string; annotation?: string; status?: string }
  const markers = (p?.markers ?? []) as TimelineMarker[]
  const effectiveMarkers: TimelineMarker[] = markers.length > 0 ? markers : scene.onScreenText.slice(1).map(t => ({ label: t }))

  const markerCount = Math.max(effectiveMarkers.length, 1)
  const trackLeft = 140
  const trackRight = 1520
  const trackWidth = trackRight - trackLeft
  const slotWidth = markerCount > 1 ? trackWidth / (markerCount - 1) : trackWidth

  // fitText: compute from longest marker label and date (hooks can't be in .map)
  const longestLabel = effectiveMarkers.reduce((a, b) => ((b.label || '').length > a.length ? b.label || '' : a), '')
  const longestDate = effectiveMarkers.reduce((a, b) => ((b.date || '').length > a.length ? b.date || '' : a), '')
  const markerLabelSize = useDataFontSize(longestLabel, slotWidth * 0.9, CAPTION_SIZE * overrides.textScale, FONT_BODY)
  const markerDateSize = useDataFontSize(longestDate, slotWidth * 0.9, (LABEL_SIZE - 2) * overrides.textScale)

  return (
    <AbsoluteFill style={{ color: '#f7efe6' }}>
      {scene.imageUrl && (
        <CompositionBackgroundImage src={scene.imageUrl} reveal={reveal} brightness={overrides.brightness ?? 0.3} />
      )}
      <AbsoluteFill style={{ padding: overrides.padding, display: 'flex', flexDirection: 'column', gap: 36 }}>
        <div
          style={{
            fontFamily: FONT_HEADLINE,
            fontSize: headlineSize,
            lineHeight: 0.96,
            fontWeight: 'bold',
            opacity: reveal,
            transform: `translateY(${interpolate(reveal, [0, 1], [20, 0])}px)`,
          }}
        >
          {headline}
        </div>
      </AbsoluteFill>
      {/* marker text labels -- track dots and line come from the background image */}
      {effectiveMarkers.map((m, i) => {
        const x = trackLeft + (trackWidth / Math.max(markerCount - 1, 1)) * i
        const dotReveal = spring({
          frame: Math.max(frame - 8 - i * 6, 0),
          fps,
          config: { damping: 16, stiffness: 110, mass: 0.9 },
        })
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              top: 468,
              left: x,
              transform: 'translateX(-50%)',
              textAlign: 'center',
              opacity: dotReveal,
            }}
          >
            <div
              style={{
                fontFamily: FONT_BODY,
                fontSize: markerLabelSize,
                fontWeight: 600,
              }}
            >
              {m.label || ''}
            </div>
            {m.date ? (
              <div
                style={{
                  fontFamily: FONT_DATA,
                  fontSize: markerDateSize,
                  color: 'rgba(255,244,234,0.5)',
                  marginTop: 4,
                }}
              >
                {m.date}
              </div>
            ) : null}
            {m.annotation ? (
              <div
                style={{
                  position: 'absolute',
                  top: -48,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  fontFamily: FONT_CAPTION,
                  fontSize: LABEL_SIZE - 2,
                  color: 'rgba(255,244,234,0.5)',
                  whiteSpace: 'nowrap',
                }}
              >
                {m.annotation}
              </div>
            ) : null}
          </div>
        )
      })}
      {/* span label arc */}
      {spanLabel ? (
        <div
          style={{
            position: 'absolute',
            top: 370,
            left: trackLeft,
            width: trackWidth,
            textAlign: 'center',
            fontFamily: FONT_CAPTION,
            fontSize: CAPTION_SIZE + 2,
            color: 'rgba(255,244,234,0.5)',
            opacity: interpolate(reveal, [0.5, 1], [0, 1]),
          }}
        >
          {spanLabel}
        </div>
      ) : null}
      {caption ? (
        <div
          style={{
            position: 'absolute',
            bottom: overrides.padding,
            left: overrides.padding,
            fontFamily: FONT_CAPTION,
            fontSize: CAPTION_SIZE + 2,
            color: 'rgba(255,244,234,0.6)',
            opacity: interpolate(reveal, [0.5, 1], [0, 1]),
          }}
        >
          {caption}
        </div>
      ) : null}
    </AbsoluteFill>
  )
}

// ─── Template: analogy_metaphor ───

function AnalogyMetaphorTemplate({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const reveal = spring({ frame, fps, config: { damping: 20, stiffness: 100, mass: 0.9 } })
  const overrides = useStyleOverrides(scene, { brightness: 0.35, saturation: 0.8 })

  const headline = sceneStr(scene, 'headline', scene.title || '')
  const caption = sceneStr(scene, 'caption', '')
  const headlineSize = useHeadlineFontSize(headline, 1400, 60 * overrides.textScale)
  const p = scene.composition?.props as Record<string, unknown> | undefined
  const left = (p?.left ?? {}) as {
    title?: string; items?: string[]; accent?: string; direction?: string; summary?: string
  }
  const right = (p?.right ?? {}) as {
    title?: string; items?: string[]; accent?: string; direction?: string; summary?: string
  }

  const accentColors: Record<string, string> = {
    teal: overrides.accentColor || '#5eead4', amber: '#fbbf24', blue: '#60a5fa', green: '#4ade80',
  }

  const renderAnalogyPanel = (side: typeof left, fromX: number) => {
    const color = accentColors[side.accent || 'teal'] || (overrides.accentColor || '#5eead4')
    const panelReveal = spring({
      frame: Math.max(frame - 8, 0),
      fps,
      config: { damping: 18, stiffness: 100, mass: 0.9 },
    })
    return (
      <div
        style={{
          flex: 1,
          padding: '28px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
          transform: `translateX(${interpolate(panelReveal, [0, 1], [fromX, 0])}px)`,
          opacity: panelReveal,
        }}
      >
        <div
          style={{
            fontFamily: FONT_DATA,
            fontSize: CAPTION_SIZE + 2,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color,
            fontWeight: 700,
          }}
        >
          {side.title || ''}
        </div>
        {(side.items || []).map((item, i) => {
          const itemReveal = spring({
            frame: Math.max(frame - 16 - i * 8, 0),
            fps,
            config: { damping: 16, stiffness: 110, mass: 0.9 },
          })
          return (
            <div
              key={i}
              style={{
                fontFamily: FONT_BODY,
                fontSize: BODY_SIZE - 6,
                lineHeight: BODY_LINE_HEIGHT,
                opacity: itemReveal,
                transform: `translateY(${interpolate(itemReveal, [0, 1], [8, 0])}px)`,
              }}
            >
              {item}
            </div>
          )
        })}
        {side.summary ? (
          <div
            style={{
              marginTop: 8,
              fontFamily: FONT_DATA,
              fontSize: LABEL_SIZE,
              fontWeight: 700,
              color,
              alignSelf: 'flex-start',
              opacity: interpolate(reveal, [0.3, 1], [0, 1]),
            }}
          >
            {side.summary}
          </div>
        ) : null}
      </div>
    )
  }

  return (
    <AbsoluteFill style={{ color: '#f7efe6' }}>
      {scene.imageUrl && (
        <CompositionBackgroundImage
          src={scene.imageUrl}
          reveal={reveal}
          brightness={overrides.brightness ?? 0.35}
          saturation={overrides.saturation ?? 0.8}
          scrimGradient="linear-gradient(180deg, rgba(3,5,10,0.75) 0%, rgba(3,5,10,0.5) 30%, rgba(3,5,10,0.5) 70%, rgba(3,5,10,0.75) 100%)"
        />
      )}
      <AbsoluteFill style={{ padding: overrides.padding, display: 'flex', flexDirection: 'column', gap: 28 }}>
        <div
          style={{
            fontFamily: FONT_HEADLINE,
            fontSize: headlineSize,
            lineHeight: 0.96,
            fontWeight: 'bold',
            textAlign: 'center',
            opacity: reveal,
            transform: `translateY(${interpolate(reveal, [0, 1], [20, 0])}px)`,
          }}
        >
          {headline}
        </div>
        <div style={{ display: 'flex', gap: 24, flex: 1, alignItems: 'stretch' }}>
          {renderAnalogyPanel(left, -32)}
          {renderAnalogyPanel(right, 32)}
        </div>
        {caption ? (
          <div
            style={{
              fontFamily: FONT_CAPTION,
              fontSize: CAPTION_SIZE + 2,
              color: 'rgba(255,244,234,0.6)',
              textAlign: 'center',
              opacity: interpolate(reveal, [0.5, 1], [0, 1]),
            }}
          >
            {caption}
          </div>
        ) : null}
      </AbsoluteFill>
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
          fontFamily: FONT_DATA,
          fontSize: CAPTION_SIZE,
          letterSpacing: CAPTION_LETTER_SPACING,
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
                fontFamily: FONT_BODY,
                fontSize: BODY_SIZE - 6,
                lineHeight: BODY_LINE_HEIGHT,
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

type DataStagePoint = {
  x: string
  y: number | null
  label?: string
}

type DataStageSeries = {
  id: string
  label: string
  type: 'bar' | 'line'
  points: DataStagePoint[]
}

type Polarity = 'lower_is_better' | 'higher_is_better' | 'in_range_is_better' | null

type DataStagePanel = {
  id: string
  title: string
  series: DataStageSeries[]
  referenceBands: DataStageReferenceBand[]
  yAxisLabel: string
  polarity?: Polarity
}

type DataStageReferenceBand = {
  id: string
  label: string
  yMin: number
  yMax: number
  xRange?: [string, string] | null
}

type DataStageCallout = {
  id: string
  label: string
  x?: string
  y?: number
  fromX?: string
  toX?: string
}

type DataStageTheme = {
  background: string
  panel: string
  panelEdge: string
  grid: string
  gridStrong: string
  text: string
  muted: string
  primary: string
  secondary: string
  accent: string
  band: string
  bandEdge: string
  chip: string
  callout: string
}

function asFiniteNumber(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null
  }
  if (typeof value === 'string' && value.trim() === '') {
    return null
  }
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function formatDataStageValue(value: number): string {
  const absValue = Math.abs(value)
  const decimals = absValue >= 100 || Number.isInteger(value) ? 0 : absValue >= 10 ? 1 : 2
  return value.toFixed(decimals).replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1')
}

function clampNumber(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

const DATA_STAGE_COMPARISON_RE = /(-?\d+(?:\.\d+)?)\s*(?:→|->|=>|to)\s*(-?\d+(?:\.\d+)?)/i
const DATA_STAGE_RANGE_RE = /(-?\d+(?:\.\d+)?)\s*(?:to|[–—-])\s*(-?\d+(?:\.\d+)?)/i

function dataStageSourceLines(scene: RemotionScene): string[] {
  const data = (scene.composition?.data ?? {}) as Record<string, unknown>
  const fromDataPoints = Array.isArray(data.data_points) ? (data.data_points as unknown[]) : []
  return uniqueStrings([
    ...fromDataPoints.map((entry) => String(entry || '').trim()),
    ...scene.onScreenText.map((entry) => String(entry || '').trim()),
    scene.title || '',
  ])
}

function inferLegacyDataStageSeries(scene: RemotionScene, requestedType: 'bar' | 'line'): DataStageSeries[] {
  const comparisonLines = dataStageSourceLines(scene)
    .filter((line) => DATA_STAGE_COMPARISON_RE.test(line))
    .slice(0, requestedType === 'line' ? 3 : 1)

  const inferred = comparisonLines.flatMap((line, index) => {
    const match = line.match(DATA_STAGE_COMPARISON_RE)
    if (!match) {
      return []
    }

    const firstValue = asFiniteNumber(match[1])
    const secondValue = asFiniteNumber(match[2])
    if (firstValue === null || secondValue === null) {
      return []
    }

    const labelPrefix = line.includes(':')
      ? line.split(':', 1)[0].trim()
      : `${scene.title || 'Series'} ${index + 1}`

    return [{
      id: `legacy-inferred-series-${index + 1}`,
      label: labelPrefix || `${scene.title || 'Series'} ${index + 1}`,
      type: requestedType,
      points: [
        { x: 'Session 1', y: firstValue },
        { x: 'Session 2', y: secondValue },
      ],
    }]
  })

  return inferred
}

function inferLegacyDataStageValueLabel(scene: RemotionScene): string | null {
  const comparisonLine = dataStageSourceLines(scene).find((line) => DATA_STAGE_COMPARISON_RE.test(line))
  if (!comparisonLine) {
    return null
  }

  const lowered = comparisonLine.toLowerCase()
  if (lowered.includes(' ms')) {
    return 'Milliseconds'
  }
  if (lowered.includes(' sec') || lowered.includes(' second')) {
    return 'Seconds'
  }
  if (lowered.includes('ratio')) {
    return 'Ratio'
  }
  if (lowered.includes('coherence') || scene.title.toLowerCase().includes('connectivity')) {
    return 'Coherence'
  }
  if (lowered.includes('voltage') || lowered.includes('uv') || lowered.includes('µv')) {
    return 'Voltage'
  }
  return null
}

function normalizeDataStageSeries(scene: RemotionScene): DataStageSeries[] {
  const data = (scene.composition?.data ?? {}) as Record<string, unknown>
  const candidateSeries = Array.isArray(data.series) ? (data.series as unknown[]) : []
  const normalized = candidateSeries.flatMap((entry, index) => {
    if (!entry || typeof entry !== 'object') {
      return []
    }

    const item = entry as Record<string, unknown>
    const rawPoints = Array.isArray(item.points) ? (item.points as unknown[]) : []
    const points = rawPoints.flatMap((pointEntry) => {
      if (!pointEntry || typeof pointEntry !== 'object') {
        return []
      }
      const point = pointEntry as Record<string, unknown>
      const label = String(point.x || '').trim()
      if (!label) {
        return []
      }
      return [{
        x: label,
        y: asFiniteNumber(point.y),
        label: String(point.label || '').trim() || undefined,
      }]
    })

    if (points.length === 0) {
      return []
    }

    return [{
      id: String(item.id || `series-${index + 1}`),
      label: String(item.label || scene.title || `Series ${index + 1}`).trim(),
      type: (String(item.type || '').trim() === 'bar' ? 'bar' : 'line') as 'bar' | 'line',
      points,
    }]
  })

  if (normalized.length > 0 && normalized.some((series) => series.points.some((point) => point.y !== null))) {
    return normalized
  }

  const inferredType = normalized[0]?.type ?? 'bar'
  const inferredSeries = inferLegacyDataStageSeries(scene, inferredType)
  if (inferredSeries.length > 0) {
    return inferredSeries
  }

  const fallbackPoints = (scene.onScreenText.length > 0 ? scene.onScreenText : [scene.title || 'Data point'])
    .slice(0, 4)
    .map((label, index, items) => ({
      x: `Beat ${index + 1}`,
      y: items.length - index,
      label,
    }))

  return [{
    id: 'fallback-series',
    label: scene.title || 'Data stage',
    type: 'bar',
    points: fallbackPoints,
  }]
}

function normalizeDataStageReferenceBands(scene: RemotionScene): DataStageReferenceBand[] {
  const data = (scene.composition?.data ?? {}) as Record<string, unknown>
  const candidateBands = Array.isArray(data.referenceBands) ? (data.referenceBands as unknown[]) : []
  const normalizedBands = candidateBands.flatMap((entry, index) => {
    if (!entry || typeof entry !== 'object') {
      return []
    }

    const item = entry as Record<string, unknown>
    const yMin = asFiniteNumber(item.yMin)
    const yMax = asFiniteNumber(item.yMax)
    if (yMin === null || yMax === null) {
      return []
    }

    const xRange = Array.isArray(item.xRange) && item.xRange.length === 2
      ? [String(item.xRange[0] || '').trim(), String(item.xRange[1] || '').trim()] as [string, string]
      : null

    return [{
      id: String(item.id || `band-${index + 1}`),
      label: String(item.label || '').trim() || 'Reference range',
      yMin,
      yMax,
      xRange: xRange && xRange[0] && xRange[1] ? xRange : null,
    }]
  })

  if (normalizedBands.length > 0) {
    return normalizedBands
  }

  const inferredRangeLine = dataStageSourceLines(scene).find((line) => {
    const lowered = line.toLowerCase()
    return (lowered.includes('target') || lowered.includes('reference') || lowered.includes('range')) && DATA_STAGE_RANGE_RE.test(line)
  })
  if (!inferredRangeLine) {
    return []
  }

  const match = inferredRangeLine.match(DATA_STAGE_RANGE_RE)
  const yMin = asFiniteNumber(match?.[1])
  const yMax = asFiniteNumber(match?.[2])
  if (yMin === null || yMax === null) {
    return []
  }

  return [{
    id: 'legacy-inferred-band',
    label: inferredRangeLine,
    yMin: Math.min(yMin, yMax),
    yMax: Math.max(yMin, yMax),
    xRange: null,
  }]
}

function normalizeDataStageCallouts(scene: RemotionScene): DataStageCallout[] {
  const data = (scene.composition?.data ?? {}) as Record<string, unknown>
  const candidateCallouts = Array.isArray(data.callouts) ? (data.callouts as unknown[]) : []
  return candidateCallouts.flatMap((entry, index) => {
    if (!entry || typeof entry !== 'object') {
      return []
    }

    const item = entry as Record<string, unknown>
    const label = String(item.label || '').trim()
    if (!label) {
      return []
    }

    return [{
      id: String(item.id || `callout-${index + 1}`),
      label,
      x: String(item.x || '').trim() || undefined,
      y: asFiniteNumber(item.y) ?? undefined,
      fromX: String(item.fromX || '').trim() || undefined,
      toX: String(item.toX || '').trim() || undefined,
    }]
  })
}

function resolveDataStageTheme(paletteName: string): DataStageTheme {
  const normalized = paletteName.trim().toLowerCase()
  if (normalized === 'amber_on_navy') {
    return {
      background: 'radial-gradient(circle at 18% 16%, rgba(255,188,122,0.22), transparent 32%), linear-gradient(180deg, #060b14 0%, #0b1627 52%, #0b1018 100%)',
      panel: 'rgba(7, 11, 20, 0.84)',
      panelEdge: 'rgba(255,255,255,0.10)',
      grid: 'rgba(255,255,255,0.08)',
      gridStrong: 'rgba(255,255,255,0.16)',
      text: '#fff6ec',
      muted: '#b3c0d9',
      primary: '#f6b66c',
      secondary: '#ffdfaa',
      accent: '#7fc7ff',
      band: 'rgba(129, 194, 255, 0.12)',
      bandEdge: 'rgba(129, 194, 255, 0.24)',
      chip: 'rgba(8, 13, 24, 0.78)',
      callout: 'rgba(8, 12, 21, 0.94)',
    }
  }

  if (normalized === 'teal_amber_on_charcoal') {
    return {
      background: 'radial-gradient(circle at 50% 16%, rgba(115,221,201,0.14), transparent 28%), linear-gradient(180deg, #060708 0%, #111417 50%, #090c12 100%)',
      panel: 'rgba(10, 12, 16, 0.84)',
      panelEdge: 'rgba(255,255,255,0.09)',
      grid: 'rgba(255,255,255,0.07)',
      gridStrong: 'rgba(255,255,255,0.14)',
      text: '#fff6ee',
      muted: '#bac4d1',
      primary: '#66d4c5',
      secondary: '#ffd2a1',
      accent: '#ff8e5a',
      band: 'rgba(121, 224, 179, 0.12)',
      bandEdge: 'rgba(121, 224, 179, 0.24)',
      chip: 'rgba(8, 10, 14, 0.78)',
      callout: 'rgba(9, 11, 15, 0.94)',
    }
  }

  if (normalized === 'multi_zone_on_charcoal') {
    return {
      background: 'radial-gradient(circle at 22% 18%, rgba(132,153,255,0.16), transparent 32%), linear-gradient(180deg, #06080d 0%, #10151e 50%, #0a0d13 100%)',
      panel: 'rgba(8, 11, 18, 0.84)',
      panelEdge: 'rgba(255,255,255,0.10)',
      grid: 'rgba(255,255,255,0.07)',
      gridStrong: 'rgba(255,255,255,0.15)',
      text: '#fbf4ed',
      muted: '#bac6d5',
      primary: '#80abff',
      secondary: '#ffd084',
      accent: '#ff8b76',
      band: 'rgba(122, 172, 255, 0.12)',
      bandEdge: 'rgba(122, 172, 255, 0.22)',
      chip: 'rgba(8, 11, 18, 0.8)',
      callout: 'rgba(8, 11, 18, 0.94)',
    }
  }

  return {
    background: 'radial-gradient(circle at 22% 18%, rgba(105,208,218,0.18), transparent 34%), linear-gradient(180deg, #050a12 0%, #091626 52%, #0b1018 100%)',
    panel: 'rgba(8, 12, 20, 0.84)',
    panelEdge: 'rgba(255,255,255,0.10)',
    grid: 'rgba(255,255,255,0.08)',
    gridStrong: 'rgba(255,255,255,0.16)',
    text: '#fff6ed',
    muted: '#b7c4da',
    primary: '#6fd7cb',
    secondary: '#a7cdff',
    accent: '#f8c99c',
    band: 'rgba(121, 224, 179, 0.12)',
    bandEdge: 'rgba(121, 224, 179, 0.24)',
    chip: 'rgba(8, 12, 20, 0.78)',
    callout: 'rgba(8, 12, 20, 0.94)',
  }
}

function uniqueStrings(values: string[]): string[] {
  const seen = new Set<string>()
  return values.flatMap((entry) => {
    const normalized = entry.trim()
    if (!normalized) {
      return []
    }
    const key = normalized.toLowerCase()
    if (seen.has(key)) {
      return []
    }
    seen.add(key)
    return [normalized]
  })
}

function resolveDataStageHeadlineLayout(headline: string, seriesCount: number) {
  const length = headline.trim().length
  if (seriesCount > 1) {
    return {
      fontSize: 56,
      lineHeight: 0.98,
      maxWidth: '74%',
    }
  }
  if (length > 52) {
    return {
      fontSize: 60,
      lineHeight: 0.97,
      maxWidth: '72%',
    }
  }
  if (length > 40) {
    return {
      fontSize: 66,
      lineHeight: 0.95,
      maxWidth: '69%',
    }
  }
  return {
    fontSize: 72,
    lineHeight: 0.94,
    maxWidth: '66%',
  }
}

function normalizePanels(scene: RemotionScene): DataStagePanel[] | null {
  const data = (scene.composition?.data ?? {}) as Record<string, unknown>
  const raw = Array.isArray(data.panels) ? (data.panels as unknown[]) : []
  if (raw.length < 2) {
    return null
  }

  const panels = raw.flatMap((entry, panelIndex) => {
    if (!entry || typeof entry !== 'object') {
      return []
    }
    const panel = entry as Record<string, unknown>

    const candidateSeries = Array.isArray(panel.series) ? (panel.series as unknown[]) : []
    const series = candidateSeries.flatMap((s, si) => {
      if (!s || typeof s !== 'object') {
        return []
      }
      const item = s as Record<string, unknown>
      const rawPoints = Array.isArray(item.points) ? (item.points as unknown[]) : []
      const points = rawPoints.flatMap((pt) => {
        if (!pt || typeof pt !== 'object') {
          return []
        }
        const p = pt as Record<string, unknown>
        const label = String(p.x || '').trim()
        if (!label) {
          return []
        }
        return [{
          x: label,
          y: asFiniteNumber(p.y),
          label: String(p.label || '').trim() || undefined,
        }]
      })
      if (points.length === 0) {
        return []
      }
      return [{
        id: String(item.id || `panel-${panelIndex}-series-${si}`),
        label: String(item.label || '').trim(),
        type: (String(item.type || '').trim() === 'bar' ? 'bar' : 'line') as 'bar' | 'line',
        points,
      }]
    })

    const candidateBands = Array.isArray(panel.referenceBands) ? (panel.referenceBands as unknown[]) : []
    const referenceBands: DataStageReferenceBand[] = candidateBands.flatMap((b, bi) => {
      if (!b || typeof b !== 'object') {
        return []
      }
      const band = b as Record<string, unknown>
      const yMin = asFiniteNumber(band.yMin)
      const yMax = asFiniteNumber(band.yMax)
      if (yMin === null || yMax === null) {
        return []
      }
      return [{
        id: String(band.id || `panel-${panelIndex}-band-${bi}`),
        label: String(band.label || '').trim() || 'Reference range',
        yMin: Math.min(yMin, yMax),
        yMax: Math.max(yMin, yMax),
        xRange: null,
      }]
    })

    if (series.length === 0) {
      return []
    }

    const title = String(panel.title || panel.yAxisLabel || `Panel ${panelIndex + 1}`).trim()
    // Strip the panel title prefix from x labels so bars don't redundantly
    // repeat "P300 Strength — Session 1" when the header already says it.
    const cleanPrefix = title.split('(')[0].trim().replace(/:$/, '').toLowerCase()
    const cleanedSeries = cleanPrefix
      ? series.map((s) => ({
          ...s,
          points: s.points.map((pt) => {
            const xl = pt.x.toLowerCase()
            for (const sep of [' — ', ' - ', ': ']) {
              if (xl.startsWith(cleanPrefix + sep)) {
                const cleaned = pt.x.slice(cleanPrefix.length + sep.length).trim()
                return { ...pt, x: cleaned || pt.x }
              }
            }
            if (xl.startsWith(cleanPrefix)) {
              const cleaned = pt.x.slice(cleanPrefix.length).replace(/^[\s—\-:]+/, '').trim()
              return cleaned ? { ...pt, x: cleaned } : pt
            }
            return pt
          }),
        }))
      : series

    const rawPolarity = String(panel.polarity || '').trim()
    const polarity: Polarity = rawPolarity === 'lower_is_better' || rawPolarity === 'higher_is_better' || rawPolarity === 'in_range_is_better'
      ? rawPolarity
      : null

    return [{
      id: String(panel.id || `panel-${panelIndex}`),
      title,
      series: cleanedSeries,
      referenceBands,
      yAxisLabel: String(panel.yAxisLabel || panel.title || 'Value').trim(),
      polarity,
    }]
  })

  return panels.length >= 2 ? panels : null
}

/** Dim a hex color to semi-transparent rgba for out-of-band visual treatment. */
function dimHex(hex: string, opacity = 0.3): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${opacity})`
}

/** Read polarity from scene composition data. */
function normalizePolarity(scene: RemotionScene): Polarity {
  const data = (scene.composition?.data ?? {}) as Record<string, unknown>
  const raw = data.polarity
  if (raw === 'lower_is_better' || raw === 'higher_is_better' || raw === 'in_range_is_better') {
    return raw
  }
  return null
}

/** Human-readable polarity annotation for chart reference bands. */
function polarityAnnotation(polarity: Polarity): string {
  switch (polarity) {
    case 'lower_is_better':
      return '\u2193 Lower is better'
    case 'higher_is_better':
      return '\u2191 Higher is better'
    case 'in_range_is_better':
      return '\u2194 In range is target'
    default:
      return ''
  }
}

/** Polarity-aware color for out-of-band points.
 *  "Bad" side gets warm red; "good" overshoot gets neutral amber. */
function polarityPointColor(
  point: DataStagePoint,
  polarity: Polarity,
  theme: DataStageTheme,
  pointIsInBand: (p: DataStagePoint) => boolean,
  referenceBands: DataStageReferenceBand[],
): string | null {
  if (point.y === null || referenceBands.length === 0 || !polarity) return null
  if (pointIsInBand(point)) return null
  const band = referenceBands[0]
  const isAboveBand = point.y > band.yMax
  const isBelowBand = point.y < band.yMin
  if (!isAboveBand && !isBelowBand) return null
  // Determine if this is the "bad" direction
  const isBadSide =
    (polarity === 'lower_is_better' && isAboveBand) ||
    (polarity === 'higher_is_better' && isBelowBand)
  if (isBadSide) {
    return dimHex('#f87171', 0.38) // warm red for bad direction
  }
  return dimHex(theme.accent, 0.32) // neutral amber for overshoot on good side
}

function PanelMiniChart({
  panel,
  theme,
  reveal,
  isBarLayout,
}: {
  panel: DataStagePanel
  theme: DataStageTheme
  reveal: number
  isBarLayout: boolean
}) {
  const primarySeries = panel.series[0]
  const allPoints = panel.series.flatMap((s) => s.points)
  const xLabels = uniqueStrings(allPoints.map((p) => p.x))
  const labelIndex = new Map(xLabels.map((label, i) => [label, i]))

  const numericValues = [
    ...allPoints.flatMap((p) => (p.y === null ? [] : [p.y])),
    ...panel.referenceBands.flatMap((b) => [b.yMin, b.yMax]),
  ]
  const minValue = numericValues.length > 0 ? Math.min(...numericValues) : 0
  const maxValue = numericValues.length > 0 ? Math.max(...numericValues) : 1
  const valueSpan = maxValue - minValue || Math.max(1, Math.abs(maxValue) * 0.2)
  const domainMin = isBarLayout ? Math.min(0, minValue) : minValue - valueSpan * 0.18
  const domainMaxBase = maxValue + valueSpan * 0.22
  const domainMax = domainMaxBase <= domainMin ? domainMin + 1 : domainMaxBase

  const svgW = 480
  const svgH = 380
  const left = 68
  const top = 20
  const right = 16
  const bottom = 60
  const plotW = svgW - left - right
  const plotH = svgH - top - bottom
  const plotBottom = top + plotH
  const slotW = plotW / Math.max(xLabels.length, 1)

  const valueToY = (v: number) => {
    const norm = (v - domainMin) / Math.max(domainMax - domainMin, 1)
    return top + plotH - norm * plotH
  }

  const xForLabel = (label: string) => {
    const idx = labelIndex.get(label) ?? 0
    return left + slotW * (idx + 0.5)
  }

  const barW = slotW * 0.52
  const opacity = interpolate(reveal, [0, 1], [0.78, 1])

  const ticks = Array.from({ length: 4 }, (_, i) => {
    const v = domainMin + ((domainMax - domainMin) * i) / 3
    return { value: v, y: valueToY(v) }
  })

  const pointInBand = (point: DataStagePoint) => {
    if (point.y === null) {
      return false
    }
    return panel.referenceBands.some((b) => point.y !== null && point.y >= b.yMin && point.y <= b.yMax)
  }

  const panelPolarity = panel.polarity ?? null
  const panelPolarityText = polarityAnnotation(panelPolarity)

  const polarityFill = (point: DataStagePoint) =>
    polarityPointColor(point, panelPolarity, theme, pointInBand, panel.referenceBands)

  return (
    <div style={{ opacity, display: 'flex', flexDirection: 'column', gap: 10, flex: 1 }}>
      <div
        style={{
          color: theme.accent,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          fontSize: 17,
          letterSpacing: '0.07em',
          textTransform: 'uppercase',
        }}
      >
        {panel.title}
        {panelPolarityText ? (
          <span style={{ fontSize: 13, fontStyle: 'italic', marginLeft: 8, opacity: 0.7, textTransform: 'none' }}>
            {panelPolarityText}
          </span>
        ) : null}
      </div>
      <div
        style={{
          flex: 1,
          borderRadius: 20,
          overflow: 'hidden',
          background: 'linear-gradient(180deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.00) 100%)',
        }}
      >
        <svg
          viewBox={`0 0 ${svgW} ${svgH}`}
          preserveAspectRatio="none"
          style={{ width: '100%', height: '100%' }}
        >
          {ticks.map((tick, i) => (
            <g key={i}>
              <line x1={left} x2={svgW - right} y1={tick.y} y2={tick.y} stroke={theme.grid} strokeWidth={1} />
              <text
                x={left - 6}
                y={tick.y + 4}
                textAnchor="end"
                fill={theme.muted}
                fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                fontSize="13"
              >
                {formatDataStageValue(tick.value)}
              </text>
            </g>
          ))}
          {/* Rotated Y-axis label for panel */}
          {panel.yAxisLabel ? (
            <text
              x={10}
              y={top + plotH / 2}
              textAnchor="middle"
              dominantBaseline="middle"
              transform={`rotate(-90 10 ${top + plotH / 2})`}
              fill={theme.muted}
              fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
              fontSize="13"
              fontWeight="500"
            >
              {panel.yAxisLabel}
            </text>
          ) : null}
          {panel.referenceBands.map((band) => {
            const bandY1 = valueToY(band.yMax)
            const bandY2 = valueToY(band.yMin)
            return (
              <g key={band.id}>
                <rect x={left} y={bandY1} width={plotW} height={Math.max(bandY2 - bandY1, 1)} fill={theme.band} />
                <line x1={left} x2={left + plotW} y1={bandY1} y2={bandY1} stroke={theme.bandEdge} strokeWidth={1.5} />
                <line x1={left} x2={left + plotW} y1={bandY2} y2={bandY2} stroke={theme.bandEdge} strokeWidth={1.5} />
              </g>
            )
          })}
          {isBarLayout && primarySeries
            ? primarySeries.points.map((point) => {
                if (point.y === null) {
                  return null
                }
                const x = xForLabel(point.x)
                const barH = Math.abs(valueToY(point.y) - valueToY(0))
                const barY = point.y >= 0 ? valueToY(point.y) : valueToY(0)
                const inBand = pointInBand(point)
                const fill = inBand ? theme.primary : (polarityFill(point) ?? dimHex(theme.accent, 0.32))
                return (
                  <g key={point.x}>
                    <rect
                      x={x - barW / 2} y={barY} width={barW} height={Math.max(barH, 2)} fill={fill} rx={5}
                      stroke={!inBand ? theme.accent : undefined}
                      strokeWidth={!inBand ? 1.5 : undefined}
                      strokeDasharray={!inBand ? '4 3' : undefined}
                    />
                    <text
                      x={x}
                      y={barY - 9}
                      textAnchor="middle"
                      fill={theme.text}
                      fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                      fontSize="16"
                      fontWeight="600"
                    >
                      {formatDataStageValue(point.y)}
                    </text>
                    <text
                      x={x}
                      y={plotBottom + 22}
                      textAnchor="middle"
                      fill={theme.muted}
                      fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                      fontSize="14"
                    >
                      {point.x}
                    </text>
                  </g>
                )
              })
            : panel.series.flatMap((s) =>
                s.points.map((point, pi) => {
                  if (point.y === null) {
                    return null
                  }
                  const cx = xForLabel(point.x)
                  const cy = valueToY(point.y)
                  const inBand = pointInBand(point)
                  const fill = inBand ? theme.primary : (polarityFill(point) ?? dimHex(theme.accent, 0.32))
                  return (
                    <g key={`${s.id}-${pi}`}>
                      <circle cx={cx} cy={cy} r={10} fill={fill} stroke={!inBand ? theme.accent : undefined} strokeWidth={!inBand ? 1.5 : undefined} />
                      <text
                        x={cx}
                        y={cy - 16}
                        textAnchor="middle"
                        fill={theme.text}
                        fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                        fontSize="16"
                        fontWeight="600"
                      >
                        {formatDataStageValue(point.y)}
                      </text>
                      <text
                        x={cx}
                        y={plotBottom + 22}
                        textAnchor="middle"
                        fill={theme.muted}
                        fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                        fontSize="14"
                      >
                        {point.x}
                      </text>
                    </g>
                  )
                }),
              )}
          <line x1={left} x2={svgW - right} y1={plotBottom} y2={plotBottom} stroke={theme.gridStrong} strokeWidth={1.5} />
        </svg>
      </div>
    </div>
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
  const props = (scene.composition?.props ?? {}) as Record<string, unknown>
  const data = (scene.composition?.data ?? {}) as Record<string, unknown>
  const series = normalizeDataStageSeries(scene)
  const primarySeries = series[0]
  const referenceBands = normalizeDataStageReferenceBands(scene)
  const callouts = normalizeDataStageCallouts(scene)
  const layoutVariant = semanticString(props, 'layoutVariant', primarySeries.type === 'bar' ? 'bars_with_band' : 'line_with_band')
  const headline = semanticString(props, 'headline', scene.title || primarySeries.label || 'Data stage')
  const kicker = semanticString(props, 'kicker', primarySeries.label || scene.title || 'Cathode')
  const rawYAxisLabel = String(data.yAxisLabel || '').trim()
  const yAxisLabel = rawYAxisLabel && rawYAxisLabel.toLowerCase() !== 'value'
    ? rawYAxisLabel
    : inferLegacyDataStageValueLabel(scene) || primarySeries.label || 'Value'
  const xAxisLabel = String(data.xAxisLabel || '').trim()
  const xLabels = uniqueStrings(series.flatMap((item) => item.points.map((point) => point.x)))
  const labelIndex = new Map(xLabels.map((label, index) => [label, index]))
  const isBarLayout = layoutVariant.startsWith('bars') || primarySeries.type === 'bar'
  const useComparisonLanes = !isBarLayout
    && series.length > 1
    && xLabels.length === 2
    && referenceBands.length === 0
    && series.every((item) => item.points.length === 2 && item.points.every((point) => point.y !== null))
  const legendLabels = uniqueStrings(
    (isBarLayout ? [primarySeries.label] : series.map((item) => item.label)).concat(yAxisLabel),
  ).slice(0, 3)
  const headlineLayout = resolveDataStageHeadlineLayout(headline, series.length)
  const footerNotes = uniqueStrings([
    ...callouts.map((callout) => callout.label),
    ...scene.onScreenText,
  ]).slice(0, 4)
  const theme = resolveDataStageTheme(semanticString(props, 'palette', 'teal_on_navy'))
  const panelRevealProgress = interpolate(reveal, [0, 1], [0, 1])
  const panelOpacity = interpolate(panelRevealProgress, [0, 1], [0.78, 1])
  const panelTranslateY = interpolate(panelRevealProgress, [0, 1], [26, 0])

  const numericValues = [
    ...series.flatMap((item) => item.points.flatMap((point) => (point.y === null ? [] : [point.y]))),
    ...referenceBands.flatMap((band) => [band.yMin, band.yMax]),
  ]
  const minValue = numericValues.length > 0 ? Math.min(...numericValues) : 0
  const maxValue = numericValues.length > 0 ? Math.max(...numericValues) : 1
  const valueSpan = maxValue - minValue || Math.max(1, Math.abs(maxValue) * 0.2)
  const domainMin = isBarLayout ? Math.min(0, minValue) : minValue - valueSpan * 0.18
  const domainMaxBase = maxValue + valueSpan * 0.18
  const domainMax = domainMaxBase <= domainMin ? domainMin + 1 : domainMaxBase

  const svgWidth = 1060
  const svgHeight = 470
  const chartLeft = useComparisonLanes ? 46 : 94
  const chartTop = 34
  const chartRight = 38
  const chartBottom = 80
  const plotWidth = svgWidth - chartLeft - chartRight
  const plotHeight = svgHeight - chartTop - chartBottom
  const slotWidth = plotWidth / Math.max(xLabels.length, 1)
  const plotBottom = chartTop + plotHeight
  const valueToY = (value: number) => {
    const normalized = (value - domainMin) / Math.max(domainMax - domainMin, 1)
    return chartTop + plotHeight - normalized * plotHeight
  }
  const lineXAxisInset = xLabels.length <= 1
    ? 0
    : xLabels.length === 2
      ? Math.min(plotWidth * 0.12, 96)
      : xLabels.length === 3
        ? Math.min(plotWidth * 0.09, 72)
        : Math.min(slotWidth * 0.28, 44)
  const xForLabel = (label: string) => {
    const index = labelIndex.get(label) ?? 0
    if (isBarLayout || xLabels.length <= 1) {
      return chartLeft + slotWidth * (index + 0.5)
    }
    const usableWidth = Math.max(plotWidth - lineXAxisInset * 2, 1)
    const progress = index / Math.max(xLabels.length - 1, 1)
    return chartLeft + lineXAxisInset + usableWidth * progress
  }
  const tickCount = 4
  const ticks = Array.from({ length: tickCount + 1 }, (_, index) => {
    const value = domainMin + ((domainMax - domainMin) * index) / tickCount
    return {
      value,
      y: valueToY(value),
    }
  })

  const pointIsInBand = (point: DataStagePoint) => {
    const pointValue = point.y
    if (pointValue === null) {
      return false
    }
    return referenceBands.some((band) => {
      const labelPosition = labelIndex.get(point.x)
      if (labelPosition === undefined) {
        return false
      }
      const xRangeValid = !band.xRange || (() => {
        const start = labelIndex.get(band.xRange[0])
        const end = labelIndex.get(band.xRange[1])
        return start !== undefined && end !== undefined && labelPosition >= start && labelPosition <= end
      })()
      return xRangeValid && pointValue >= band.yMin && pointValue <= band.yMax
    })
  }

  const polarity = normalizePolarity(scene)
  const polarityText = polarityAnnotation(polarity)

  const pointColor = (point: DataStagePoint, index: number, seriesIndex = 0) => {
    const isCalloutTarget = callouts.some((callout) => callout.x === point.x)
    if (layoutVariant === 'line_with_zones' && point.y !== null && referenceBands[0]) {
      if (point.y < referenceBands[0].yMin) {
        return theme.accent
      }
      if (point.y > referenceBands[0].yMax) {
        return theme.secondary
      }
      return theme.primary
    }
    // Polarity-aware coloring: "bad" side gets warm red, "good" overshoot gets neutral amber.
    const pColor = polarityPointColor(point, polarity, theme, pointIsInBand, referenceBands)
    if (pColor) return pColor
    // Out-of-band points get a muted, semi-transparent fill so they visually
    // recede instead of dominating the chart.  A tall bar that is OUT of
    // target should NOT look like the star of the chart.
    if (isCalloutTarget || (point.y !== null && !pointIsInBand(point) && referenceBands.length > 0)) {
      return dimHex(theme.accent, 0.32)
    }
    if (layoutVariant === 'bars_with_delta') {
      if (index === 0) {
        return theme.secondary
      }
      if (index === primarySeries.points.length - 1) {
        return theme.primary
      }
    }
    if (!isBarLayout) {
      if (seriesIndex % 3 === 1) {
        return theme.secondary
      }
      if (seriesIndex % 3 === 2) {
        return theme.accent
      }
    }
    return index % 2 === 0 ? theme.primary : theme.secondary
  }

  const lineSeries = series.map((item, seriesIndex) => {
    const validPoints = item.points
      .map((point) => ({
        ...point,
        px: xForLabel(point.x),
        py: point.y === null ? null : valueToY(point.y),
      }))
      .filter((point) => point.py !== null)
    const path = validPoints
      .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.px.toFixed(1)} ${(point.py as number).toFixed(1)}`)
      .join(' ')
    return {
      seriesIndex,
      item,
      validPoints,
      path,
    }
  })
  const primaryLineSeries = lineSeries[0]
  const areaPath = primaryLineSeries && primaryLineSeries.validPoints.length > 0 && lineSeries.length === 1
    ? [
      primaryLineSeries.path,
      `L ${primaryLineSeries.validPoints[primaryLineSeries.validPoints.length - 1].px.toFixed(1)} ${plotBottom.toFixed(1)}`,
      `L ${primaryLineSeries.validPoints[0].px.toFixed(1)} ${plotBottom.toFixed(1)}`,
      'Z',
    ].join(' ')
    : ''

  // Dual-panel path: when composition.data.panels carries two independent metric groups.
  const dualPanels = normalizePanels(scene)
  if (dualPanels) {
    return (
      <AbsoluteFill
        data-testid="three-data-stage"
        style={{ background: theme.background }}
      >
        <AbsoluteFill
          style={{
            padding: 56,
            opacity: panelOpacity,
            transform: `translateY(${panelTranslateY}px)`,
          }}
        >
          <div
            style={{
              flex: 1,
              borderRadius: 34,
              background: `linear-gradient(180deg, ${theme.panel} 0%, rgba(6, 10, 18, 0.92) 100%)`,
              border: `1px solid ${theme.panelEdge}`,
              boxShadow: '0 28px 60px rgba(0,0,0,0.28)',
              padding: '40px 42px 36px',
              display: 'grid',
              gridTemplateRows: 'auto 1fr',
              gap: 28,
            }}
          >
            <div>
              <div
                style={{
                  color: theme.accent,
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                  fontSize: 18,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  marginBottom: 12,
                }}
              >
                {kicker}
              </div>
              <div
                data-testid="three-data-stage-headline"
                style={{
                  color: theme.text,
                  fontFamily: 'Georgia, Times, serif',
                  fontSize: 56,
                  lineHeight: 0.95,
                }}
              >
                {headline}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 36, minHeight: 0 }}>
              {dualPanels.map((panel) => (
                <PanelMiniChart
                  key={panel.id}
                  panel={panel}
                  theme={theme}
                  reveal={reveal}
                  isBarLayout={isBarLayout}
                />
              ))}
            </div>
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    )
  }

  return (
    <AbsoluteFill
      data-testid="three-data-stage"
      style={{
        background: theme.background,
      }}
    >
      <AbsoluteFill
        style={{
          padding: 56,
          opacity: panelOpacity,
          transform: `translateY(${panelTranslateY}px)`,
        }}
      >
        <div
          style={{
            flex: 1,
            borderRadius: 34,
            background: `linear-gradient(180deg, ${theme.panel} 0%, rgba(6, 10, 18, 0.92) 100%)`,
            border: `1px solid ${theme.panelEdge}`,
            boxShadow: '0 28px 60px rgba(0,0,0,0.28)',
            padding: '40px 42px 36px',
            display: 'flex',
            flexDirection: 'column' as const,
            gap: 24,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24 }}>
            <div style={{ maxWidth: headlineLayout.maxWidth }}>
              <div
                style={{
                  color: theme.accent,
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                  fontSize: 18,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  marginBottom: 14,
                }}
              >
                {kicker}
              </div>
              <div
                data-testid="three-data-stage-headline"
                style={{
                  color: theme.text,
                  fontFamily: 'Georgia, Times, serif',
                  fontSize: headlineLayout.fontSize,
                  lineHeight: headlineLayout.lineHeight,
                }}
              >
                {headline}
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'flex-end' }}>
              {legendLabels.map((label) => (
                <div
                  key={label}
                  style={{
                    maxWidth: 320,
                    padding: '10px 16px',
                    borderRadius: 999,
                    background: theme.chip,
                    border: `1px solid ${theme.panelEdge}`,
                    color: theme.muted,
                    fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
                    fontSize: 20,
                    lineHeight: 1.1,
                  }}
                >
                  {label}
                </div>
              ))}
            </div>
          </div>
          <div
            style={{
              position: 'relative',
              flex: 1,
              minHeight: 0,
              borderRadius: 28,
              overflow: 'hidden',
              background: 'linear-gradient(180deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.00) 100%)',
            }}
          >
            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              preserveAspectRatio="none"
              style={{ position: 'absolute', inset: 0, display: 'block', width: '100%', height: '100%' }}
            >
              <defs>
                <linearGradient id="data-stage-line-fill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor={theme.primary} stopOpacity={0.26} />
                  <stop offset="100%" stopColor={theme.primary} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              {layoutVariant === 'line_with_zones' && referenceBands[0] ? (
                <>
                  <rect
                    x={chartLeft}
                    y={chartTop}
                    width={plotWidth}
                    height={Math.max(valueToY(referenceBands[0].yMax) - chartTop, 0)}
                    fill="rgba(255, 176, 124, 0.06)"
                  />
                  <rect
                    x={chartLeft}
                    y={valueToY(referenceBands[0].yMax)}
                    width={plotWidth}
                    height={Math.max(valueToY(referenceBands[0].yMin) - valueToY(referenceBands[0].yMax), 0)}
                    fill={theme.band}
                  />
                  <rect
                    x={chartLeft}
                    y={valueToY(referenceBands[0].yMin)}
                    width={plotWidth}
                    height={Math.max(plotBottom - valueToY(referenceBands[0].yMin), 0)}
                    fill="rgba(116, 159, 255, 0.06)"
                  />
                </>
              ) : null}
              {referenceBands.map((band) => {
                const startIndex = band.xRange ? labelIndex.get(band.xRange[0]) ?? 0 : 0
                const endIndex = band.xRange ? labelIndex.get(band.xRange[1]) ?? (xLabels.length - 1) : (xLabels.length - 1)
                const bandX = chartLeft + slotWidth * startIndex
                const bandWidth = slotWidth * (endIndex - startIndex + 1)
                const bandTop = valueToY(band.yMax)
                const bandHeight = Math.max(valueToY(band.yMin) - bandTop, 8)
                return (
                  <g key={band.id}>
                    <rect
                      x={bandX + 6}
                      y={bandTop}
                      width={Math.max(bandWidth - 12, 20)}
                      height={bandHeight}
                      rx={16}
                      fill={theme.band}
                      stroke={theme.bandEdge}
                      strokeWidth={1.5}
                    />
                    <text
                      x={bandX + 20}
                      y={bandTop + 24}
                      fill={theme.muted}
                      fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                      fontSize="18"
                    >
                      {band.label}
                    </text>
                    {polarityText ? (
                      <text
                        x={bandX + 20}
                        y={bandTop + 44}
                        fill={theme.accent}
                        fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                        fontSize="15"
                        fontStyle="italic"
                        opacity={0.7}
                      >
                        {polarityText}
                      </text>
                    ) : null}
                  </g>
                )
              })}
              {!useComparisonLanes ? ticks.map((tick, index) => (
                <g key={`${tick.value}-${index}`}>
                  <line
                    x1={chartLeft}
                    x2={chartLeft + plotWidth}
                    y1={tick.y}
                    y2={tick.y}
                    stroke={index === tickCount ? theme.gridStrong : theme.grid}
                    strokeWidth={index === tickCount ? 1.5 : 1}
                    strokeDasharray={index === tickCount ? '0' : '6 8'}
                  />
                  <text
                    x={chartLeft - 14}
                    y={tick.y + 6}
                    textAnchor="end"
                    fill={theme.muted}
                    fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                    fontSize="18"
                  >
                    {formatDataStageValue(tick.value)}
                  </text>
                </g>
              )) : null}
              {/* Rotated Y-axis label */}
              {yAxisLabel ? (
                <text
                  x={14}
                  y={chartTop + plotHeight / 2}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  transform={`rotate(-90 14 ${chartTop + plotHeight / 2})`}
                  fill={theme.muted}
                  fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                  fontSize="16"
                  fontWeight="500"
                >
                  {yAxisLabel}
                </text>
              ) : null}
              {isBarLayout ? primarySeries.points.map((point, index) => {
                const value = point.y ?? 0
                const x = xForLabel(point.x)
                const baseline = valueToY(domainMin)
                const targetTop = valueToY(value)
                const barTop = point.y === null ? baseline - 12 : targetTop
                const barHeight = Math.max(baseline - barTop, 12)
                const barWidth = Math.min(84, slotWidth * 0.56)
                const fill = point.y === null ? 'rgba(255,255,255,0.08)' : pointColor(point, index)
                const outOfBand = point.y !== null && !pointIsInBand(point) && referenceBands.length > 0
                return (
                  <g key={`${point.x}-${index}`}>
                    <rect
                      data-testid={point.y === null ? 'three-data-stage-bar-empty' : 'three-data-stage-bar'}
                      data-series-id={primarySeries.id}
                      data-point-x={point.x}
                      data-point-y={point.y ?? ''}
                      x={x - barWidth / 2}
                      y={barTop}
                      width={barWidth}
                      height={barHeight}
                      rx={18}
                      fill={fill}
                      stroke={outOfBand ? theme.accent : undefined}
                      strokeWidth={outOfBand ? 2 : undefined}
                      strokeDasharray={outOfBand ? '6 4' : undefined}
                    />
                    {point.y !== null ? (
                      <text
                        x={x}
                        y={barTop - 12}
                        textAnchor="middle"
                        fill={theme.text}
                        fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                        fontSize="18"
                      >
                        {formatDataStageValue(point.y)}
                      </text>
                    ) : (
                      <text
                        x={x}
                        y={baseline - 12}
                        textAnchor="middle"
                        fill={theme.muted}
                        fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                        fontSize="16"
                      >
                        n/a
                      </text>
                    )}
                    <text
                      x={x}
                      y={plotBottom + 34}
                      textAnchor="middle"
                      fill={theme.muted}
                      fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                      fontSize="20"
                    >
                      {point.x}
                    </text>
                  </g>
                )
              }) : (
                <>
                  {useComparisonLanes ? (
                    <>
                      {lineSeries.map(({ item, validPoints, seriesIndex }) => {
                        const laneHeight = plotHeight / Math.max(lineSeries.length, 1)
                        const laneTop = chartTop + laneHeight * seriesIndex
                        const laneBottom = laneTop + laneHeight
                        const lanePaddingY = Math.min(laneHeight * 0.18, 32)
                        const laneValues = validPoints.map((point) => point.y as number)
                        const laneMin = Math.min(...laneValues)
                        const laneMax = Math.max(...laneValues)
                        const laneSpan = laneMax - laneMin || Math.max(0.1, Math.abs(laneMax) * 0.15)
                        const laneDomainMin = laneMin - laneSpan * 0.14
                        const laneDomainMax = laneMax + laneSpan * 0.14
                        const laneValueToY = (value: number) => {
                          const progress = (value - laneDomainMin) / Math.max(laneDomainMax - laneDomainMin, 1e-6)
                          return laneBottom - lanePaddingY - progress * Math.max(laneHeight - lanePaddingY * 2, 1)
                        }
                        const lanePoints = item.points.map((point) => ({
                          ...point,
                          px: xForLabel(point.x),
                          py: laneValueToY(point.y as number),
                        }))
                        const lanePath = lanePoints
                          .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.px.toFixed(1)} ${point.py.toFixed(1)}`)
                          .join(' ')
                        const fillColor = pointColor(lanePoints[0] as DataStagePoint, 0, seriesIndex)
                        return (
                          <g key={item.id}>
                            <rect
                              x={chartLeft}
                              y={laneTop + 6}
                              width={plotWidth}
                              height={Math.max(laneHeight - 12, 32)}
                              rx={18}
                              fill={seriesIndex % 2 === 0 ? 'rgba(255,255,255,0.015)' : 'rgba(255,255,255,0.03)'}
                            />
                            <path
                              data-testid="three-data-stage-line"
                              data-series-id={item.id}
                              data-point-count={lanePoints.length}
                              d={lanePath}
                              fill="none"
                              stroke={fillColor}
                              strokeWidth={6}
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                            {lanePoints.map((point, index) => (
                              <g key={`${item.id}-${point.x}-${index}`}>
                                <circle
                                  data-testid="three-data-stage-line-point"
                                  data-series-id={item.id}
                                  data-point-x={point.x}
                                  data-point-y={point.y ?? ''}
                                  cx={point.px}
                                  cy={point.py}
                                  r={10 + panelRevealProgress * 2}
                                  fill={fillColor}
                                />
                                <circle
                                  cx={point.px}
                                  cy={point.py}
                                  r={5}
                                  fill="#08111f"
                                />
                                <text
                                  x={point.px}
                                  y={point.py - 14}
                                  textAnchor="middle"
                                  fill={theme.text}
                                  fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                                  fontSize="17"
                                >
                                  {formatDataStageValue(point.y as number)}
                                </text>
                              </g>
                            ))}
                          </g>
                        )
                      })}
                      {xLabels.map((label) => (
                        <text
                          key={label}
                          x={xForLabel(label)}
                          y={plotBottom + 34}
                          textAnchor="middle"
                          fill={theme.muted}
                          fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                          fontSize="20"
                        >
                          {label}
                        </text>
                      ))}
                    </>
                  ) : (
                    <>
                  {areaPath ? (
                    <path d={areaPath} fill="url(#data-stage-line-fill)" opacity={0.9} />
                  ) : null}
                  {lineSeries.map(({ item, path, validPoints, seriesIndex }) => (
                    path ? (
                      <path
                        key={item.id}
                        data-testid="three-data-stage-line"
                        data-series-id={item.id}
                        data-point-count={validPoints.length}
                        d={path}
                        fill="none"
                        stroke={pointColor(validPoints[0] as DataStagePoint, 0, seriesIndex)}
                        strokeWidth={6}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    ) : null
                  ))}
                  {primarySeries.points.map((point, index) => (
                    <text
                      key={`${point.x}-${index}`}
                      x={xForLabel(point.x)}
                      y={plotBottom + 34}
                      textAnchor="middle"
                      fill={theme.muted}
                      fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                      fontSize="20"
                    >
                      {point.x}
                    </text>
                  ))}
                  {lineSeries.flatMap(({ item, validPoints, seriesIndex }) => validPoints.map((point, index) => (
                    <g key={`${item.id}-${point.x}-${index}`}>
                      {(() => {
                        const oob = point.y !== null && !pointIsInBand(point) && referenceBands.length > 0
                        return (
                          <>
                          <circle
                            data-testid="three-data-stage-line-point"
                            data-series-id={item.id}
                            data-point-x={point.x}
                            data-point-y={point.y ?? ''}
                            cx={point.px}
                            cy={point.py as number}
                            r={10 + panelRevealProgress * 2}
                            fill={pointColor(point, index, seriesIndex)}
                            stroke={oob ? theme.accent : undefined}
                            strokeWidth={oob ? 2 : undefined}
                            strokeDasharray={oob ? '4 3' : undefined}
                          />
                          <circle
                            cx={point.px}
                            cy={point.py as number}
                            r={5}
                            fill="#08111f"
                          />
                          </>
                        )
                      })()}
                    </g>
                  )))}
                    </>
                  )}
                </>
              )}
              {callouts.filter((callout) => callout.fromX && callout.toX).map((callout) => {
                const fromX = xForLabel(callout.fromX as string)
                const toX = xForLabel(callout.toX as string)
                const y = chartTop + 18
                const labelX = (fromX + toX) / 2
                return (
                  <g key={callout.id}>
                    <line x1={fromX} x2={toX} y1={y} y2={y} stroke={theme.accent} strokeWidth={3} strokeDasharray="10 8" />
                    <circle cx={fromX} cy={y} r={5} fill={theme.accent} />
                    <circle cx={toX} cy={y} r={5} fill={theme.accent} />
                    <rect x={labelX - 116} y={y - 38} width={232} height={28} rx={14} fill={theme.callout} />
                    <text
                      x={labelX}
                      y={y - 18}
                      textAnchor="middle"
                      fill={theme.text}
                      fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                      fontSize="16"
                    >
                      {callout.label}
                    </text>
                  </g>
                )
              })}
              {callouts.filter((callout) => callout.x).slice(0, 3).map((callout) => {
                const x = xForLabel(callout.x as string)
                const point = primarySeries.points.find((entry) => entry.x === callout.x)
                const y = point?.y !== null && point?.y !== undefined ? valueToY(point.y) : plotBottom - 40
                const calloutWidth = 244
                const boxX = clampNumber(x - calloutWidth / 2, chartLeft + 8, chartLeft + plotWidth - calloutWidth - 8)
                const boxY = clampNumber(y - 64, chartTop + 8, plotBottom - 44)
                return (
                  <g key={callout.id}>
                    <line x1={x} x2={x} y1={y - 6} y2={boxY + 34} stroke={theme.accent} strokeWidth={2} />
                    <rect x={boxX} y={boxY} width={calloutWidth} height={34} rx={17} fill={theme.callout} />
                    <text
                      x={boxX + calloutWidth / 2}
                      y={boxY + 22}
                      textAnchor="middle"
                      fill={theme.text}
                      fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                      fontSize="16"
                    >
                      {callout.label}
                    </text>
                  </g>
                )
              })}
              {/* X-axis label */}
              {xAxisLabel ? (
                <text
                  x={chartLeft + plotWidth / 2}
                  y={svgHeight - 6}
                  textAnchor="middle"
                  fill={theme.muted}
                  fontFamily='"Helvetica Neue", Helvetica, Arial, sans-serif'
                  fontSize="16"
                  fontWeight="500"
                >
                  {xAxisLabel}
                </text>
              ) : null}
            </svg>
          </div>
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            {footerNotes.map((note) => (
              <div
                key={note}
                style={{
                  maxWidth: '48%',
                  padding: '14px 18px',
                  borderRadius: 20,
                  background: theme.chip,
                  border: `1px solid ${theme.panelEdge}`,
                  color: theme.text,
                  fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
                  fontSize: 20,
                  lineHeight: 1.12,
                }}
              >
                {note}
              </div>
            ))}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  )
}

type TableauPalette = {
  background: string
  chamber: string
  glow: string
  brass: string
  mist: string
  star: string
  accent: string
  shadow: string
}

function normalizePaletteWords(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim().toLowerCase()).filter(Boolean)
  }
  if (typeof value === 'string') {
    return value.split(',').map((item) => item.trim().toLowerCase()).filter(Boolean)
  }
  return []
}

function semanticString(props: Record<string, unknown>, key: string, fallback: string): string {
  return String(props[key] || fallback).trim()
}

function semanticNumber(props: Record<string, unknown>, key: string, fallback: number): number {
  const parsed = Number(props[key])
  return Number.isFinite(parsed) ? parsed : fallback
}

function resolveTableauPalette(words: string[]): TableauPalette {
  const joined = words.join(' ')
  const seaMode = joined.includes('sea')
  const violetMode = joined.includes('violet')
  return {
    background: seaMode ? '#07101b' : '#050814',
    chamber: joined.includes('indigo') ? '#1c1a38' : violetMode ? '#251a3f' : '#121833',
    glow: joined.includes('amber') ? '#f2a558' : '#d9b06f',
    brass: joined.includes('brass') ? '#b78b49' : '#9d7a4a',
    mist: seaMode ? '#2c5b7a' : '#4559a9',
    star: joined.includes('ivory') ? '#f8efe0' : '#e7e0ff',
    accent: violetMode ? '#7868ff' : '#6486ff',
    shadow: '#070914',
  }
}

function HourglassMoonCore({ palette, pulse = 0 }: { palette: TableauPalette; pulse?: number }) {
  return (
    <group>
      <mesh position={[0, 0.98, 0]} scale={[1.02, 0.72 + pulse * 0.03, 1.02]}>
        <sphereGeometry args={[1.2, 48, 48]} />
        <meshStandardMaterial color={palette.star} emissive={palette.glow} emissiveIntensity={0.62 + pulse * 0.14} roughness={0.18} metalness={0.06} transparent opacity={0.95} />
      </mesh>
      <mesh position={[0, -0.98, 0]} scale={[1.02, 0.72 + pulse * 0.03, 1.02]}>
        <sphereGeometry args={[1.2, 48, 48]} />
        <meshStandardMaterial color={palette.star} emissive={palette.glow} emissiveIntensity={0.56 + pulse * 0.12} roughness={0.2} metalness={0.06} transparent opacity={0.95} />
      </mesh>
      <mesh scale={[0.28, 1.95, 0.28]}>
        <cylinderGeometry args={[0.45, 0.18, 1.52, 32]} />
        <meshStandardMaterial color={palette.glow} emissive={palette.glow} emissiveIntensity={0.8 + pulse * 0.18} roughness={0.22} metalness={0.18} />
      </mesh>
      <mesh scale={0.5 + pulse * 0.05}>
        <sphereGeometry args={[1.0, 32, 32]} />
        <meshStandardMaterial color={palette.glow} emissive={palette.glow} emissiveIntensity={1.35} transparent opacity={0.56} />
      </mesh>
      <mesh scale={[1.1, 0.92, 1.1]}>
        <sphereGeometry args={[1.24, 48, 48]} />
        <meshStandardMaterial color={palette.star} roughness={0.06} metalness={0.02} transparent opacity={0.08} />
      </mesh>
      <mesh rotation={[0.35, 0.24, 0.82]} position={[0.18, 1.16, 0.16]}>
        <boxGeometry args={[0.06, 1.22, 0.03]} />
        <meshStandardMaterial color={palette.accent} emissive={palette.glow} emissiveIntensity={0.92} />
      </mesh>
      <mesh rotation={[-0.45, -0.2, -0.56]} position={[-0.14, -1.08, -0.1]}>
        <boxGeometry args={[0.06, 1.18, 0.03]} />
        <meshStandardMaterial color={palette.accent} emissive={palette.glow} emissiveIntensity={0.92} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
        <torusGeometry args={[1.28, 0.04, 10, 96]} />
        <meshStandardMaterial color={palette.glow} emissive={palette.glow} emissiveIntensity={0.6} />
      </mesh>
    </group>
  )
}

function MoonOrb({ palette }: { palette: TableauPalette }) {
  return (
    <group>
      <mesh>
        <sphereGeometry args={[1.18, 40, 40]} />
        <meshStandardMaterial color={palette.star} emissive={palette.glow} emissiveIntensity={0.48} roughness={0.35} metalness={0.06} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0.22, 0]}>
        <torusGeometry args={[1.5, 0.05, 10, 96]} />
        <meshStandardMaterial color={palette.accent} emissive={palette.accent} emissiveIntensity={0.42} />
      </mesh>
    </group>
  )
}

function MothSculpture({ palette, wingTilt = 0, scale = 1 }: { palette: TableauPalette; wingTilt?: number; scale?: number }) {
  return (
    <group scale={scale}>
      <mesh position={[0, -0.05, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <capsuleGeometry args={[0.08, 0.42, 4, 12]} />
        <meshStandardMaterial color={palette.brass} emissive={palette.glow} emissiveIntensity={0.24} roughness={0.16} metalness={0.88} />
      </mesh>
      <mesh position={[-0.32, 0.12, 0]} rotation={[0.1, 0.2, -0.72 + wingTilt]} scale={[0.95, 0.05, 0.48]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color={palette.brass} emissive={palette.glow} emissiveIntensity={0.16} roughness={0.12} metalness={0.92} />
      </mesh>
      <mesh position={[0.32, 0.12, 0]} rotation={[0.1, -0.2, 0.72 - wingTilt]} scale={[0.95, 0.05, 0.48]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color={palette.brass} emissive={palette.glow} emissiveIntensity={0.16} roughness={0.12} metalness={0.92} />
      </mesh>
      <mesh position={[-0.2, -0.06, -0.04]} rotation={[0.22, 0.16, -0.46 + wingTilt * 0.6]} scale={[0.58, 0.04, 0.34]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color={palette.brass} emissive={palette.glow} emissiveIntensity={0.12} roughness={0.12} metalness={0.9} />
      </mesh>
      <mesh position={[0.2, -0.06, -0.04]} rotation={[0.22, -0.16, 0.46 - wingTilt * 0.6]} scale={[0.58, 0.04, 0.34]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color={palette.brass} emissive={palette.glow} emissiveIntensity={0.12} roughness={0.12} metalness={0.9} />
      </mesh>
      <mesh position={[0, 0.22, 0.02]} scale={0.1}>
        <sphereGeometry args={[1, 12, 12]} />
        <meshStandardMaterial color={palette.star} emissive={palette.glow} emissiveIntensity={0.4} />
      </mesh>
    </group>
  )
}

function SymbolicMonolith({ palette, accentScale = 1 }: { palette: TableauPalette; accentScale?: number }) {
  return (
    <group>
      <mesh scale={[1.1, 2.4, 1.1]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color={palette.chamber} emissive={palette.accent} emissiveIntensity={0.16 * accentScale} roughness={0.34} metalness={0.46} />
      </mesh>
      <mesh position={[0, 1.55, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.64, 0.05, 10, 80]} />
        <meshStandardMaterial color={palette.glow} emissive={palette.glow} emissiveIntensity={0.42} />
      </mesh>
    </group>
  )
}

function ConstellationCurtain({ palette, side = 1 }: { palette: TableauPalette; side?: 1 | -1 }) {
  return (
    <group position={[side * 5.2, 2.2, -1.8]} rotation={[0, 0, side * 0.26]}>
      {[0, 1, 2].map((index) => (
        <group key={`${side}-${index}`} position={[side * index * 0.46, 1.1 - index * 0.9, index * -0.42]}>
          <mesh rotation={[0.08, side * 0.18, side * 0.12]}>
            <boxGeometry args={[0.08, 4.1 - index * 0.28, 0.08]} />
            <meshStandardMaterial color={palette.accent} emissive={palette.accent} emissiveIntensity={0.62} transparent opacity={0.88} />
          </mesh>
          {[-1, 0, 1].map((starIndex) => (
            <mesh
              key={`${side}-${index}-${starIndex}`}
              position={[side * 0.08 * starIndex, 1.1 - starIndex * 1.05, 0]}
              scale={0.18 + index * 0.04}
            >
              <sphereGeometry args={[1, 12, 12]} />
              <meshStandardMaterial color={palette.star} emissive={palette.star} emissiveIntensity={1.25} />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  )
}

function TableauObject({
  label,
  palette,
  scale = 1,
  pulse = 0,
}: {
  label: string
  palette: TableauPalette
  scale?: number
  pulse?: number
}) {
  const normalized = label.toLowerCase()
  if (normalized.includes('hourglass') || (normalized.includes('moon') && normalized.includes('crack'))) {
    return (
      <group scale={scale}>
        <HourglassMoonCore palette={palette} pulse={pulse} />
      </group>
    )
  }
  if (normalized.includes('moon') || normalized.includes('orb')) {
    return (
      <group scale={scale}>
        <MoonOrb palette={palette} />
      </group>
    )
  }
  if (normalized.includes('moth') || normalized.includes('wing')) {
    return <MothSculpture palette={palette} scale={scale} wingTilt={pulse * 0.12} />
  }
  if (normalized.includes('constellation') || normalized.includes('curtain') || normalized.includes('star')) {
    return (
      <group scale={scale}>
        <ConstellationCurtain palette={palette} side={1} />
      </group>
    )
  }
  return (
    <group scale={scale}>
      <SymbolicMonolith palette={palette} accentScale={1 + pulse * 0.2} />
    </group>
  )
}

function OrbitingTableauAssembly({
  frame,
  durationInFrames,
  palette,
  heroObject,
  orbitingObject,
  secondaryObject,
  orbitCount,
}: {
  frame: number
  durationInFrames: number
  palette: TableauPalette
  heroObject: string
  orbitingObject: string
  secondaryObject: string
  orbitCount: number
}) {
  const motion = interpolate(frame, [0, Math.max(durationInFrames - 1, 1)], [-0.14, 0.18])
  const pulse = interpolate(frame, [0, Math.max(durationInFrames - 1, 1)], [0.04, 0.16])
  const ringCount = Math.max(3, orbitCount || 3)
  const orbiters = Array.from({ length: Math.max(6, ringCount * 2) })
  const ringHeights = [1.1, 1.72, 2.28]
  const ringRadii = [2.25, 3.05, 3.88]
  return (
    <group rotation={[0.05, motion, 0]} position={[0, -0.9, 0]}>
      <fog attach="fog" args={[palette.shadow, 9, 28]} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2.1, 0]}>
        <circleGeometry args={[9.5, 64]} />
        <meshStandardMaterial color={palette.shadow} emissive={palette.chamber} emissiveIntensity={0.12} roughness={0.95} />
      </mesh>
      <mesh scale={[10.5, 10.5, 10.5]}>
        <sphereGeometry args={[1, 48, 48]} />
        <meshStandardMaterial color={palette.chamber} side={BackSide} roughness={1} metalness={0.02} />
      </mesh>
      <mesh position={[0, 1.4, 0]} scale={[0.78, 5.8, 0.78]}>
        <cylinderGeometry args={[0.9, 1.15, 1, 24]} />
        <meshBasicMaterial color={palette.glow} transparent opacity={0.12} depthWrite={false} blending={AdditiveBlending} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2.02, 0]} scale={[1.8, 1, 1]}>
        <circleGeometry args={[1.55, 48]} />
        <meshBasicMaterial color={palette.glow} transparent opacity={0.1} depthWrite={false} />
      </mesh>
      {[-1, -0.4, 0.35, 1].map((offset, index) => (
        <mesh key={`lichen-vein-${index}`} position={[offset * 5.2, 0.8, -4.5]} rotation={[0.04, offset * 0.1, offset * 0.06]} scale={[0.24, 4.3, 0.1]}>
          <boxGeometry args={[1, 1, 1]} />
          <meshStandardMaterial color={palette.mist} emissive={palette.mist} emissiveIntensity={0.52} transparent opacity={0.36} />
        </mesh>
      ))}
      {[-1, 1].map((side) => (
        <mesh key={`arch-${side}`} position={[side * 5.85, 1.35, -3.9]} rotation={[0, side * 0.12, 0]} scale={[0.42, 4.6, 0.42]}>
          <boxGeometry args={[1, 1, 1]} />
          <meshStandardMaterial color={palette.shadow} emissive={palette.chamber} emissiveIntensity={0.18} roughness={0.85} metalness={0.04} />
        </mesh>
      ))}
      {ringHeights.map((height, index) => (
        <mesh
          key={`orbit-ring-${index}`}
          position={[0, height, 0]}
          rotation={[Math.PI / 2, index * 0.22, index === 1 ? 0.36 : index === 2 ? -0.26 : 0]}
        >
          <torusGeometry args={[ringRadii[index], 0.018, 10, 120]} />
          <meshStandardMaterial color={palette.glow} emissive={palette.glow} emissiveIntensity={0.3} transparent opacity={0.28} />
        </mesh>
      ))}
      <mesh position={[0, 4.15, -1.8]} rotation={[Math.PI / 2.2, 0.12, 0]} scale={[1, 1, 1]}>
        <torusGeometry args={[5.6, 0.035, 10, 96, Math.PI * 0.72]} />
        <meshStandardMaterial color={palette.accent} emissive={palette.accent} emissiveIntensity={0.42} transparent opacity={0.72} />
      </mesh>
      <mesh position={[0.9, 4.45, -1.4]} rotation={[Math.PI / 2.28, -0.32, 0.1]} scale={[1, 1, 1]}>
        <torusGeometry args={[4.7, 0.028, 10, 96, Math.PI * 0.64]} />
        <meshStandardMaterial color={palette.star} emissive={palette.star} emissiveIntensity={0.52} transparent opacity={0.7} />
      </mesh>
      {[0, 1, 2, 3, 4].map((index) => (
        <mesh
          key={`canopy-star-${index}`}
          position={[-2.8 + index * 1.5, 4.4 + (index % 2) * 0.24, -1.4 - (index % 3) * 0.25]}
          scale={0.14 + (index % 2) * 0.05}
        >
          <sphereGeometry args={[1, 12, 12]} />
          <meshStandardMaterial color={palette.star} emissive={palette.star} emissiveIntensity={1.15} />
        </mesh>
      ))}
      <group position={[0, 1.6, 0]}>
        <Float speed={0.7} rotationIntensity={0.08} floatIntensity={0.22}>
          <TableauObject label={heroObject} palette={palette} scale={1.08} pulse={pulse} />
        </Float>
      </group>
      {orbiters.map((_, index) => {
        const ringIndex = index % ringCount
        const baseAngle = (index / orbiters.length) * Math.PI * 2
        const animatedAngle = baseAngle + frame * (0.007 + ringIndex * 0.0014)
        const radius = ringRadii[ringIndex]
        const x = Math.cos(animatedAngle) * radius
        const z = Math.sin(animatedAngle) * radius
        const y = ringHeights[ringIndex] + Math.sin(animatedAngle * 1.4 + index) * 0.18
        return (
          <group key={`orbiter-${index}`} position={[x, y, z]} rotation={[0, -animatedAngle + Math.PI / 2, 0]}>
            <Float speed={0.9 + index * 0.08} rotationIntensity={0.1} floatIntensity={0.16}>
              <TableauObject label={orbitingObject} palette={palette} scale={0.68 + ringIndex * 0.06} pulse={pulse} />
            </Float>
          </group>
        )
      })}
      <ConstellationCurtain palette={palette} side={-1} />
      <ConstellationCurtain palette={palette} side={1} />
      <group position={[0, 2.2, -4.5]} scale={0.7}>
        <TableauObject label={secondaryObject} palette={palette} scale={0.82} pulse={pulse} />
      </group>
      {[0, 1].map((index) => (
        <mesh
          key={`fog-sheet-${index}`}
          position={[index === 0 ? -2.4 : 2.1, -0.3 + index * 0.6, 2.4 + index * 0.5]}
          rotation={[0, index === 0 ? 0.34 : -0.28, 0]}
          scale={[5.2, 2.2, 1]}
        >
          <planeGeometry args={[1, 1]} />
          <meshBasicMaterial color={palette.mist} transparent opacity={0.08} depthWrite={false} blending={AdditiveBlending} />
        </mesh>
      ))}
    </group>
  )
}

function SymbolicDuetAssembly({
  frame,
  durationInFrames,
  palette,
  heroObject,
  secondaryObject,
}: {
  frame: number
  durationInFrames: number
  palette: TableauPalette
  heroObject: string
  secondaryObject: string
}) {
  const spread = interpolate(frame, [0, Math.max(durationInFrames - 1, 1)], [2.4, 3.2])
  const pulse = interpolate(frame, [0, Math.max(durationInFrames - 1, 1)], [0.02, 0.14])
  return (
    <group position={[0, -0.75, 0]} rotation={[0.04, interpolate(frame, [0, Math.max(durationInFrames - 1, 1)], [-0.08, 0.1]), 0]}>
      <fog attach="fog" args={[palette.shadow, 9, 24]} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.9, 0]}>
        <circleGeometry args={[8.4, 64]} />
        <meshStandardMaterial color={palette.shadow} emissive={palette.chamber} emissiveIntensity={0.12} roughness={0.95} />
      </mesh>
      <mesh scale={[9.6, 9.6, 9.6]}>
        <sphereGeometry args={[1, 48, 48]} />
        <meshStandardMaterial color={palette.chamber} side={BackSide} roughness={1} metalness={0.02} />
      </mesh>
      <group position={[-spread, 1.2, 0.4]}>
        <Float speed={0.8} rotationIntensity={0.08} floatIntensity={0.22}>
          <TableauObject label={heroObject} palette={palette} scale={0.92} pulse={pulse} />
        </Float>
      </group>
      <group position={[spread, 1.34, -0.25]}>
        <Float speed={0.95} rotationIntensity={0.08} floatIntensity={0.2}>
          <TableauObject label={secondaryObject} palette={palette} scale={0.86} pulse={pulse} />
        </Float>
      </group>
      <mesh position={[0, 1.25, -0.4]} rotation={[0.16, 0, 0]} scale={[4.8, 0.12, 1.4]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color={palette.accent} emissive={palette.accent} emissiveIntensity={0.35} transparent opacity={0.18} />
      </mesh>
      <ConstellationCurtain palette={palette} side={-1} />
      <ConstellationCurtain palette={palette} side={1} />
    </group>
  )
}

function SurrealCopyOverlay({
  scene,
  copyTreatment,
}: {
  scene: RemotionScene
  copyTreatment: string
}) {
  if (copyTreatment === 'none') {
    return null
  }

  if (copyTreatment === 'lower_third') {
    return (
      <div
        style={{
          position: 'absolute',
          left: 56,
          bottom: 52,
          maxWidth: 520,
          padding: '18px 22px',
          borderRadius: 22,
          background: 'rgba(8, 10, 18, 0.7)',
          border: '1px solid rgba(255,255,255,0.08)',
          color: '#f8efe0',
          fontFamily: FONT_BODY,
          fontSize: BODY_SIZE - 4,
          lineHeight: BODY_LINE_HEIGHT,
        }}
      >
        {scene.title}
      </div>
    )
  }

  return (
    <div
      style={{
        position: 'absolute',
        left: 56,
        top: 54,
        display: 'inline-flex',
        padding: '10px 16px',
        borderRadius: 999,
        background: 'rgba(8, 10, 18, 0.72)',
        border: '1px solid rgba(255,255,255,0.08)',
        color: '#f3d8b1',
        fontFamily: FONT_DATA,
        fontSize: LABEL_SIZE,
        letterSpacing: CAPTION_LETTER_SPACING,
        textTransform: 'uppercase',
      }}
    >
      {scene.title}
    </div>
  )
}

function SurrealTableau3D({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const { fps, width, height } = useVideoConfig()
  const reveal = spring({
    frame,
    fps,
    config: {
      damping: 16,
      stiffness: 86,
      mass: 1,
    },
  })
  const props = (scene.composition?.props ?? {}) as Record<string, unknown>
  const layoutVariant = semanticString(props, 'layoutVariant', 'symbolic_duet')
  const heroObject = semanticString(props, 'heroObject', scene.title || 'central hero object')
  const secondaryObject = semanticString(props, 'secondaryObject', 'symbolic counterform')
  const orbitingObject = semanticString(props, 'orbitingObject', 'orbiting forms')
  const orbitCount = semanticNumber(props, 'orbitCount', layoutVariant === 'orbit_tableau' ? 6 : 0)
  const environmentBackdrop = semanticString(props, 'environmentBackdrop', 'dreamlike cinematic chamber')
  const ambientDetails = semanticString(props, 'ambientDetails', '')
  const palette = resolveTableauPalette(normalizePaletteWords(props.paletteWords))
  const copyTreatment = semanticString(props, 'copyTreatment', 'none')
  const backgroundDescriptor = `${environmentBackdrop} ${ambientDetails}`.toLowerCase()
  const background = backgroundDescriptor.includes('sea')
    ? `radial-gradient(circle at 50% 18%, rgba(126,188,255,0.14), transparent 30%), linear-gradient(180deg, ${palette.background} 0%, #0d1830 58%, ${palette.shadow} 100%)`
    : `radial-gradient(circle at 50% 18%, rgba(255,190,120,0.16), transparent 30%), linear-gradient(180deg, ${palette.background} 0%, ${palette.chamber} 56%, ${palette.shadow} 100%)`
  const cameraZ = interpolate(reveal, [0, 1], [10.4, layoutVariant === 'orbit_tableau' ? 8.3 : 8.8])
  const cameraX = layoutVariant === 'orbit_tableau'
    ? Math.sin(frame / 58) * 0.4
    : Math.sin(frame / 92) * 0.18
  const vignetteOpacity = interpolate(reveal, [0, 1], [0.72, 0.9])

  return (
    <AbsoluteFill style={{ background }}>
      <div style={{ position: 'absolute', inset: 0 }}>
        <ThreeCanvas width={width} height={height} camera={{ position: [cameraX, 2.4, cameraZ], fov: 38 }}>
          <color attach="background" args={[palette.background]} />
          <ambientLight intensity={0.8} />
          <hemisphereLight intensity={0.95} color={palette.star} groundColor={palette.shadow} />
          <pointLight position={[0, 4.4, 1.8]} intensity={34} color={palette.glow} distance={22} decay={1.7} />
          <directionalLight position={[5.6, 7.8, 5.2]} intensity={1.9} color={palette.star} />
          <directionalLight position={[-5.2, 3.4, 2.2]} intensity={1.15} color={palette.accent} />
          {layoutVariant === 'orbit_tableau' ? (
            <OrbitingTableauAssembly
              frame={frame}
              durationInFrames={scene.durationInFrames}
              palette={palette}
              heroObject={heroObject}
              orbitingObject={orbitingObject}
              secondaryObject={secondaryObject}
              orbitCount={orbitCount}
            />
          ) : (
            <SymbolicDuetAssembly
              frame={frame}
              durationInFrames={scene.durationInFrames}
              palette={palette}
              heroObject={heroObject}
              secondaryObject={secondaryObject}
            />
          )}
        </ThreeCanvas>
      </div>
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          background: `radial-gradient(circle at 50% 50%, transparent 34%, rgba(2, 3, 7, ${vignetteOpacity}) 100%)`,
        }}
      >
        <SurrealCopyOverlay scene={scene} copyTreatment={copyTreatment} />
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
    // ── Clinical template compositions ──
    case 'cover_hook':
      return <CoverHookTemplate scene={scene} />
    case 'orientation':
      return <OrientationTemplate scene={scene} />
    case 'synthesis_summary':
      return <SynthesisSummaryTemplate scene={scene} />
    case 'closing_cta':
      return <ClosingCtaTemplate scene={scene} />
    case 'clinical_explanation':
      return <ClinicalExplanationTemplate scene={scene} />
    case 'metric_improvement':
      return <MetricImprovementTemplate scene={scene} />
    case 'brain_region_focus':
      return <BrainRegionFocusTemplate scene={scene} />
    case 'metric_comparison':
      return <MetricComparisonTemplate scene={scene} />
    case 'timeline_progression':
      return <TimelineProgressionTemplate scene={scene} />
    case 'analogy_metaphor':
      return <AnalogyMetaphorTemplate scene={scene} />
    case 'kinetic_statements':
    case 'kinetic_title':
    default:
      return <KineticTitleTemplate headline={headline} body={body} kicker={kicker} />
  }
}

function StaticOrMotionSceneVisual({ scene }: { scene: RemotionScene }) {
  const frame = useCurrentFrame()
  const panProgress = interpolate(frame, [0, Math.max(scene.durationInFrames - 1, 1)], [1.02, 1.08])
  const manifestation = resolveManifestation(scene)
  const family = String(scene.composition?.family || scene.motion?.templateId || '')
  const mode = String(scene.composition?.mode || (manifestation === 'native_remotion' ? 'native' : 'none'))
  const isMediaOverlayFamily = manifestation !== 'native_remotion' && BUILTIN_TEXT_LAYER_FAMILIES.has(family)

  if (mode === 'native' && family && !isMediaOverlayFamily) {
    return <MotionTemplateRenderer scene={scene} />
  }

  if (manifestation === 'authored_image' && scene.imageUrl) {
    const shouldPanImage = family === 'media_pan'
    return (
      <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
        <Img
          src={scene.imageUrl}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: shouldPanImage ? `scale(${panProgress})` : 'scale(1)',
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
  const manifestation = resolveManifestation(scene)

  if (manifestation === 'source_video') {
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
}: {
  scene: RemotionScene
}) {
  const textLayerKind = resolveTextLayerKind(scene)

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
}: CathodeRenderProps) {
  const hasTransitions = scenes.some((scene) => scene.composition?.transitionAfter?.kind)

  if (hasTransitions) {
    return (
      <AbsoluteFill style={{ backgroundColor: '#03050a' }}>
        <TransitionSeries>
          {scenes.map((scene, index) => (
            <React.Fragment key={scene.uid}>
              <TransitionSeries.Sequence durationInFrames={getSequenceDurationInFrames(scene)}>
                <SceneLayer scene={scene} />
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
            <SceneLayer scene={scene} />
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
