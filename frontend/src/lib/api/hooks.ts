import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchBootstrap } from './bootstrap.ts'
import { fetchProjects, createProject } from './projects.ts'
import { fetchPlan, fetchRemotionManifest, rebuildStoryboard } from './plans.ts'
import { dispatchMakeVideo, type MakeVideoJobRequest } from './jobs.ts'
import { uploadStyleRefs } from './style-refs.ts'
import { uploadFootage } from './footage.ts'
import type { Plan } from '../schemas/plan.ts'

export function useBootstrap() {
  return useQuery({
    queryKey: ['bootstrap'],
    queryFn: fetchBootstrap,
    staleTime: 60_000,
  })
}

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  })
}

export function usePlan(project: string) {
  return useQuery({
    queryKey: ['plan', project],
    queryFn: () => fetchPlan(project),
    enabled: !!project && project !== 'new',
  })
}

export function useRemotionManifest(project: string, opts?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['remotion-manifest', project],
    queryFn: () => fetchRemotionManifest(project),
    enabled: Boolean(project && project !== 'new' && opts?.enabled !== false),
  })
}

export function useCreateProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useStartMakeVideoJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (request: MakeVideoJobRequest) => dispatchMakeVideo(request),
    onSuccess: (_, request) => {
      void qc.invalidateQueries({ queryKey: ['projects'] })
      void qc.invalidateQueries({ queryKey: ['jobs', request.project_name] })
    },
  })
}

export function useRebuildStoryboard(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload?: { provider?: string; brief?: Record<string, unknown>; agent_demo_profile?: Record<string, unknown> }) => rebuildStoryboard(project, payload),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
      void qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useUploadStyleRefs(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['upload style refs', project],
    mutationFn: (files: File[]) => uploadStyleRefs(project, files),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
    },
  })
}

export function useUploadFootage(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['upload footage', project],
    mutationFn: (files: File[]) => uploadFootage(project, files),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
    },
  })
}
