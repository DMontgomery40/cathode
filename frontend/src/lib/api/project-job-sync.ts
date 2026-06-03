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
  const stageKey = stages.join('\0')

  useEffect(() => {
    const stageSet = new Set(stageKey.split('\0').filter(Boolean))
    for (const job of jobs ?? []) {
      if (!job.job_id || seenRef.current.has(job.job_id)) {
        continue
      }
      const stage = job.requested_stage || job.current_stage
      if (!stageSet.has(stage) || !DONE.has(job.status)) {
        continue
      }
      seenRef.current.add(job.job_id)
      void queryClient.invalidateQueries({ queryKey: ['project', project, 'plan'] })
      void queryClient.invalidateQueries({ queryKey: ['project', project, 'jobs'] })
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
    }
  }, [jobs, project, queryClient, stageKey])
}
