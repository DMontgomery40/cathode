import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequest, jsonBody } from './client'
import type { Job } from './jobs'
import type { ProjectSummary } from './projects'
import type { Brief, Plan } from '../schemas/plan'

export interface Bootstrap {
  providers: {
    api_keys?: Record<string, boolean>
    llm_provider?: string | null
    image_providers: string[]
    video_providers: string[]
    render_backends?: string[]
    remotion_available?: boolean
    remotion_capabilities?: Record<string, boolean>
    tts_providers?: Record<string, string>
    tts_voice_options?: Record<string, Array<{ value: string; label: string; description: string }>>
    image_edit_models?: string[]
    cost_catalog?: unknown
  }
  defaults: {
    brief: Partial<Brief>
    render_profile: Record<string, unknown>
    image_profile: Record<string, unknown>
    video_profile: Record<string, unknown>
    tts_profile: Record<string, unknown>
  }
  projects: string[]
}

export interface MakeVideoRequest {
  project_name: string
  brief: Record<string, unknown>
  provider?: string | null
  image_profile?: Record<string, unknown> | null
  video_profile?: Record<string, unknown> | null
  agent_demo_profile?: Record<string, unknown> | null
  tts_profile?: Record<string, unknown> | null
  render_profile?: Record<string, unknown> | null
  overwrite?: boolean
  run_until?: string | null
}

export interface ShortFormRequest {
  project_name: string
  source_material?: string
  source_transcript?: string
  footage_notes?: string
  audience?: string
  hook_promise?: string
  payoff?: string
  ending_cta?: string
  short_form_tier?: string
  approach?: string
  caption_strategy?: string
  platform_targets?: string[]
  runtime_seconds?: number
  tone?: string
  visual_style?: string
  must_include?: string
  must_avoid?: string
  source_anchor_card?: string
  source_context_lock?: string
  subject?: string
  domain?: string
  setting?: string
  actors?: string
  primary_objects?: string
  workflow_action?: string
  visual_anchors?: string
  supported_claims?: string
  evidence_boundary?: string
  allowed_metaphors?: string
  forbidden_drift?: string
  caption_timing_source?: string
  caption_renderer?: string
  voice_direction?: string
  motion_intensity?: string
  available_footage?: string
  footage_manifest?: Record<string, unknown>[]
  style_reference_summary?: string
  style_reference_paths?: string[]
  paid_media_budget_usd?: string
  image_profile?: Record<string, unknown> | null
  provider?: string | null
  overwrite?: boolean
  run_until?: string | null
}

export interface ShortFormOption {
  value: string
  label: string
  description?: string
}

export interface ShortFormPayload {
  project_name: string
  brief: Record<string, unknown>
  render_profile: Record<string, unknown>
  video_profile: Record<string, unknown>
  tts_profile: Record<string, unknown>
  image_profile?: Record<string, unknown> | null
  runtime_seconds: number
  run_until: string
  preview?: Record<string, unknown>
}

export interface ShortFormOptions {
  tiers: ShortFormOption[]
  approaches: ShortFormOption[]
  caption_strategies: ShortFormOption[]
  platform_targets: ShortFormOption[]
  run_until: ShortFormOption[]
  defaults: {
    short_form_tier: string
    approach: string
    caption_strategy: string
    platform_targets: string[]
    runtime_seconds: number
    run_until: string
    render_profile: Record<string, unknown>
  }
}

export function useBootstrap() {
  return useQuery({
    queryKey: ['bootstrap'],
    queryFn: () => apiRequest<Bootstrap>('/api/bootstrap'),
  })
}

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => apiRequest<ProjectSummary[]>('/api/projects'),
  })
}

export function usePlan(project: string | null | undefined) {
  return useQuery({
    queryKey: ['project', project, 'plan'],
    enabled: Boolean(project && project !== 'new'),
    queryFn: () => apiRequest<Plan>(`/api/projects/${encodeURIComponent(String(project))}/plan`),
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['create project'],
    mutationFn: (body: {
      project_name: string
      brief: Record<string, unknown>
      provider?: string | null
      image_profile?: Record<string, unknown> | null
      video_profile?: Record<string, unknown> | null
      agent_demo_profile?: Record<string, unknown> | null
      tts_profile?: Record<string, unknown> | null
      render_profile?: Record<string, unknown> | null
      overwrite?: boolean
    }) => apiRequest<Plan>('/api/projects', {
      method: 'POST',
      body: jsonBody(body),
    }),
    onSuccess: (plan) => {
      const project = String(plan.meta?.project_name ?? '')
      if (project) {
        queryClient.setQueryData(['project', project, 'plan'], plan)
      }
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useRebuildStoryboard(project: string | null | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['rebuild storyboard', String(project ?? '')],
    mutationFn: (body?: { brief?: Record<string, unknown>; provider?: string | null; agent_demo_profile?: Record<string, unknown> | null }) => apiRequest<Plan>(
      `/api/projects/${encodeURIComponent(String(project))}/storyboard`,
      {
        method: 'POST',
        body: jsonBody(body ?? {}),
      },
    ),
    onSuccess: (plan) => {
      queryClient.setQueryData(['project', project, 'plan'], plan)
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useStartMakeVideoJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['start make video'],
    mutationFn: (body: MakeVideoRequest) => apiRequest<Job>('/api/jobs/make-video', {
      method: 'POST',
      body: jsonBody(body),
    }),
    onSuccess: (job) => {
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
      if (job.project_name) {
        void queryClient.invalidateQueries({ queryKey: ['project', job.project_name, 'jobs'] })
      }
    },
  })
}

export function useShortFormOptions() {
  return useQuery({
    queryKey: ['short form', 'options'],
    queryFn: () => apiRequest<ShortFormOptions>('/api/short-form/options'),
  })
}

export function usePreviewShortForm() {
  return useMutation({
    mutationKey: ['preview short form'],
    mutationFn: (body: ShortFormRequest) => apiRequest<ShortFormPayload>('/api/short-form/preview', {
      method: 'POST',
      body: jsonBody(body),
    }),
  })
}

export function useStartShortFormJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['start short form'],
    mutationFn: (body: ShortFormRequest) => apiRequest<Job>('/api/short-form/jobs', {
      method: 'POST',
      body: jsonBody(body),
    }),
    onSuccess: (job) => {
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
      if (job.project_name) {
        void queryClient.invalidateQueries({ queryKey: ['project', job.project_name, 'jobs'] })
      }
    },
  })
}

function uploadFiles(path: string, files: File[]) {
  const body = new FormData()
  files.forEach((file) => body.append('files', file))
  return apiRequest<Plan>(path, {
    method: 'POST',
    body,
  })
}

export function useUploadFootage(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['upload footage', project],
    mutationFn: (files: File[]) => uploadFiles(`/api/projects/${encodeURIComponent(project)}/footage`, files),
    onSuccess: (plan) => {
      queryClient.setQueryData(['project', project, 'plan'], plan)
    },
  })
}

export function useUploadStyleRefs(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['upload style refs', project],
    mutationFn: (files: File[]) => uploadFiles(`/api/projects/${encodeURIComponent(project)}/style-refs`, files),
    onSuccess: (plan) => {
      queryClient.setQueryData(['project', project, 'plan'], plan)
    },
  })
}

export function useRemotionManifest(project: string | null | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['project', project, 'remotion-manifest'],
    enabled: Boolean(project && (options?.enabled ?? true)),
    queryFn: () => apiRequest<Record<string, unknown>>(`/api/projects/${encodeURIComponent(String(project))}/remotion-manifest`),
    retry: false,
  })
}
