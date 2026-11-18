<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { intlLocale } from '../i18n'

// Your year in review: totals from your own records for one calendar year. It only exists when you open it.
interface Year {
  year: number; checkins: number; active_days: number; best_streak: number; checkins_by_month: number[]; best_month: number | null
  top_habits: { name: string; count: number }[]; steps_total: number; steps_days: number; steps_avg: number | null; step_goal_days: number
  sleep_nights: number; sleep_avg_minutes: number | null; focus_minutes: number; meditation_minutes: number
  journal_entries: number; mood_avg: number | null; mood_logs: number; weight_change_kg: number | null; badges_earned: number
}
const { t, locale } = useI18n()
const now = new Date().getFullYear()
const year = ref(now)
const years = Array.from({ length: now - 1900 + 1 }, (_, i) => now - i)
const data = ref<Year | null>(null)
const error = ref('')
const loc = computed(() => intlLocale(locale.value))
const num = (n: number) => n.toLocaleString(loc.value)
const hours = (m: number) => t('wellness.duration', { h: Math.floor(m / 60), m: m % 60 })
const monthNames = computed(() => {
  const f = new Intl.DateTimeFormat(loc.value, { month: 'short' })
  return Array.from({ length: 12 }, (_, i) => f.format(new Date(2024, i, 1)))
})
const fullMonth = (m: number) => new Intl.DateTimeFormat(loc.value, { month: 'long' }).format(new Date(2024, m - 1, 1))
const maxMonth = computed(() => Math.max(1, ...(data.value?.checkins_by_month ?? [0])))
const km = computed(() => (data.value ? Math.round(data.value.steps_total * 0.00075) : 0)) // about 0.75 m per step

async function load() {
  error.value = ''
  try {
    data.value = (await api.get<Year>('/api/insights/year', { params: { year: year.value } })).data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
watch(year, load)
onMounted(load)
</script>

<template>
  <div class="min-h-[calc(100vh-3rem)] bg-page p-4 md:p-8">
    <div class="max-w-3xl mx-auto space-y-4">
      <header class="flex flex-wrap items-center justify-between gap-2">
        <h1 class="text-2xl font-bold text-slate-800">{{ t('review.title') }}</h1>
        <div class="flex items-center gap-2">
          <select v-model.number="year" :aria-label="t('calendar.year')" class="border rounded-lg px-2 py-1.5 text-sm">
            <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
          </select>
          <RouterLink to="/progress" class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover">← {{ t('progress.title') }}</RouterLink>
        </div>
      </header>
      <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>

      <template v-if="data">
        <section v-if="data.checkins === 0 && data.steps_days === 0 && data.mood_logs === 0 && data.sleep_nights === 0" class="bg-surface rounded-xl shadow p-6 text-center text-slate-600">
          {{ t('review.empty', { year: data.year }) }}
        </section>
        <template v-else>
          <section class="bg-surface rounded-xl shadow p-6 text-center border-t-4 border-amber-500">
            <p class="text-sm uppercase tracking-wider text-slate-500">{{ t('review.headline', { year: data.year }) }}</p>
            <p class="text-6xl font-bold text-slate-800 tabular-nums" style="font-family: var(--font-display)">{{ num(data.checkins) }}</p>
            <p class="text-slate-600">{{ t('review.checkins', { days: data.active_days }) }}</p>
            <p v-if="data.best_streak" class="text-sm text-streak mt-1">🔥 {{ t('review.bestStreak', data.best_streak) }}</p>
          </section>

          <section class="bg-surface rounded-xl shadow p-4">
            <h2 class="font-bold text-slate-800 mb-2">{{ t('review.byMonth') }}<span v-if="data.best_month" class="text-sm font-normal text-slate-500"> · {{ t('review.bestMonth', { month: fullMonth(data.best_month) }) }}</span></h2>
            <div class="flex items-end gap-1.5 h-28" role="img" :aria-label="t('review.byMonth')">
              <div v-for="(c, i) in data.checkins_by_month" :key="i" class="flex-1 flex flex-col items-center justify-end h-full gap-1">
                <span class="text-[0.65rem] text-slate-500 tabular-nums">{{ c || '' }}</span>
                <div class="w-full rounded-t" :class="data.best_month === i + 1 ? 'bg-teal-500' : 'bg-slate-300'" :style="{ height: (c / maxMonth) * 100 + '%', minHeight: c ? '3px' : '2px' }"></div>
                <span class="text-[0.65rem] text-slate-600">{{ monthNames[i] }}</span>
              </div>
            </div>
          </section>

          <section v-if="data.top_habits.length" class="bg-surface rounded-xl shadow p-4">
            <h2 class="font-bold text-slate-800 mb-2">{{ t('review.topHabits') }}</h2>
            <ol class="text-sm text-slate-700 space-y-1">
              <li v-for="(h, i) in data.top_habits" :key="h.name" class="flex justify-between"><span>{{ ['🥇', '🥈', '🥉'][i] }} {{ h.name }}</span><span class="tabular-nums text-slate-600">{{ num(h.count) }}</span></li>
            </ol>
          </section>

          <section class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-center">
            <div v-if="data.steps_days" class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ num(data.steps_total) }}</p><p class="text-xs text-slate-500">{{ t('review.steps', { km: num(km) }) }}</p><p class="text-xs text-slate-500">{{ t('review.goalDays', { n: data.step_goal_days }) }}</p></div>
            <div v-if="data.sleep_nights && data.sleep_avg_minutes" class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800">{{ hours(data.sleep_avg_minutes) }}</p><p class="text-xs text-slate-500">{{ t('review.sleep', { n: data.sleep_nights }) }}</p></div>
            <div v-if="data.mood_avg !== null" class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ data.mood_avg }}</p><p class="text-xs text-slate-500">{{ t('review.mood', { n: data.mood_logs }) }}</p></div>
            <div v-if="data.focus_minutes" class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800">{{ hours(data.focus_minutes) }}</p><p class="text-xs text-slate-500">{{ t('review.focus') }}</p></div>
            <div v-if="data.meditation_minutes" class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800">{{ hours(data.meditation_minutes) }}</p><p class="text-xs text-slate-500">{{ t('review.meditation') }}</p></div>
            <div v-if="data.journal_entries" class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ data.journal_entries }}</p><p class="text-xs text-slate-500">{{ t('review.journal') }}</p></div>
            <div v-if="data.weight_change_kg !== null" class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ data.weight_change_kg > 0 ? '+' : '' }}{{ data.weight_change_kg }} kg</p><p class="text-xs text-slate-500">{{ t('review.weight') }}</p></div>
            <div v-if="data.badges_earned" class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ data.badges_earned }}</p><p class="text-xs text-slate-500">{{ t('review.badges') }}</p></div>
          </section>
        </template>
      </template>
    </div>
  </div>
</template>
