import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'
import type { BadgeInfo } from './badges'

export interface WallpaperItem { id: string; cost: number; theme: string }
export interface Unlock { id: string; cost: number; unlocked_at: string }
export interface Nuggets {
  points: number; earned: number; spent: number; balance: number
  points_per_nugget: number; next_in: number; unlocked: Unlock[]; catalog: WallpaperItem[]
}

// Gold nuggets: 1 for every 10 points earned, spent on wallpapers. The server keeps the ledger.
export const useNuggetsStore = defineStore('nuggets', () => {
  const data = ref<Nuggets | null>(null)

  async function fetch() {
    try {
      data.value = (await api.get<Nuggets>('/api/nuggets')).data
    } catch {
      // the chip keeps its last value
    }
  }

  async function unlock(id: string) {
    const res = (await api.post<Nuggets & { new_badges?: BadgeInfo[] }>(`/api/nuggets/wallpapers/${id}/unlock`)).data
    data.value = res
    return res.new_badges ?? []
  }

  const isUnlocked = (id: string) => !!data.value?.unlocked.some((u) => u.id === id)

  return { data, fetch, unlock, isUnlocked }
})
