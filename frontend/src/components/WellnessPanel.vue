<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'
import { apiErrorMessage } from '../i18n/errors'
import { intlLocale } from '../i18n'
import { formatDate, parseIso } from '../i18n/dates'
import DateField from './DateField.vue'
import StepsRing from './StepsRing.vue'
import StepsChart, { type StepBucket } from './StepsChart.vue'

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
  new_badges?: BadgeInfo[]
}

interface History {
  days: WellnessDay[]
  total: number
  steps_logged: number
  avg_steps: number
  best_steps: number
  sleep_logged: number
  avg_sleep_minutes: number
}

const EARLIEST = '2000-01-01' // no limit on how far back you can log; this is only a sanity floor
const PAGE = 30
const POINTS_STEPS = 10
const POINTS_SLEEP = 10

// Steps and sleep share one data source; the panel can show either part or both.
const props = withDefaults(defineProps<{ parts?: ('steps' | 'sleep')[] }>(), { parts: () => ['steps', 'sleep'] })
const emit = defineEmits<{ saved: [] }>()
const showSteps = computed(() => props.parts.includes('steps'))
const showSleep = computed(() => props.parts.includes('sleep'))

const { t, locale } = useI18n()
const auth = useAuthStore()
const badgesStore = useBadgesStore()

function toIso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const today = new Date()
const maxDate = toIso(today)

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

// ── the interactive steps part: a ring for the chosen day, quick-add buttons and a chart ──
const QUICK_ADD = [500, 1000, 2500, 5000]
const period = ref<'week' | 'month' | 'year'>('week')
const series = ref<{ goal: number; today: number | null; goal_streak: number; buckets: StepBucket[] } | null>(null)
const dayInWindow = computed(() => !!summary.value?.days.some((d) => d.date === date.value))
const savedSteps = computed(() => summary.value?.days.find((d) => d.date === date.value)?.steps ?? 0)

async function loadSeries() {
  if (!showSteps.value) return
  try {
    series.value = (await api.get('/api/wellness/steps/series', { params: { period: period.value } })).data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function bump(n: number) {
  error.value = ''
  message.value = ''
  busy.value = true
  try {
    const { data } = await api.put<LogResult>('/api/wellness/steps', { steps: Math.min(100000, savedSteps.value + n), log_date: date.value })
    await afterSave(data)
  } catch (e) {
    error.value = apiErrorMessage(e)
  } finally {
    busy.value = false
  }
}

function setPeriod(p: 'week' | 'month' | 'year') {
  period.value = p
  loadSeries()
}

const stepGoal = computed(() => summary.value?.step_goal ?? 8000)
const sleepGoal = computed(() => summary.value?.sleep_goal_minutes ?? 420)

// The complete history, newest first, loaded a page at a time
const histKind = computed(() => (showSteps.value && showSleep.value ? undefined : showSteps.value ? 'steps' : 'sleep'))
const history = ref<WellnessDay[]>([])
const stats = ref<History | null>(null)

async function loadHistory(reset: boolean) {
  try {
    const { data } = await api.get<History>('/api/wellness/history', {
      params: { limit: PAGE, offset: reset ? 0 : history.value.length, kind: histKind.value },
    })
    history.value = reset ? data.days : [...history.value, ...data.days]
    stats.value = data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function removeDay(d: WellnessDay) {
  if (!confirm(t('wellness.confirmDelete', { date: formatDate(d.date) }))) return
  error.value = ''
  try {
    if (showSteps.value && d.steps != null) await api.delete(`/api/wellness/steps/${d.date}`)
    if (showSleep.value && d.sleep_minutes != null) await api.delete(`/api/wellness/sleep/${d.date}`)
    await Promise.all([load(), loadHistory(true), loadSeries()])
    emit('saved')
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

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
  await badgesStore.announce(result.new_badges)
  const keepDate = date.value
  await Promise.all([load(), loadHistory(true), loadSeries()])
  date.value = keepDate
  fillForm()
  emit('saved')
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
onMounted(() => {
  load()
  loadHistory(true)
  loadSeries()
})
</script>

<template>
  <div class="space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
    <p v-if="message" role="status" class="text-ok text-sm font-medium">{{ message }}</p>

    <section v-if="summary" :class="['grid gap-4', showSteps && showSleep ? 'grid-cols-2' : 'grid-cols-1']">
      <div v-if="showSteps" class="bg-surface rounded-xl shadow p-4 border-t-4 border-teal-500">
        <p class="text-sm text-slate-500">{{ t('wellness.avgSteps') }}</p>
        <p class="text-2xl font-bold text-slate-800">{{ summary.avg_steps_7d.toLocaleString(loc) }}</p>
        <p class="text-xs text-slate-500">{{ t('wellness.goalSteps', { n: stepGoal.toLocaleString(loc) }) }}</p>
      </div>
      <div v-if="showSleep" class="bg-surface rounded-xl shadow p-4 border-t-4 border-indigo-500">
        <p class="text-sm text-slate-500">{{ t('wellness.avgSleep') }}</p>
        <p class="text-2xl font-bold text-slate-800">{{ formatDuration(summary.avg_sleep_minutes_7d) }}</p>
        <p class="text-xs text-slate-500">{{ t('wellness.goalSleep', { n: formatDuration(sleepGoal) }) }}</p>
      </div>
    </section>

    <section v-if="showSteps && summary && dayInWindow" class="bg-surface rounded-xl shadow p-4 space-y-3 border-t-4 border-teal-500">
      <StepsRing :steps="savedSteps" :goal="stepGoal" :streak="series?.goal_streak ?? 0" />
      <div class="flex flex-wrap justify-center gap-2" role="group" :aria-label="t('steps.quickAdd')">
        <button v-for="n in QUICK_ADD" :key="n" type="button" :disabled="busy" @click="bump(n)"
          class="rounded-full border border-slate-400 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 active:scale-95 transition disabled:opacity-50">
          +{{ n.toLocaleString(loc) }}
        </button>
      </div>
      <p class="text-xs text-slate-500 text-center">{{ t('steps.quickHint', { date: formatDate(date) }) }}</p>
    </section>

    <section v-if="showSteps && series" class="bg-surface rounded-xl shadow p-4">
      <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
        <h2 class="font-bold text-slate-800">{{ t('steps.chart') }}</h2>
        <div class="flex gap-1" role="radiogroup" :aria-label="t('steps.chart')">
          <button v-for="p in (['week', 'month', 'year'] as const)" :key="p" type="button" role="radio" :aria-checked="period === p" @click="setPeriod(p)"
            :class="['rounded-lg px-3 py-1 text-xs', period === p ? 'bg-primary text-on-primary' : 'border border-slate-400 text-slate-600 hover:bg-slate-50']">
            {{ t(`steps.periods.${p}`) }}
          </button>
        </div>
      </div>
      <StepsChart :buckets="series.buckets" :goal="series.goal" :period="period" />
    </section>

    <section class="bg-surface rounded-xl shadow p-4 space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="font-bold text-slate-800">{{ t('wellness.logTitle') }}</h2>
        <div class="flex items-center gap-2 text-sm text-slate-600">
          <span>{{ t('wellness.date') }}</span>
          <DateField v-model="date" :min="EARLIEST" :max="maxDate" :label="t('wellness.date')" required />
        </div>
      </div>

      <form v-if="showSteps" @submit.prevent="saveSteps" class="flex flex-wrap items-end gap-3">
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

      <form v-if="showSleep" @submit.prevent="saveSleep" class="space-y-3">
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
        {{ showSteps && showSleep ? t('wellness.hint', { steps: POINTS_STEPS, sleep: POINTS_SLEEP })
          : showSteps ? t('wellness.hintSteps', { n: POINTS_STEPS }) : t('wellness.hintSleep', { n: POINTS_SLEEP }) }}
      </p>
    </section>

    <section v-if="stats" class="bg-surface rounded-xl shadow p-4">
      <h2 class="font-bold text-slate-800 mb-1">{{ t('wellness.history') }}</h2>
      <p class="text-xs text-slate-500 mb-3">
        <template v-if="showSteps">{{ t('wellness.allTimeSteps', { days: stats.steps_logged, avg: stats.avg_steps.toLocaleString(loc), best: stats.best_steps.toLocaleString(loc) }) }}</template>
        <template v-if="showSteps && showSleep"><br /></template>
        <template v-if="showSleep">{{ t('wellness.allTimeSleep', { days: stats.sleep_logged, avg: formatDuration(stats.avg_sleep_minutes) }) }}</template>
      </p>
      <ul v-if="history.length" class="divide-y">
        <li v-for="d in history" :key="d.date" class="py-2 text-sm">
          <div class="flex items-center justify-between text-slate-700 mb-1">
            <span class="font-medium">{{ formatDay(d.date) }}</span>
            <span class="text-slate-500 flex items-center gap-1">
              <template v-if="(showSteps && d.steps != null) || (showSleep && d.sleep_minutes != null)">
                <span v-if="showSteps && d.steps != null">👟 {{ d.steps.toLocaleString(loc) }}</span>
                <span v-if="showSleep && d.sleep_minutes != null" :class="showSteps ? 'ml-3' : ''">😴 {{ formatDuration(d.sleep_minutes) }}<span v-if="d.sleep_quality" class="text-xs"> · {{ d.sleep_quality }}/5</span></span>
              </template>
              <span v-else class="text-slate-500">{{ t('wellness.noData') }}</span>
              <button @click="removeDay(d)" :aria-label="t('home.remove')" :title="t('home.remove')"
                class="w-6 h-6 inline-flex items-center justify-center rounded text-slate-500 hover:text-danger hover:bg-slate-100">✕</button>
            </span>
          </div>
          <div :class="['grid gap-2', showSteps && showSleep ? 'grid-cols-2' : 'grid-cols-1']">
            <div v-if="showSteps" class="h-1.5 rounded bg-slate-100 overflow-hidden">
              <div class="h-full bg-teal-500" :style="{ width: stepsPercent(d.steps) + '%' }" />
            </div>
            <div v-if="showSleep" class="h-1.5 rounded bg-slate-100 overflow-hidden">
              <div class="h-full bg-indigo-500" :style="{ width: sleepPercent(d.sleep_minutes) + '%' }" />
            </div>
          </div>
        </li>
      </ul>
      <p v-else class="text-sm text-slate-500">{{ t('wellness.noHistory') }}</p>
      <button v-if="history.length < stats.total" @click="loadHistory(false)"
        class="mt-3 w-full border border-slate-400 text-slate-600 rounded-lg px-3 py-1.5 text-sm hover:bg-slate-50">
        {{ t('wellness.showMore', { n: stats.total - history.length }) }}
      </button>
    </section>
  </div>
</template>
