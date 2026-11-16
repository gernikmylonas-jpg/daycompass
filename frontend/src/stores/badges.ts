import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export interface BadgeInfo {
  code: string
  name: string
  description: string
  icon: string
}

export interface BadgeStatus extends BadgeInfo {
  earned: boolean
  awarded_at: string | null
}

export const useBadgesStore = defineStore('badges', () => {
  const badges = ref<BadgeStatus[]>([])
  const toasts = ref<BadgeInfo[]>([])

  async function fetchBadges() {
    const { data } = await api.get<BadgeStatus[]>('/api/badges')
    badges.value = data
  }

  async function announce(newBadges: BadgeInfo[] | undefined) {
    if (!newBadges || newBadges.length === 0) return
    toasts.value = newBadges
    window.setTimeout(() => {
      toasts.value = []
    }, 6000)
    await fetchBadges()
  }

  function dismiss() {
    toasts.value = []
  }

  return { badges, toasts, fetchBadges, announce, dismiss }
})
