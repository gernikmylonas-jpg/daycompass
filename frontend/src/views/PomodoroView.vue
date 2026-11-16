<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'
import axios from 'axios'
import api from '../api'
import BadgeToast from '../components/BadgeToast.vue'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'

interface Session {
  id: string
  kind: 'work' | 'reading'
  title: string | null
  duration_minutes: number
  session_date: string
  completed_at: string
}

interface Summary {
  today_minutes: number
  today_sessions: number
  total_minutes: number
  total_sessions: number
  recent: Session[]
}

const badgesStore = useBadgesStore()
const kind = ref<'work' | 'reading'>('work')
const title = ref('')
const earned = ref('')
const workMinutes = ref(25)
const breakMinutes = ref(5)
const phase = ref<'work' | 'break'>('work')
const running = ref(false)
const remaining = ref(workMinutes.value * 60)
const summary = ref<Summary | null>(null)
const error = ref('')

let endAt = 0
let timer: number | undefined

const display = computed(() => {
  const m = Math.floor(remaining.value / 60)
  const s = remaining.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const phaseLabel = computed(() => (phase.value === 'work' ? 'Εστίαση' : 'Διάλειμμα'))

function totalSeconds() {
  return (phase.value === 'work' ? workMinutes.value : breakMinutes.value) * 60
}

function showError(e: unknown) {
  error.value = axios.isAxiosError(e)
    ? (e.response?.data?.detail ?? 'Κάτι πήγε στραβά')
    : 'Κάτι πήγε στραβά'
}

async function loadSummary() {
  try {
    const { data } = await api.get<Summary>('/api/pomodoro/summary')
    summary.value = data
  } catch (e) {
    showError(e)
  }
}

function stopTimer() {
  running.value = false
  if (timer !== undefined) {
    window.clearInterval(timer)
    timer = undefined
  }
  document.title = 'DayCompass'
}

function tick() {
  remaining.value = Math.max(0, Math.round((endAt - Date.now()) / 1000))
  document.title = `${display.value} · ${phaseLabel.value}`
  if (remaining.value <= 0) finishPhase()
}

function startTimer() {
  endAt = Date.now() + remaining.value * 1000
  running.value = true
  timer = window.setInterval(tick, 250)
}

async function finishPhase() {
  stopTimer()
  if (phase.value === 'work') {
    try {
      const { data } = await api.post<{ new_badges?: BadgeInfo[] }>('/api/pomodoro', {
        kind: kind.value,
        title: title.value.trim() || null,
        duration_minutes: workMinutes.value,
      })
      earned.value = '🎉 +5 πόντοι!'
      await loadSummary()
      await badgesStore.announce(data.new_badges)
    } catch (e) {
      showError(e)
    }
    phase.value = 'break'
    remaining.value = totalSeconds()
    startTimer()
  } else {
    phase.value = 'work'
    remaining.value = totalSeconds()
  }
}

function toggle() {
  error.value = ''
  earned.value = ''
  if (running.value) {
    stopTimer()
  } else {
    startTimer()
  }
}

function reset() {
  stopTimer()
  phase.value = 'work'
  remaining.value = totalSeconds()
}

function applySettings() {
  if (running.value) return
  workMinutes.value = Math.min(180, Math.max(1, Math.floor(workMinutes.value || 25)))
  breakMinutes.value = Math.min(60, Math.max(1, Math.floor(breakMinutes.value || 5)))
  remaining.value = totalSeconds()
}

function kindLabel(k: string) {
  return k === 'work' ? 'Δουλειά' : 'Διάβασμα'
}

function formatWhen(iso: string) {
  return new Date(iso + 'Z').toLocaleString('el-GR', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

onMounted(loadSummary)
onUnmounted(stopTimer)
</script>

<template>
  <div class="min-h-screen bg-slate-100 p-4 md:p-8">
    <div class="max-w-2xl mx-auto space-y-4">
      <header class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-slate-800">Pomodoro</h1>
        <RouterLink to="/"
          class="bg-slate-800 text-white rounded-lg px-4 py-2 text-sm hover:bg-slate-700">
          ← Πυξίδα
        </RouterLink>
      </header>

      <p v-if="error" class="text-red-600 text-sm">{{ error }}</p>
      <p v-if="earned" class="text-green-600 text-sm font-medium">{{ earned }}</p>

      <section class="bg-white rounded-xl shadow p-6 border-t-4 border-orange-500 text-center space-y-4">
        <p :class="['text-sm font-medium', phase === 'work' ? 'text-orange-600' : 'text-teal-600']">
          {{ phaseLabel }}
        </p>
        <p class="text-6xl font-bold text-slate-800 tabular-nums">{{ display }}</p>

        <div class="flex justify-center gap-3">
          <button @click="toggle"
            class="bg-slate-800 text-white rounded-lg px-6 py-2 hover:bg-slate-700">
            {{ running ? 'Παύση' : 'Έναρξη' }}
          </button>
          <button @click="reset"
            class="border border-slate-300 text-slate-600 rounded-lg px-6 py-2 hover:bg-slate-50">
            Επαναφορά
          </button>
        </div>

        <input v-model="title" :disabled="running && phase === 'work'" type="text" maxlength="100"
          placeholder="Τίτλος (π.χ. Κεφάλαιο 3 Vue)" class="border rounded-lg px-3 py-2 text-sm w-full max-w-sm" />

        <div class="flex flex-wrap justify-center gap-4 text-sm text-slate-600 pt-2">
          <label class="flex items-center gap-2">
            Τύπος
            <select v-model="kind" :disabled="running" class="border rounded-lg px-2 py-1">
              <option value="work">Δουλειά</option>
              <option value="reading">Διάβασμα</option>
            </select>
          </label>
          <label class="flex items-center gap-2">
            Εστίαση (λεπτά)
            <input v-model.number="workMinutes" @change="applySettings" :disabled="running"
              type="number" min="1" max="180" class="border rounded-lg px-2 py-1 w-16" />
          </label>
          <label class="flex items-center gap-2">
            Διάλειμμα (λεπτά)
            <input v-model.number="breakMinutes" @change="applySettings" :disabled="running"
              type="number" min="1" max="60" class="border rounded-lg px-2 py-1 w-16" />
          </label>
        </div>
      </section>

      <section v-if="summary" class="grid grid-cols-2 gap-4">
        <div class="bg-white rounded-xl shadow p-4">
          <p class="text-sm text-slate-500">Σήμερα</p>
          <p class="text-2xl font-bold text-slate-800">{{ summary.today_minutes }} λεπτά</p>
          <p class="text-xs text-slate-400">{{ summary.today_sessions }} sessions</p>
        </div>
        <div class="bg-white rounded-xl shadow p-4">
          <p class="text-sm text-slate-500">Συνολικά</p>
          <p class="text-2xl font-bold text-slate-800">{{ summary.total_minutes }} λεπτά</p>
          <p class="text-xs text-slate-400">{{ summary.total_sessions }} sessions</p>
        </div>
      </section>

      <section v-if="summary" class="bg-white rounded-xl shadow p-4">
        <h2 class="font-bold text-slate-800 mb-2">Ιστορικό</h2>
        <ul v-if="summary.recent.length" class="divide-y">
          <li v-for="s in summary.recent" :key="s.id"
            class="flex justify-between py-2 text-sm text-slate-700">
            <span>
              <span v-if="s.title" class="font-medium">{{ s.title }}</span>
              <span v-else>{{ kindLabel(s.kind) }}</span>
              · {{ s.duration_minutes }} λεπτά
            </span>
            <span class="text-slate-400">{{ formatWhen(s.completed_at) }}</span>
          </li>
        </ul>
        <p v-else class="text-slate-400 text-sm">Κανένα session ακόμα.</p>
      </section>
    </div>
    <BadgeToast />
  </div>
</template>
