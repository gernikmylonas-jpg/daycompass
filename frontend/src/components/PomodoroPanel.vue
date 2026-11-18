<script setup lang="ts">
import FocusSounds from './FocusSounds.vue'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'
import { apiErrorMessage } from '../i18n/errors'
import { formatDateTime } from '../i18n/dates'

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

const emit = defineEmits<{ summary: [todaySessions: number] }>()

const { t } = useI18n()
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
const projects = ref<{ title: string; minutes: number; sessions: number }[]>([])
const error = ref('')

let endAt = 0
let timer: number | undefined

const display = computed(() => {
  const m = Math.floor(remaining.value / 60)
  const s = remaining.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const phaseLabel = computed(() => (phase.value === 'work' ? t('pomodoro.focus') : t('pomodoro.break')))

function totalSeconds() {
  return (phase.value === 'work' ? workMinutes.value : breakMinutes.value) * 60
}

function showError(e: unknown) {
  error.value = apiErrorMessage(e)
}

async function loadSummary() {
  try {
    const { data } = await api.get<Summary>('/api/pomodoro/summary')
    summary.value = data
    emit('summary', data.today_sessions)
    projects.value = (await api.get('/api/pomodoro/projects')).data
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
      earned.value = t('pomodoro.earned', { n: 5 })
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
  return k === 'work' ? t('pomodoro.kindWork') : t('pomodoro.kindReading')
}

function formatWhen(iso: string) {
  return formatDateTime(new Date(iso + 'Z'))
}

onMounted(loadSummary)
onUnmounted(stopTimer)
</script>

<template>
  <div class="space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
    <p v-if="earned" role="status" class="text-ok text-sm font-medium">{{ earned }}</p>

    <section class="bg-surface rounded-xl shadow p-6 border-t-4 border-orange-500 text-center space-y-4">
      <p :class="['text-sm font-medium', phase === 'work' ? 'text-phase-focus' : 'text-phase-break']">
        {{ phaseLabel }}
      </p>
      <p class="text-6xl font-bold text-slate-800 tabular-nums">{{ display }}</p>

      <div class="flex justify-center gap-3">
        <button @click="toggle"
          class="bg-primary text-on-primary rounded-lg px-6 py-2 hover:bg-primary-hover">
          {{ running ? t('pomodoro.pause') : t('pomodoro.start') }}
        </button>
        <button @click="reset"
          class="border border-slate-400 text-slate-600 rounded-lg px-6 py-2 hover:bg-slate-50">
          {{ t('pomodoro.reset') }}
        </button>
      </div>

      <input v-model="title" :disabled="running && phase === 'work'" type="text" maxlength="100"
        :placeholder="t('pomodoro.titlePlaceholder')" :aria-label="t('pomodoro.titlePlaceholder')" class="border rounded-lg px-3 py-2 text-sm w-full max-w-sm" list="focus-projects" />
      <datalist id="focus-projects"><option v-for="p in projects" :key="p.title" :value="p.title" /></datalist>

      <div class="flex flex-wrap justify-center gap-4 text-sm text-slate-600 pt-2">
        <label class="flex items-center gap-2">
          {{ t('pomodoro.kind') }}
          <select v-model="kind" :disabled="running" class="border rounded-lg px-2 py-1">
            <option value="work">{{ t('pomodoro.kindWork') }}</option>
            <option value="reading">{{ t('pomodoro.kindReading') }}</option>
          </select>
        </label>
        <label class="flex items-center gap-2">
          {{ t('pomodoro.focusMinutes') }}
          <input v-model.number="workMinutes" @change="applySettings" :disabled="running"
            type="number" min="1" max="180" class="border rounded-lg px-2 py-1 w-16" />
        </label>
        <label class="flex items-center gap-2">
          {{ t('pomodoro.breakMinutes') }}
          <input v-model.number="breakMinutes" @change="applySettings" :disabled="running"
            type="number" min="1" max="60" class="border rounded-lg px-2 py-1 w-16" />
        </label>
      </div>
    </section>

    <section v-if="summary" class="grid grid-cols-2 gap-4">
      <div class="bg-surface rounded-xl shadow p-4">
        <p class="text-sm text-slate-500">{{ t('pomodoro.today') }}</p>
        <p class="text-2xl font-bold text-slate-800">{{ t('pomodoro.minutes', { n: summary.today_minutes }) }}</p>
        <p class="text-xs text-slate-500">{{ t('pomodoro.sessions', summary.today_sessions) }}</p>
      </div>
      <div class="bg-surface rounded-xl shadow p-4">
        <p class="text-sm text-slate-500">{{ t('pomodoro.total') }}</p>
        <p class="text-2xl font-bold text-slate-800">{{ t('pomodoro.minutes', { n: summary.total_minutes }) }}</p>
        <p class="text-xs text-slate-500">{{ t('pomodoro.sessions', summary.total_sessions) }}</p>
      </div>
    </section>

    <section v-if="summary" class="bg-surface rounded-xl shadow p-4">
      <h2 class="font-bold text-slate-800 mb-2">{{ t('pomodoro.history') }}</h2>
      <ul v-if="summary.recent.length" class="divide-y">
        <li v-for="s in summary.recent" :key="s.id"
          class="flex justify-between py-2 text-sm text-slate-700">
          <span>
            <span v-if="s.title" class="font-medium">{{ s.title }}</span>
            <span v-else>{{ kindLabel(s.kind) }}</span>
            · {{ t('pomodoro.minutes', { n: s.duration_minutes }) }}
          </span>
          <span class="text-slate-500">{{ formatWhen(s.completed_at) }}</span>
        </li>
      </ul>
      <p v-else class="text-slate-500 text-sm">{{ t('pomodoro.noSessions') }}</p>
    </section>
    <section v-if="projects.length" class="bg-surface rounded-xl shadow p-4 space-y-2">
      <h2 class="font-bold text-slate-800">{{ t('pomodoro.byProject') }}</h2>
      <div v-for="p in projects.slice(0, 8)" :key="p.title" class="text-sm">
        <div class="flex justify-between text-slate-700"><span class="break-words">{{ p.title }}</span><span class="tabular-nums shrink-0">{{ t('wellness.duration', { h: Math.floor(p.minutes / 60), m: p.minutes % 60 }) }} · {{ t('pomodoro.sessions', p.sessions) }}</span></div>
        <div class="h-1.5 rounded bg-slate-100 overflow-hidden"><div class="h-full bg-orange-500" :style="{ width: (p.minutes / projects[0].minutes) * 100 + '%' }"></div></div>
      </div>
    </section>
    <FocusSounds />
  </div>
</template>
