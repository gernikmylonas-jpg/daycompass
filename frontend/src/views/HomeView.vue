<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { useHabitsStore, type Category, type Habit } from '../stores/habits'

const auth = useAuthStore()
const habitsStore = useHabitsStore()
const router = useRouter()

const error = ref('')
const newNames = ref<Record<Category, string>>({
  body: '',
  mind: '',
  work: '',
  schedule: '',
})

const directions: {
  key: Category
  title: string
  subtitle: string
  position: string
  accent: string
}[] = [
  { key: 'body', title: 'Βορράς', subtitle: 'Σώμα', position: 'md:col-start-2 md:row-start-1', accent: 'border-teal-500' },
  { key: 'work', title: 'Δύση', subtitle: 'Δουλειά & μελέτη', position: 'md:col-start-1 md:row-start-2', accent: 'border-orange-500' },
  { key: 'schedule', title: 'Ανατολή', subtitle: 'Πρόγραμμα', position: 'md:col-start-3 md:row-start-2', accent: 'border-pink-500' },
  { key: 'mind', title: 'Νότος', subtitle: 'Mental health', position: 'md:col-start-2 md:row-start-3', accent: 'border-purple-500' },
]

function habitsIn(category: Category) {
  return habitsStore.habits.filter((h) => h.category === category)
}

function showError(e: unknown) {
  error.value = axios.isAxiosError(e)
    ? (e.response?.data?.detail ?? 'Κάτι πήγε στραβά')
    : 'Κάτι πήγε στραβά'
}

async function add(category: Category) {
  const name = newNames.value[category].trim()
  if (!name) return
  error.value = ''
  try {
    await habitsStore.addHabit(name, category)
    newNames.value[category] = ''
  } catch (e) {
    showError(e)
  }
}

async function toggle(habit: Habit) {
  if (habit.checked_in_today) return
  error.value = ''
  try {
    await habitsStore.checkIn(habit)
    await auth.refreshUser()
  } catch (e) {
    showError(e)
  }
}

async function remove(habit: Habit) {
  error.value = ''
  try {
    await habitsStore.removeHabit(habit.id)
  } catch (e) {
    showError(e)
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(async () => {
  try {
    await Promise.all([habitsStore.fetchHabits(), auth.refreshUser()])
  } catch (e) {
    showError(e)
  }
})
</script>

<template>
  <div class="min-h-screen bg-slate-100 p-4 md:p-8">
    <div class="max-w-5xl mx-auto">
      <header class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-slate-800">DayCompass</h1>
        <div class="flex items-center gap-4">
          <span class="text-slate-600 text-sm">{{ auth.user?.name }}</span>
          <button @click="logout"
            class="bg-slate-800 text-white rounded-lg px-4 py-2 text-sm hover:bg-slate-700">
            Αποσύνδεση
          </button>
        </div>
      </header>

      <p v-if="error" class="text-red-600 text-sm mb-4">{{ error }}</p>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <section v-for="d in directions" :key="d.key"
          :class="['bg-white rounded-xl shadow p-4 space-y-3 border-t-4', d.accent, d.position]">
          <div>
            <h2 class="text-lg font-bold text-slate-800">{{ d.title }}</h2>
            <p class="text-slate-500 text-sm">{{ d.subtitle }}</p>
          </div>

          <ul class="space-y-2">
            <li v-for="h in habitsIn(d.key)" :key="h.id" class="flex items-center gap-2">
              <button @click="toggle(h)" :disabled="h.checked_in_today"
                :class="['w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs shrink-0',
                  h.checked_in_today ? 'bg-green-500 border-green-500 text-white' : 'border-slate-300 hover:border-slate-500']">
                <span v-if="h.checked_in_today">✓</span>
              </button>
              <span :class="['flex-1 text-sm', h.checked_in_today ? 'line-through text-slate-400' : 'text-slate-700']">
                {{ h.name }}
              </span>
              <button @click="remove(h)" class="text-slate-300 hover:text-red-500 text-sm" title="Διαγραφή">✕</button>
            </li>
            <li v-if="habitsIn(d.key).length === 0" class="text-slate-400 text-sm">
              Κανένα habit ακόμα
            </li>
          </ul>

          <form @submit.prevent="add(d.key)" class="flex gap-2">
            <input v-model="newNames[d.key]" type="text" placeholder="Νέο habit..."
              class="flex-1 border rounded-lg px-3 py-1.5 text-sm" />
            <button type="submit"
              class="bg-slate-800 text-white rounded-lg px-3 text-sm hover:bg-slate-700">+</button>
          </form>
        </section>

        <section
          class="bg-slate-800 text-white rounded-xl shadow p-4 flex flex-col items-center justify-center md:col-start-2 md:row-start-2">
          <p class="text-sm text-slate-300">Σύνολο πόντων</p>
          <p class="text-5xl font-bold">{{ auth.user?.total_points }}</p>
        </section>
      </div>
    </div>
  </div>
</template>