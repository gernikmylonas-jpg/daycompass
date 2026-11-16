<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { useHabitsStore, type Category, type Habit, type HeatmapDay } from '../stores/habits'
import Heatmap from '../components/Heatmap.vue'
import BadgesPanel from '../components/BadgesPanel.vue'
import BadgeToast from '../components/BadgeToast.vue'
import { useBadgesStore } from '../stores/badges'

const auth = useAuthStore()
const habitsStore = useHabitsStore()
const badgesStore = useBadgesStore()
const router = useRouter()

const error = ref('')
const newNames = ref<Record<Category, string>>({
  body: '',
  mind: '',
  work: '',
  schedule: '',
})

const editingId = ref<string | null>(null)
const editName = ref('')
const editCategory = ref<Category>('body')

const selectedId = ref<string | null>(null)
const selectedDays = ref<HeatmapDay[]>([])

const selectedHabit = computed(
  () => habitsStore.habits.find((h) => h.id === selectedId.value) ?? null,
)

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

async function loadSelected() {
  if (!selectedId.value) return
  try {
    selectedDays.value = await habitsStore.fetchHabitHeatmap(selectedId.value)
  } catch (e) {
    showError(e)
  }
}

async function selectHabit(habit: Habit) {
  if (selectedId.value === habit.id) {
    closeSelected()
    return
  }
  selectedId.value = habit.id
  selectedDays.value = []
  await loadSelected()
}

function closeSelected() {
  selectedId.value = null
  selectedDays.value = []
}

function startEdit(habit: Habit) {
  editingId.value = habit.id
  editName.value = habit.name
  editCategory.value = habit.category
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit(habit: Habit) {
  const name = editName.value.trim()
  if (!name) return
  error.value = ''
  try {
    await habitsStore.updateHabit(habit, { name, category: editCategory.value })
    editingId.value = null
  } catch (e) {
    showError(e)
  }
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
    const newBadges = await habitsStore.checkIn(habit)
    await auth.refreshUser()
    await badgesStore.announce(newBadges)
    if (selectedId.value === habit.id) await loadSelected()
  } catch (e) {
    showError(e)
  }
}

async function remove(habit: Habit) {
  error.value = ''
  try {
    await habitsStore.removeHabit(habit.id)
    if (selectedId.value === habit.id) closeSelected()
    if (editingId.value === habit.id) editingId.value = null
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
    await Promise.all([habitsStore.fetchHabits(), habitsStore.fetchHeatmap(), auth.refreshUser()])
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
          <RouterLink to="/pomodoro" class="text-slate-600 text-sm hover:text-slate-900 underline">Pomodoro</RouterLink>
          <RouterLink to="/calendar" class="text-slate-600 text-sm hover:text-slate-900 underline">Ημερολόγιο</RouterLink>
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
            <li v-for="h in habitsIn(d.key)" :key="h.id">
              <form v-if="editingId === h.id" @submit.prevent="saveEdit(h)" class="space-y-2">
                <input v-model="editName" type="text" maxlength="100" @keyup.esc="cancelEdit"
                  class="w-full border rounded-lg px-3 py-1.5 text-sm" />
                <select v-model="editCategory" class="w-full border rounded-lg px-2 py-1.5 text-sm">
                  <option v-for="o in directions" :key="o.key" :value="o.key">
                    {{ o.title }} – {{ o.subtitle }}
                  </option>
                </select>
                <div class="flex gap-2">
                  <button type="submit"
                    class="bg-slate-800 text-white rounded-lg px-3 py-1 text-sm hover:bg-slate-700">
                    Αποθήκευση
                  </button>
                  <button type="button" @click="cancelEdit"
                    class="border border-slate-300 text-slate-600 rounded-lg px-3 py-1 text-sm hover:bg-slate-50">
                    Άκυρο
                  </button>
                </div>
              </form>

              <div v-else class="flex items-center gap-2">
                <button @click="toggle(h)" :disabled="h.checked_in_today"
                  :class="['w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs shrink-0',
                    h.checked_in_today ? 'bg-green-500 border-green-500 text-white' : 'border-slate-300 hover:border-slate-500']">
                  <span v-if="h.checked_in_today">✓</span>
                </button>
                <span :class="['flex-1 text-sm', h.checked_in_today ? 'line-through text-slate-400' : 'text-slate-700']">
                  {{ h.name }}
                </span>
                <span v-if="h.current_streak > 0" class="text-xs text-orange-500 whitespace-nowrap"
                  :title="`Καλύτερο streak: ${h.best_streak}`">🔥 {{ h.current_streak }}</span>
                <button @click="selectHabit(h)"
                  :class="['text-sm', selectedId === h.id ? 'text-green-600' : 'text-slate-300 hover:text-slate-600']"
                  title="Heatmap">📊</button>
                <button @click="startEdit(h)" class="text-slate-300 hover:text-slate-600 text-sm" title="Επεξεργασία">✎</button>
                <button @click="remove(h)" class="text-slate-300 hover:text-red-500 text-sm" title="Διαγραφή">✕</button>
              </div>
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

      <div class="mt-4 space-y-4">
        <div v-if="selectedHabit" class="space-y-2">
          <div class="flex items-center justify-between text-sm text-slate-600 px-1">
            <span>🔥 Τρέχον: {{ selectedHabit.current_streak }} · 🏆 Καλύτερο: {{ selectedHabit.best_streak }}</span>
            <button @click="closeSelected" class="hover:text-slate-900">Κλείσιμο ✕</button>
          </div>
          <Heatmap :days="selectedDays" :title="`Heatmap: ${selectedHabit.name}`" />
        </div>

        <Heatmap :days="habitsStore.heatmap" title="Δραστηριότητα (όλα τα habits)" />
        <BadgesPanel />
      </div>
      <BadgeToast />
    </div>
  </div>
</template>
