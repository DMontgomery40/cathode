import { create } from 'zustand'

export interface NotificationItem {
  id: string
  title: string
  description?: string
  tone?: 'info' | 'success' | 'warning' | 'danger'
}

interface NotificationState {
  items: NotificationItem[]
  notify: (item: Omit<NotificationItem, 'id'>) => void
  dismiss: (id: string) => void
}

export const useNotificationsStore = create<NotificationState>((set) => ({
  items: [],
  notify: (item) => {
    const id = `note_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    set((state) => ({
      items: [...state.items, { id, ...item }].slice(-6),
    }))
    window.setTimeout(() => {
      set((state) => ({ items: state.items.filter((entry) => entry.id != id) }))
    }, 6000)
  },
  dismiss: (id) => set((state) => ({ items: state.items.filter((entry) => entry.id !== id) })),
}))
