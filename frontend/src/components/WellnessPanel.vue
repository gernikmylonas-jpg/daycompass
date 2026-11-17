<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { apiErrorMessage } from '../i18n/errors'
import { intlLocale } from '../i18n'
import { formatDate, parseIso } from '../i18n/dates'
import DateField from './DateField.vue'

interface WellnessDay {
  date: string
  steps: number | null
  sleep_minutes: number | null
  sleep_quality: number | null
}

interface Summary {
  step_goal: number
  sleep_goal_minutes: number
  avg_steps_7d: number
  avg_sleep_minutes_7d: number
  days: WellnessDay[]
}

interface LogResult {
  goal_reached: boolean
  points_awarded: number
}

const MAX_BACKFILL_DAYS = 30
const POINTS_STEPS = 10
const POINTS_SLEEP = 10

const { t, locale } = useI18n()
const auth = useAuthStore()

function toIso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const today = new Date()
const maxDate = toIso(today)
const minDate = toIso(new Date(today.getFullYear(), today.getMonth(), today.getDate() - MAX_BACKFILL_DAYS))

const summary = ref<Summary | null>(null)
const date = ref(maxDate)
const steps = ref<number | null>(null)
const sleepHours = ref<number | null>(null)
const sleepMinutes = ref<number | null>(null)
const quality = ref<number | ''>('')
const error = ref('')
const message = ref('')
const busy = ref(false)

const loc = computed(() => intlLocale(locale.value))

function formatDuration(totalMinutes: number) {
  return t('wellness.duration', { h: Math.floor(totalMinutes / 60), m: totalMinutes % 60 })
}

function formatDay(iso: string) {
  const weekday = new Intl.DateTimeFormat(loc.value, { weekday: 'short' }).format(parseIso(iso))
  return `${weekday} ${formatDate(iso)}`
}

const stepGoal = computed(() => summary.value?.step_goal ?? 8000)
const sleepGoal = computed(() => summary.value?.sleep_goal_minutes ?? 420)

// newest first for the history list
const history = computed(() => [...(summary.value?.days ?? [])].reverse())

function fillForm() {
  const day = summary.value?.days.find((d) => d.date === date.value)
  steps.value = day?.steps ?? null
  if (day?.sleep_minutes != null) {
    sleepHours.value = Math.floor(day.sleep_minutes / 60)
    sleepMinutes.value = day.sleep_minutes % 60
  } else {
    sleepHours.value = null
    sleepMinutes.value = null
  }
  quality.value = day?.sleep_quality ?? ''
}

async function load() {
  try {
    const { data } = await api.get<Summary>('/api/wellness/summary')
    summary.value = data
    fillForm()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function afterSave(result: LogResult) {
  message.value = result.points_awarded > 0
    ? t('wellness.pointsEarned', { n: result.points_awarded })
    : t('wellness.saved')
  if (result.points_awarded > 0) await auth.refreshUser().catch(() => {})
  const keepDate = date.value
  await load()
  date.value = keepDate
  fillForm()
}

async function saveSteps() {
  error.value = ''
  message.value = ''
  if (steps.value == null || !date.value) return
  busy.value = true
  try {
    const { data } = await api.put<LogResult>('/api/wellness/steps', {
      steps: Math.round(steps.value),
      log_date: date.value,
    })
    await afterSave(data)
  } catch (e) {
    error.value = apiErrorMessage(e)
  } finally {
    busy.value = false
  }
}

async function saveSleep() {
  error.value = ''
  message.value = ''
  const minutes = Math.round((sleepHours.value ?? 0) * 60 + (sleepMinutes.value ?? 0))
  if ((sleepHours.value == null && sleepMinutes.value == null) || !date.value) return
  busy.value = true
  try {
    const { data } = await api.put<LogResult>('/api/wellness/sleep', {
      minutes,
      quality: quality.value === '' ? null : Number(quality.value),
      log_date: date.value,
    })
    await afterSave(data)
  } catch (e) {
    error.value = apiErrorMessage(e)
  } finally {
    busy.value = false
  }
}

function stepsPercent(value: number | null) {
  return value == null ? 0 : Math.min(100, Math.round((value / stepGoal.value) * 100))
}

function sleepPercent(value: number | null) {
  return value == null ? 0 : Math.min(100, Math.round((value / sleepGoal.value) * 100))
}

watch(date, () => {
  if (!date.value) return
  message.value = ''
  fillForm()
})
onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
    <p v-if="message" role="status" class="text-ok text-sm font-medium">{{ message }}</p>

    <section v-if="summary" class="grid grid-cols-2 gap-4">
      <div class="bg-surface rounded-xl shadow p-4 border-t-4 border-teal-500">
        <p class="text-sm text-slate-500">{{ t('wellness.avgSteps') }}</p>
        <p class="text-2xl font-bold text-slate-800">{{ summary.avg_steps_7d.toLocaleString(loc) }}</p>
        <p class="text-xs text-slate-500">{{ t('wellness.goalSteps', { n: stepGoal.toLocaleString(loc) }) }}</p>
      </div>
      <div class="bg-surface rounded-xl shadow p-4 border-t-4 border-purple-500">
        <p class="text-sm text-slate-500">{{ t('wellness.avgSleep') }}</p>
        <p class="text-2xl font-bold text-slate-800">{{ formatDuration(summary.avg_sleep_minutes_7d) }}</p>
        <p class="text-xs text-slate-500">{{ t('wellness.goalSleep', { n: formatDuration(sleepGoal) }) }}</p>
      </div>
    </section>

    <section class="bg-surface rounded-xl shadow p-4 space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="font-bold text-slate-800">{{ t('wellness.logTitle') }}</h2>
        <div class="flex items-center gap-2 text-sm text-slate-600">
          <span>{{ t('wellness.date') }}</span>
          <DateField v-model="date" :min="minDate" :max="maxDate" :label="t('wellness.date')" required />
        </div>
      </div>

      <form @submit.prevent="saveSteps" class="flex flex-wrap items-end gap-3">
        <label class="text-sm text-slate-600 flex-1 min-w-40">
          {{ t('wellness.steps') }}
          <input v-model.number="steps" type="number" min="0" max="100000" step="1" required
            :placeholder="t('wellness.stepsPlaceholder')" :aria-label="t('wellness.stepsPlaceholder')"
            class="mt-1 border rounded-lg px-3 py-2 w-full" />
        </label>
        <button type="submit" :disabled="busy"
          class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover disabled:opacity-50">
          {{ t('wellness.saveSteps') }}
        </button>
      </form>

      <form @submit.prevent="saveSleep" class="space-y-3">
        <div class="flex flex-wrap items-end gap-3">
          <label class="text-sm text-slate-600">
            {{ t('wellness.sleep') }} ({{ t('wellness.hours') }})
            <input v-model.number="sleepHours" type="number" min="0" max="24" step="1"
              class="mt-1 border rounded-lg px-3 py-2 w-24 block" />
          </label>
          <label class="text-sm text-slate-600">
            {{ t('wellness.minutes') }}
            <input v-model.number="sleepMinutes" type="number" min="0" max="59" step="1"
              class="mt-1 border rounded-lg px-3 py-2 w-24 block" />
          </label>
          <label class="text-sm text-slate-600 flex-1 min-w-40">
            {{ t('wellness.quality') }}
            <select v-model="quality" class="mt-1 border rounded-lg px-3 py-2 w-full block">
              <option value="">{{ t('wellness.qualityNone') }}</option>
              <option v-for="q in 5" :key="q" :value="q">{{ t(`wellness.q${q}`) }}</option>
            </select>
          </label>
          <button type="submit" :disabled="busy"
            class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover disabled:opacity-50">
            {{ t('wellness.saveSleep') }}
          </button>
        </div>
      </form>

      <p class="text-xs text-slate-500">
        {{ t('wellness.hint', { steps: POINTS_STEPS, sleep: POINTS_SLEEP }) }}
      </p>
    </section>

    <section v-if="summary" class="bg-surface rounded-xl shadow p-4">
      <h2 class="font-bold text-slate-800 mb-2">{{ t('wellness.last14') }}</h2>
      <ul class="divide-y">
        <li v-for="d in history" :key="d.date" class="py-2 text-sm">
          <div class="flex items-center justify-between text-slate-700 mb-1">
            <span class="font-medium">{{ formatDay(d.date) }}</span>
            <span class="text-slate-500">
              <template v-if="d.steps != null || d.sleep_minutes != null">
                <span v-if="d.steps != null">👟 {{ d.steps.toLocaleString(loc) }}</span>
                <span v-if="d.sleep_minutes != null" class="ml-3">😴 {{ formatDuration(d.sleep_minutes) }}</span>
              </template>
              <span v-else class="text-slate-500">{{ t('wellness.noData') }}</span>
            </span>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div class="h-1.5 rounded bg-slate-100 overflow-hidden">
              <div class="h-full bg-teal-500" :style="{ width: stepsPercent(d.steps) + '%' }" />
            </div>
            <div class="h-1.5 rounded bg-slate-100 overflow-hidden">
              <div class="h-full bg-purple-500" :style="{ width: sleepPercent(d.sleep_minutes) + '%' }" />
            </div>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>
