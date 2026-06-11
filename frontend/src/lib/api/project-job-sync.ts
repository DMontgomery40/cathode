import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { Job } from './jobs'

const DONE = new Set(['succeeded', 'partial_success', 'failed', 'cancelled'])

export function useInvalidateProjectOnJobCompletion(
  project: string,
  jobs: Job[] | undefined,
  stages: string[],
) {
  const queryClient = useQueryClient()
  const seenRef = useRef<Set<string>>(new Set())
  const progressRef = useRef<Map<string, string>>(new Map())
  const stageKey = stages.join('\0')

  useEffect(() => {
    const stageSet = new Set(stageKey.split('\0').filter(Boolean))
    for (const job of jobs ?? []) {
      if (!job.job_id) {
        continue
      }
      const stage = job.requested_stage || job.current_stage
      if (!stageSet.has(stage)) {
        continue
      }

      // The asset pass writes each scene's media into plan.json as it lands;
      // refetch the plan on every step transition so the timeline fills in
      // live instead of staying frozen until the whole job finishes. The
      // first observation is skipped — the plan was just fetched on mount.
      if (job.status === 'running' || job.status === 'queued') {
        const signature = (job.steps ?? [])
          .map((step) => `${step.id}:${step.status}`)
          .join('|')
        if (progressRef.current.get(job.job_id) !== signature) {
          const firstObservation = !progressRef.current.has(job.job_id)
          progressRef.current.set(job.job_id, signature)
          if (!firstObservation) {
            void queryClient.invalidateQueries({ queryKey: ['project', project, 'plan'] })
            void queryClient.invalidateQueries({ queryKey: ['projects'] })
          }
        }
        continue
      }

      if (seenRef.current.has(job.job_id) || !DONE.has(job.status)) {
        continue
      }
      seenRef.current.add(job.job_id)
      void queryClient.invalidateQueries({ queryKey: ['project', project, 'plan'] })
      void queryClient.invalidateQueries({ queryKey: ['project', project, 'jobs'] })
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
    }
  }, [jobs, project, queryClient, stageKey])
}
