import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export type Category = 'body' | 'mind' | 'work' | 'schedule'

export interface Habit {
  id: string
  name: string
  frequency: string
  category: Category
  checked_in_today: boolean
}

export const useHabitsStore = defineStore('habits', () => {
  const habits = ref<Habit[]>([])

  async function fetchHabits() {
    const { data } = await api.get<Habit[]>('/api/habits')
    habits.value = data
  }

  async function addHabit(name: string, category: Category) {
    const { data } = await api.post<Habit>('/api/habits', {
      name,
      frequency: 'daily',
      category,
    })
    habits.value.push({ ...data, checked_in_today: false })
  }

  async function checkIn(habit: Habit) {
    await api.post(`/api/habits/${habit.id}/check-in`)
    habit.checked_in_today = true
  }

  async function removeHabit(id: string) {
    await api.delete(`/api/habits/${id}`)
    habits.value = habits.value.filter((h) => h.id !== id)
  }

  return { habits, fetchHabits, addHabit, checkIn, removeHabit }
})