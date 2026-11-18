<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { formatDate, toIso } from '../i18n/dates'
import { intlLocale } from '../i18n'

// Period tracking. Private and entirely optional: nothing is stored until you tap a day, and predictions are simple
// averages of your own past cycles (not medical advice, not contraception).
interface Day { date: string; flow: string | null; note: string | null }
interface Overview {
  days: Day[]; periods: { start: string; end: string; length: number }[]; cycle_lengths: number[]
  stats: { cycles_logged: number; average_cycle: number | null; average_period: number | null; regular: boolean | null; shortest: number | null; longest: number | null; current_cycle_day: number | null }
  predictions: { start: string; earliest: string; latest: string; length: number }[]; next_in_days: number | null; late_by_days: number | null
}
const FLOWS = ['spotting', 'light', 'medium', 'heavy'] as const
const { t, locale } = useI18n()
const loc = computed(() => intlLocale(locale.value))
const today = toIso(new Date())
const data = ref<Overview | null>(null)
const error = ref('')
const flow = ref<(typeof FLOWS)[number]>('medium')
const month = ref(today.slice(0, 7))

async function load() {
  try {
    data.value = (await api.get<Overview>('/api/cycle')).data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
async function run(fn: () => Promise<unknown>) {
  error.value = ''
  try {
    await fn()
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

const logged = computed(() => new Map((data.value?.days ?? []).map((d) => [d.date, d])))
const predicted = computed(() => {
  const set = new Set<string>()
  for (const p of data.value?.predictions ?? []) {
    const start = new Date(p.start + 'T00:00:00')
    for (let i = 0; i < p.length; i++) set.add(toIso(new Date(start.getFullYear(), start.getMonth(), start.getDate() + i)))
  }
  return set
})

function toggle(date: string) {
  if (date > today) return
  return run(() => (logged.value.has(date) ? api.delete(`/api/cycle/day/${date}`) : api.put(`/api/cycle/day/${date}`, { flow: flow.value })))
}
const startToday = () => run(() => api.put(`/api/cycle/day/${today}`, { flow: flow.value }))

const monthLabel = computed(() => new Intl.DateTimeFormat(loc.value, { month: 'long', year: 'numeric' }).format(new Date(Number(month.value.slice(0, 4)), Number(month.value.slice(5)) - 1, 1)))
function shift(n: number) {
  const d = new Date(Number(month.value.slice(0, 4)), Number(month.value.slice(5)) - 1 + n, 1)
  month.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}
const weekdays = computed(() => {
  const f = new Intl.DateTimeFormat(loc.value, { weekday: 'narrow' })
  return Array.from({ length: 7 }, (_, i) => f.format(new Date(2024, 0, 1 + i)))
})
const cells = computed(() => {
  const y = Number(month.value.slice(0, 4)), m = Number(month.value.slice(5)) - 1
  const lead = (new Date(y, m, 1).getDay() + 6) % 7
  const n = new Date(y, m + 1, 0).getDate()
  return [...Array(lead).fill(null), ...Array.from({ length: n }, (_, i) => ({ day: i + 1, date: `${month.value}-${String(i + 1).padStart(2, '0')}` }))]
})
const maxLen = computed(() => Math.max(1, ...(data.value?.cycle_lengths ?? [1])))
onMounted(load)
</script>

<template>
  <div v-if="data" class="space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>

    <section class="bg-surface rounded-xl shadow p-4 space-y-2 border-t-4 border-pink-500">
      <h3 class="font-bold text-slate-800">🌸 {{ t('cycle.title') }}</h3>
      <template v-if="data.stats.current_cycle_day">
        <p class="text-slate-800">{{ t('cycle.day', { n: data.stats.current_cycle_day }) }}</p>
        <p v-if="data.predictions.length" class="text-sm text-slate-700">
          <template v-if="data.late_by_days">{{ t('cycle.late', data.late_by_days) }}</template>
          <template v-else-if="data.next_in_days === 0">{{ t('cycle.today') }}</template>
          <template v-else-if="(data.next_in_days ?? 0) > 0">{{ t('cycle.next', { date: formatDate(data.predictions[0].start), n: data.next_in_days, spread: Math.round((new Date(data.predictions[0].latest).getTime() - new Date(data.predictions[0].earliest).getTime()) / 86_400_000 / 2) }) }}</template>
        </p>
        <p v-else class="text-sm text-slate-500">{{ t('cycle.needMore') }}</p>
      </template>
      <p v-else class="text-sm text-slate-600">{{ t('cycle.intro') }}</p>
      <div class="flex flex-wrap items-center gap-2 pt-1">
        <button type="button" @click="startToday" class="bg-primary text-on-primary rounded-lg px-3 py-1.5 text-sm hover:bg-primary-hover">{{ t('cycle.markToday') }}</button>
        <span class="text-xs text-slate-500">{{ t('cycle.flow') }}:</span>
        <button v-for="f in FLOWS" :key="f" type="button" :aria-pressed="flow === f" @click="flow = f"
          :class="['rounded-full border px-2.5 py-0.5 text-xs', flow === f ? 'border-slate-700 bg-slate-100 font-semibold text-slate-900' : 'border-slate-300 text-slate-600 hover:bg-slate-50']">{{ t(`cycle.flows.${f}`) }}</button>
      </div>
    </section>

    <section class="bg-surface rounded-xl shadow p-4 space-y-2">
      <div class="flex items-center justify-between gap-2">
        <button type="button" @click="shift(-1)" :aria-label="t('calendar.prev')" class="w-8 h-8 rounded-full border border-slate-300 hover:bg-slate-50">‹</button>
        <h3 class="font-bold text-slate-800 capitalize">{{ monthLabel }}</h3>
        <button type="button" @click="shift(1)" :aria-label="t('calendar.next')" class="w-8 h-8 rounded-full border border-slate-300 hover:bg-slate-50">›</button>
      </div>
      <div class="grid grid-cols-7 gap-1 text-center text-xs text-slate-500"><div v-for="(w, i) in weekdays" :key="i">{{ w }}</div></div>
      <div class="grid grid-cols-7 gap-1">
        <template v-for="(c, i) in cells" :key="i">
          <div v-if="!c" />
          <button v-else type="button" @click="toggle(c.date)" :disabled="c.date > today"
            :aria-label="`${formatDate(c.date)}${logged.has(c.date) ? ' — ' + t('cycle.logged') : predicted.has(c.date) ? ' — ' + t('cycle.expected') : ''}`" :aria-pressed="logged.has(c.date)"
            :class="['h-10 rounded-lg text-sm border', logged.has(c.date) ? 'bg-pink-700 text-white border-pink-800 font-semibold' : predicted.has(c.date) ? 'border-2 border-dashed border-pink-500 text-slate-800' : 'border-transparent text-slate-700 hover:bg-slate-50', c.date === today ? 'ring-1 ring-slate-500' : '', c.date > today ? 'opacity-40' : '']">{{ c.day }}</button>
        </template>
      </div>
      <p class="text-xs text-slate-500"><span class="inline-block w-3 h-3 rounded bg-pink-700 align-middle"></span> {{ t('cycle.logged') }} · <span class="inline-block w-3 h-3 rounded border-2 border-dashed border-pink-500 align-middle"></span> {{ t('cycle.expected') }} · {{ t('cycle.tapHint') }}</p>
    </section>

    <section v-if="data.stats.average_cycle" class="grid grid-cols-3 gap-3 text-center">
      <div class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ data.stats.average_cycle }}</p><p class="text-xs text-slate-500">{{ t('cycle.avgCycle') }}</p></div>
      <div class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ data.stats.average_period }}</p><p class="text-xs text-slate-500">{{ t('cycle.avgPeriod') }}</p></div>
      <div class="bg-surface rounded-xl shadow p-3"><p class="text-xl font-bold text-slate-800 tabular-nums">{{ data.stats.shortest }}–{{ data.stats.longest }}</p><p class="text-xs text-slate-500">{{ t('cycle.range') }}</p></div>
    </section>

    <section v-if="data.cycle_lengths.length" class="bg-surface rounded-xl shadow p-4">
      <h3 class="font-bold text-slate-800 mb-2">{{ t('cycle.lengths') }}</h3>
      <div class="flex items-end gap-2 h-20" role="img" :aria-label="t('cycle.lengths')">
        <div v-for="(n, i) in data.cycle_lengths" :key="i" class="flex-1 flex flex-col items-center justify-end h-full gap-1"><span class="text-xs text-slate-500 tabular-nums">{{ n }}</span><div class="w-full rounded-t bg-pink-400" :style="{ height: (n / maxLen) * 100 + '%' }"></div></div>
      </div>
      <p v-if="data.stats.regular !== null" class="text-xs text-slate-500 mt-1">{{ t(data.stats.regular ? 'cycle.regular' : 'cycle.irregular') }}</p>
    </section>

    <section v-if="data.periods.length" class="bg-surface rounded-xl shadow p-4">
      <h3 class="font-bold text-slate-800 mb-2">{{ t('wellness.history') }}</h3>
      <ul class="text-sm text-slate-700 divide-y"><li v-for="p in [...data.periods].reverse()" :key="p.start" class="py-1 flex justify-between"><span>{{ formatDate(p.start) }} – {{ formatDate(p.end) }}</span><span class="text-slate-500">{{ t('cycle.days', p.length) }}</span></li></ul>
    </section>

    <p class="text-xs text-slate-500">{{ t('cycle.disclaimer') }}</p>
  </div>
</template>
