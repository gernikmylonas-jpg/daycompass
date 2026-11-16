import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'
import type { BadgeInfo } from './badges'

export type Category = 'body' | 'mind' | 'work' | 'schedule'

export interface Habit {
  id: string
  name: string
  frequency: string
  category: Category
  checked_in_today: boolean
  current_streak: number
  best_streak: number
}

export interface HeatmapDay {
  date: string
  count: number
}

export const useHabitsStore = defineStore('habits', () => {
  const habits = ref<Habit[]>([])
  const heatmap = ref<HeatmapDay[]>([])

  async function fetchHabits() {
    const { data } = await api.get<Habit[]>('/api/habits')
    habits.value = data
  }

  async function fetchHeatmap() {
    const { data } = await api.get<HeatmapDay[]>('/api/stats/heatmap', {
      params: { days: 119 },
    })
    heatmap.value = data
  }

  async function addHabit(name: string, category: Category) {
    const { data } = await api.post<Habit>('/api/habits', {
      name,
      frequency: 'daily',
      category,
    })
    habits.value.push(data)
  }

  async function updateHabit(habit: Habit, changes: { name?: string; category?: Category }) {
    const { data } = await api.put<Habit>(`/api/habits/${habit.id}`, changes)
    const index = habits.value.findIndex((h) => h.id === habit.id)
    if (index !== -1) habits.value[index] = data
  }

  async function fetchHabitHeatmap(id: string): Promise<HeatmapDay[]> {
    const { data } = await api.get<HeatmapDay[]>(`/api/habits/${id}/heatmap`, {
      params: { days: 119 },
    })
    return data
  }

  async function checkIn(habit: Habit): Promise<BadgeInfo[]> {
    const { data } = await api.post<{ new_badges?: BadgeInfo[] }>(`/api/habits/${habit.id}/check-in`)
    await Promise.all([fetchHabits(), fetchHeatmap()])
    return data.new_badges ?? []
  }

  async function removeHabit(id: string) {
    await api.delete(`/api/habits/${id}`)
    habits.value = habits.value.filter((h) => h.id !== id)
    await fetchHeatmap()
  }

  return {
    habits,
    heatmap,
    fetchHabits,
    fetchHeatmap,
    fetchHabitHeatmap,
    addHabit,
    updateHabit,
    checkIn,
    removeHabit,
  }
})
