<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { formatDate } from '../i18n/dates'
import { intlLocale } from '../i18n'
import RadarChart, { type RadarAxis } from '../components/RadarChart.vue'

// The compass report: how balanced the last week / month was, and what your own data suggests.
interface Correlation { key: string; n_with: number; n_without: number; avg_with: number; avg_without: number }
interface Report {
  period: string; start: string; end: string; axes: Record<string, number | null>
  checkins: number; active_days: number; days: number; points_earned: number
  pomodoro_minutes: number; meditation_minutes: number
  avg_steps: number | null; avg_sleep_minutes: number | null; avg_mood: number | null; prev_avg_mood: number | null
  journal_entries: number; weekdays: number[]; correlations: Correlation[]
}

// clockwise from north, like the compass
const AXIS_ORDER = ['body', 'sleep', 'schedule', 'movement', 'mind', 'focus', 'work', 'calm']
const MIN_DIFFERENCE = 0.3 // mood points; smaller gaps are reported as "no clear difference"

const { t, locale } = useI18n()
const period = ref<'week' | 'month'>('week')
const report = ref<Report | null>(null)
const error = ref('')

async function load() {
  error.value = ''
  try {
    report.value = (await api.get<Report>('/api/insights/report', { params: { period: period.value } })).data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

const axes = computed<RadarAxis[]>(() =>
  AXIS_ORDER.map((key) => ({ key, label: t(`report.axes.${key}`), value: report.value?.axes[key] ?? null })),
)

const weakest = computed(() => {
  const known = axes.value.filter((a) => a.value !== null)
  return known.length >= 3 ? known.reduce((low, a) => ((a.value as number) < (low.value as number) ? a : low)) : null
})
const strongest = computed(() => {
  const known = axes.value.filter((a) => a.value !== null)
  return known.length >= 3 ? known.reduce((hi, a) => ((a.value as number) > (hi.value as number) ? a : hi)) : null
})

const weekdayNames = computed(() => {
  const f = new Intl.DateTimeFormat(intlLocale(locale.value), { weekday: 'short' })
  return Array.from({ length: 7 }, (_, i) => f.format(new Date(2024, 0, 1 + i)))
})
const maxWeekday = computed(() => Math.max(1, ...(report.value?.weekdays ?? [0])))

const hours = (minutes: number) => t('wellness.duration', { h: Math.floor(minutes / 60), m: minutes % 60 })

const insights = computed(() =>
  (report.value?.correlations ?? []).map((c) => {
    const diff = c.avg_with - c.avg_without
    return { ...c, diff, clear: Math.abs(diff) >= MIN_DIFFERENCE }
  }),
)

watch(period, load)
onMounted(load)
</script>

<template>
  <div class="min-h-[calc(100vh-3rem)] bg-page p-4 md:p-8">
    <div class="max-w-3xl mx-auto space-y-4">
      <header class="flex flex-wrap items-center justify-between gap-2">
        <h1 class="text-2xl font-bold text-slate-800">{{ t('report.title') }}</h1>
        <RouterLink to="/progress" class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover">← {{ t('progress.title') }}</RouterLink>
      </header>

      <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>

      <div class="flex gap-2" role="radiogroup" :aria-label="t('report.title')">
        <button v-for="p in (['week', 'month'] as const)" :key="p" role="radio" :aria-checked="period === p" @click="period = p"
          :class="['rounded-lg px-4 py-1.5 text-sm', period === p ? 'bg-primary text-on-primary' : 'border border-slate-400 text-slate-600 hover:bg-slate-50']">
          {{ t(`report.${p}`) }}
        </button>
        <span v-if="report" class="ml-auto self-center text-xs text-slate-500">{{ formatDate(report.start) }} – {{ formatDate(report.end) }}</span>
      </div>

      <template v-if="report">
        <section class="bg-surface rounded-xl shadow p-4">
          <h2 class="font-bold text-slate-800 mb-1">{{ t('report.balance') }}</h2>
          <RadarChart :axes="axes" :title="t('report.balance')" :no-data="t('report.noData')" />
          <p v-if="strongest && weakest && strongest.key !== weakest.key" class="text-sm text-slate-600 text-center mt-2">
            {{ t('report.strongest', { axis: strongest.label }) }} · {{ t('report.weakest', { axis: weakest.label }) }}
          </p>
        </section>

        <section class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ report.checkins }}</p><p class="text-xs text-slate-500">{{ t('report.checkins') }}</p></div>
          <div class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ report.active_days }}/{{ report.days }}</p><p class="text-xs text-slate-500">{{ t('report.activeDays') }}</p></div>
          <div class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ report.points_earned }}</p><p class="text-xs text-slate-500">{{ t('report.pointsEarned') }}</p></div>
          <div class="bg-surface rounded-xl shadow p-3">
            <p class="text-xl font-bold text-slate-800 tabular-nums">{{ report.avg_mood ?? '—' }}</p>
            <p class="text-xs text-slate-500">{{ t('report.avgMood') }}</p>
            <p v-if="report.avg_mood !== null && report.prev_avg_mood !== null && report.avg_mood !== report.prev_avg_mood" class="text-xs" :class="report.avg_mood > report.prev_avg_mood ? 'text-ok' : 'text-danger'">
              {{ report.avg_mood > report.prev_avg_mood ? '▲' : '▼' }} {{ t(report.avg_mood > report.prev_avg_mood ? 'report.moodUp' : 'report.moodDown', { n: report.prev_avg_mood }) }}
            </p>
          </div>
          <div class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ report.avg_steps?.toLocaleString() ?? '—' }}</p><p class="text-xs text-slate-500">{{ t('report.avgSteps') }}</p></div>
          <div class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ report.avg_sleep_minutes !== null ? hours(report.avg_sleep_minutes) : '—' }}</p><p class="text-xs text-slate-500">{{ t('report.avgSleep') }}</p></div>
          <div class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ report.pomodoro_minutes }}</p><p class="text-xs text-slate-500">{{ t('report.focusMinutes') }}</p></div>
          <div class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ report.meditation_minutes }}</p><p class="text-xs text-slate-500">{{ t('report.meditationMinutes') }}</p></div>
        </section>

        <section class="bg-surface rounded-xl shadow p-4">
          <h2 class="font-bold text-slate-800 mb-3">{{ t('report.weekdays') }}</h2>
          <div class="flex items-end gap-2 h-28" role="img" :aria-label="t('report.weekdays') + ': ' + weekdayNames.map((n, i) => `${n} ${report!.weekdays[i]}`).join(', ')">
            <div v-for="(count, i) in report.weekdays" :key="i" class="flex-1 flex flex-col items-center justify-end h-full gap-1">
              <span class="text-xs text-slate-500 tabular-nums">{{ count || '' }}</span>
              <div class="w-full rounded-t" :class="count === maxWeekday && count > 0 ? 'bg-teal-500' : 'bg-slate-300'" :style="{ height: (count / maxWeekday) * 100 + '%', minHeight: count ? '4px' : '2px' }"></div>
              <span class="text-xs text-slate-600">{{ weekdayNames[i] }}</span>
            </div>
          </div>
        </section>

        <section class="bg-surface rounded-xl shadow p-4 space-y-2">
          <h2 class="font-bold text-slate-800">{{ t('report.insights') }}</h2>
          <ul v-if="insights.length" class="space-y-2 text-sm text-slate-700">
            <li v-for="i in insights" :key="i.key" class="rounded-lg border border-slate-200 p-3">
              <template v-if="i.clear">
                {{ t(`report.insight.${i.key}`, { a: i.avg_with.toFixed(1), b: i.avg_without.toFixed(1) }) }}
                <span :class="i.diff > 0 ? 'text-ok' : 'text-danger'" class="font-semibold">({{ i.diff > 0 ? '+' : '' }}{{ i.diff.toFixed(1) }})</span>
              </template>
              <template v-else>{{ t(`report.noDifference.${i.key}`) }}</template>
              <p class="text-xs text-slate-500 mt-1">{{ t('report.samples', { a: i.n_with, b: i.n_without }) }}</p>
            </li>
          </ul>
          <p v-else class="text-sm text-slate-500">{{ t('report.noInsights') }}</p>
          <p class="text-xs text-slate-500">{{ t('report.note') }}</p>
        </section>
      </template>
    </div>
  </div>
</template>
