import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import { workspaceLayout } from '../design-system/layout'

interface UIState {
  railCollapsed: boolean
  toggleRail: () => void
  railWidth: number
  setRailWidth: (width: number) => void
  resetRailWidth: () => void
  selectedSceneId: string | null
  setSelectedScene: (id: string | null) => void
  commandPaletteOpen: boolean
  setCommandPaletteOpen: (open: boolean) => void
  sceneTimelineHeight: number
  setSceneTimelineHeight: (height: number) => void
  resetSceneTimelineHeight: () => void
  expandSceneTimeline: () => void
  sceneInspectorWidth: number
  setSceneInspectorWidth: (width: number) => void
  resetSceneInspectorWidth: () => void
  sceneInspectorCollapsed: boolean
  toggleSceneInspectorCollapsed: () => void
  openSceneInspector: () => void
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      railCollapsed: false,
      toggleRail: () => set((s) => ({ railCollapsed: !s.railCollapsed })),
      railWidth: workspaceLayout.rail.default,
      setRailWidth: (width) => set({
        railWidth: clamp(width, workspaceLayout.rail.min, workspaceLayout.rail.max),
      }),
      resetRailWidth: () => set({ railWidth: workspaceLayout.rail.default }),
      selectedSceneId: null,
      setSelectedScene: (id) => set({ selectedSceneId: id }),
      commandPaletteOpen: false,
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      sceneTimelineHeight: workspaceLayout.timeline.default,
      setSceneTimelineHeight: (height) => set({
        sceneTimelineHeight: clamp(height, workspaceLayout.timeline.min, workspaceLayout.timeline.max),
      }),
      resetSceneTimelineHeight: () => set({ sceneTimelineHeight: workspaceLayout.timeline.default }),
      expandSceneTimeline: () => set({
        sceneTimelineHeight: Math.round(
          workspaceLayout.timeline.min + ((workspaceLayout.timeline.max - workspaceLayout.timeline.min) * 0.72),
        ),
      }),
      sceneInspectorWidth: workspaceLayout.inspector.default,
      setSceneInspectorWidth: (width) => set({
        sceneInspectorWidth: clamp(width, workspaceLayout.inspector.min, workspaceLayout.inspector.max),
      }),
      resetSceneInspectorWidth: () => set({ sceneInspectorWidth: workspaceLayout.inspector.default }),
      sceneInspectorCollapsed: false,
      toggleSceneInspectorCollapsed: () => set((state) => ({
        sceneInspectorCollapsed: !state.sceneInspectorCollapsed,
      })),
      openSceneInspector: () => set({ sceneInspectorCollapsed: false }),
    }),
    {
      name: 'cathode-ui',
      storage: createJSONStorage(() => window.localStorage),
      partialize: (state) => ({
        railCollapsed: state.railCollapsed,
        railWidth: state.railWidth,
        sceneTimelineHeight: state.sceneTimelineHeight,
        sceneInspectorWidth: state.sceneInspectorWidth,
        sceneInspectorCollapsed: state.sceneInspectorCollapsed,
      }),
    },
  ),
)
