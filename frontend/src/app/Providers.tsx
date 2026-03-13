import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import { getApiErrorMessage } from '../lib/api/errors'
import { useNotificationsStore } from '../stores/notifications'

const queryClient = new QueryClient({
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      useNotificationsStore.getState().notify({
        title: mutation.options.mutationKey?.join(' ') || 'Action failed',
        description: getApiErrorMessage(error, 'The request failed before Cathode could finish it.'),
        tone: 'danger',
      })
    },
  }),
  queryCache: new QueryCache({
    onError: (error, query) => {
      if (query.state.data !== undefined) {
        useNotificationsStore.getState().notify({
          title: query.queryKey.join(' ') || 'Refresh failed',
          description: getApiErrorMessage(error, 'Cathode could not refresh this surface.'),
          tone: 'warning',
        })
      }
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

export function Providers() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}
