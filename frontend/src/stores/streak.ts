import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

// Daily streak: days in a row with at least one habit check-in.
export const useStreakStore = defineStore('streak', () => {
  const current = ref(0)
  const best = ref(0)
  const activeToday = ref(false)
  const loaded = ref(false)

  async function fetch() {
    try {
      const { data } = await api.get<{ current: number; best: number; active_today: boolean }>('/api/stats/streak')
      current.value = data.current
      best.value = data.best
      activeToday.value = data.active_today
    } catch {
      // the chip simply keeps its last value
    } finally {
      loaded.value = true
    }
  }

  return { current, best, activeToday, loaded, fetch }
})
