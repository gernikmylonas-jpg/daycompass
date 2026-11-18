<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { formatDate, parseIso, toIso } from '../i18n/dates'
import DateField from './DateField.vue'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'

// Weight, kept calm: one reading a day, a 7-day trend because single readings jump around, an optional goal and
// BMI. It never colours a number red and never awards points for a result.
interface Entry { date: string; kg: number; avg7: number }
interface Profile { height_cm: number | null; goal_kg: number | null; unit: 'kg' | 'lb'; show_bmi: boolean }
interface Stats {
  logged_total: number; latest: { date: string; kg: number } | null; trend: number | null
  change_7d: number | null; change_30d: number | null; to_goal: number | null; bmi: number | null; rapid_loss: boolean
}

const LB = 2.20462
const { t, locale } = useI18n()
const badgesStore = useBadgesStore()
const today = toIso(new Date())

const range = ref<30 | 90 | 365>(90)
const profile = ref<Profile>({ height_cm: null, goal_kg: null, unit: 'kg', show_bmi: false })
const entries = ref<Entry[]>([])
const stats = ref<Stats | null>(null)
const date = ref(today)
const input = ref<number | null>(null)
const error = ref('')
const message = ref('')
const showSettings = ref(false)
const form = ref({ height: null as number | null, goal: null as number | null })

const unit = computed(() => profile.value.unit)
const show = (kg: number) => (unit.value === 'lb' ? kg * LB : kg)
const fmt = (kg: number) => show(kg).toLocaleString(locale.value, { maximumFractionDigits: 1, minimumFractionDigits: 1 })
const signed = (kg: number) => `${kg > 0 ? '+' : kg < 0 ? '−' : ''}${Math.abs(show(kg)).toLocaleString(locale.value, { maximumFractionDigits: 1, minimumFractionDigits: 1 })}`

async function load() {
  try {
    const { data } = await api.get<{ profile: Profile; entries: Entry[]; stats: Stats }>('/api/weight', { params: { days: range.value } })
    profile.value = data.profile
    entries.value = data.entries
    stats.value = data.stats
    form.value = { height: data.profile.height_cm, goal: data.profile.goal_kg === null ? null : Math.round(show(data.profile.goal_kg) * 10) / 10 }
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function save() {
  error.value = message.value = ''
  if (input.value == null) return
  const kg = unit.value === 'lb' ? input.value / LB : input.value
  try {
    const { data } = await api.put<{ new_badges?: BadgeInfo[] }>(`/api/weight/${date.value}`, { kg })
    await badgesStore.announce(data.new_badges)
    message.value = t('weight.saved')
    input.value = null
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function remove(e: Entry) {
  if (!confirm(t('wellness.confirmDelete', { date: formatDate(e.date) }))) return
  try {
    await api.delete(`/api/weight/${e.date}`)
    await load()
  } catch (err) {
    error.value = apiErrorMessage(err)
  }
}

async function saveProfile(next?: Partial<Profile>) {
  error.value = message.value = ''
  const goalKg = form.value.goal == null ? null : (next?.unit ?? unit.value) === 'lb' ? form.value.goal / LB : form.value.goal
  try {
    await api.put('/api/weight/profile', {
      height_cm: form.value.height || null,
      goal_kg: goalKg,
      unit: next?.unit ?? profile.value.unit,
      show_bmi: next?.show_bmi ?? profile.value.show_bmi,
    })
    message.value = t('weight.saved')
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

// ── the chart: faint dots for each reading, a strong line for the 7-day trend, a dashed line for the goal ──
const W = 320
const H = 160
const PAD = { l: 38, r: 8, t: 10, b: 20 }
const chart = computed(() => {
  const pts = entries.value
  if (pts.length < 2) return null
  const values = [...pts.flatMap((p) => [p.kg, p.avg7]), ...(profile.value.goal_kg ? [profile.value.goal_kg] : [])]
  const lo = Math.floor(Math.min(...values) - 1)
  const hi = Math.ceil(Math.max(...values) + 1)
  const t0 = parseIso(pts[0].date).getTime()
  const t1 = parseIso(pts[pts.length - 1].date).getTime()
  const x = (d: string) => PAD.l + ((parseIso(d).getTime() - t0) / Math.max(t1 - t0, 1)) * (W - PAD.l - PAD.r)
  const y = (kg: number) => PAD.t + (1 - (kg - lo) / (hi - lo)) * (H - PAD.t - PAD.b)
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.date).toFixed(1)},${y(p.avg7).toFixed(1)}`).join(' ')
  const ticks = [lo, (lo + hi) / 2, hi]
  return { x, y, line, ticks, first: pts[0].date, last: pts[pts.length - 1].date }
})

const latestFirst = computed(() => [...entries.value].reverse().slice(0, 10))
const arrow = (n: number) => (n > 0.05 ? '↗' : n < -0.05 ? '↘' : '→')

function setRange(r: 30 | 90 | 365) {
  range.value = r
  load()
}
onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
    <p v-if="message" role="status" class="text-ok text-sm font-medium">{{ message }}</p>

    <section v-if="stats" class="grid grid-cols-2 gap-3 text-center">
      <div class="bg-surface rounded-xl shadow p-3 border-t-4 border-sky-500 col-span-2 sm:col-span-1">
        <p class="text-xs text-slate-500">{{ t('weight.trend') }}</p>
        <p class="text-3xl font-bold text-slate-800 tabular-nums" style="font-family: var(--font-display)">
          {{ stats.trend !== null ? fmt(stats.trend) : '—' }}<span class="text-base font-normal text-slate-500"> {{ unit }}</span>
        </p>
        <p v-if="stats.latest" class="text-xs text-slate-500">{{ t('weight.latest', { kg: fmt(stats.latest.kg), unit, date: formatDate(stats.latest.date) }) }}</p>
      </div>
      <div class="bg-surface rounded-xl shadow p-3">
        <p class="text-xs text-slate-500">{{ t('weight.week') }}</p>
        <p class="text-xl font-bold text-slate-800 tabular-nums">
          <template v-if="stats.change_7d !== null">{{ arrow(stats.change_7d) }} {{ signed(stats.change_7d) }} {{ unit }}</template><template v-else>—</template>
        </p>
        <p class="text-xs text-slate-500">
          <template v-if="stats.change_30d !== null">{{ t('weight.month') }}: {{ signed(stats.change_30d) }} {{ unit }}</template>
        </p>
      </div>
      <div v-if="stats.to_goal !== null && profile.goal_kg" class="bg-surface rounded-xl shadow p-3">
        <p class="text-xs text-slate-500">{{ t('weight.goal') }}: {{ fmt(profile.goal_kg) }} {{ unit }}</p>
        <p class="text-xl font-bold text-slate-800 tabular-nums">{{ stats.to_goal === 0 ? t('weight.atGoal') : t('weight.toGoal', { n: fmt(Math.abs(stats.to_goal)), unit }) }}</p>
      </div>
      <div v-if="stats.bmi !== null" class="bg-surface rounded-xl shadow p-3">
        <p class="text-xs text-slate-500">{{ t('weight.bmi') }}</p>
        <p class="text-xl font-bold text-slate-800 tabular-nums">{{ stats.bmi }}</p>
        <p class="text-xs text-slate-500">{{ t('weight.bmiNote') }}</p>
      </div>
    </section>

    <p v-if="stats?.rapid_loss" role="note" class="text-sm text-slate-700 bg-surface rounded-xl shadow p-3 border-l-4 border-amber-500">
      {{ t('weight.rapid') }}
    </p>

    <section class="bg-surface rounded-xl shadow p-4 space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h3 class="font-bold text-slate-800">{{ t('weight.log') }}</h3>
        <DateField v-model="date" min="2000-01-01" :max="today" :label="t('wellness.date')" required />
      </div>
      <form @submit.prevent="save" class="flex items-end gap-3">
        <label class="text-sm text-slate-600 flex-1">
          {{ t('weight.title') }} ({{ unit }})
          <input v-model.number="input" type="number" step="0.1" min="1" max="900" required inputmode="decimal"
            :aria-label="t('weight.title')" class="mt-1 border rounded-lg px-3 py-2 w-full" />
        </label>
        <button type="submit" class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover">{{ t('common.save') }}</button>
      </form>
      <p class="text-xs text-slate-500">{{ t('weight.hint') }}</p>
    </section>

    <section class="bg-surface rounded-xl shadow p-4">
      <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
        <h3 class="font-bold text-slate-800">{{ t('weight.chart') }}</h3>
        <div class="flex gap-1" role="radiogroup" :aria-label="t('weight.chart')">
          <button v-for="r in ([30, 90, 365] as const)" :key="r" type="button" role="radio" :aria-checked="range === r" @click="setRange(r)"
            :class="['rounded-lg px-3 py-1 text-xs', range === r ? 'bg-primary text-on-primary' : 'border border-slate-400 text-slate-600 hover:bg-slate-50']">
            {{ t('weight.days', r) }}
          </button>
        </div>
      </div>
      <svg v-if="chart" :viewBox="`0 0 ${W} ${H}`" class="w-full" role="img" :aria-label="t('weight.chart')">
        <g v-for="v in chart.ticks" :key="v">
          <line :x1="PAD.l" :x2="W - PAD.r" :y1="chart.y(v)" :y2="chart.y(v)" stroke="var(--color-slate-200)" stroke-width="0.7" />
          <text :x="PAD.l - 4" :y="chart.y(v) + 3" text-anchor="end" font-size="8" fill="var(--color-slate-500)">{{ Math.round(show(v)) }}</text>
        </g>
        <line v-if="profile.goal_kg" :x1="PAD.l" :x2="W - PAD.r" :y1="chart.y(profile.goal_kg)" :y2="chart.y(profile.goal_kg)" stroke="var(--color-compass-north)" stroke-dasharray="4 3" stroke-width="1" />
        <circle v-for="p in entries" :key="p.date" :cx="chart.x(p.date)" :cy="chart.y(p.kg)" r="2" fill="var(--color-slate-400)" opacity="0.7"><title>{{ formatDate(p.date) }}: {{ fmt(p.kg) }} {{ unit }}</title></circle>
        <path :d="chart.line" fill="none" stroke="var(--color-teal-500)" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" />
        <text :x="PAD.l" :y="H - 5" font-size="8" fill="var(--color-slate-500)">{{ formatDate(chart.first) }}</text>
        <text :x="W - PAD.r" :y="H - 5" text-anchor="end" font-size="8" fill="var(--color-slate-500)">{{ formatDate(chart.last) }}</text>
      </svg>
      <p v-else class="text-sm text-slate-500">{{ t('weight.needMore') }}</p>
      <p class="text-xs text-slate-500 mt-1">{{ t('weight.legend') }}</p>
    </section>

    <section class="bg-surface rounded-xl shadow p-4">
      <button type="button" @click="showSettings = !showSettings" :aria-expanded="showSettings" class="w-full flex items-center justify-between text-sm font-bold text-slate-800">
        {{ t('weight.settings') }} <span aria-hidden="true">{{ showSettings ? '▴' : '▾' }}</span>
      </button>
      <form v-if="showSettings" @submit.prevent="saveProfile()" class="space-y-3 mt-3">
        <div class="flex gap-2" role="radiogroup" :aria-label="t('weight.unit')">
          <button v-for="u in (['kg', 'lb'] as const)" :key="u" type="button" role="radio" :aria-checked="unit === u" @click="saveProfile({ unit: u })"
            :class="['rounded-lg px-4 py-1.5 text-sm', unit === u ? 'bg-primary text-on-primary' : 'border border-slate-400 text-slate-600 hover:bg-slate-50']">{{ u }}</button>
        </div>
        <div class="flex flex-wrap gap-3">
          <label class="text-sm text-slate-600 flex-1 min-w-32">{{ t('weight.height') }} (cm)
            <input v-model.number="form.height" type="number" min="80" max="250" class="mt-1 border rounded-lg px-3 py-2 w-full" /></label>
          <label class="text-sm text-slate-600 flex-1 min-w-32">{{ t('weight.goal') }} ({{ unit }})
            <input v-model.number="form.goal" type="number" step="0.1" min="1" max="900" class="mt-1 border rounded-lg px-3 py-2 w-full" /></label>
        </div>
        <label class="flex items-start gap-2 text-sm text-slate-700">
          <input type="checkbox" class="mt-1 h-4 w-4" :checked="profile.show_bmi" @change="saveProfile({ show_bmi: ($event.target as HTMLInputElement).checked })" />
          <span>{{ t('weight.showBmi') }}<span class="block text-xs text-slate-500">{{ t('weight.bmiHint') }}</span></span>
        </label>
        <button type="submit" class="bg-primary text-on-primary rounded-lg px-4 py-1.5 text-sm hover:bg-primary-hover">{{ t('common.save') }}</button>
      </form>
    </section>

    <section v-if="latestFirst.length" class="bg-surface rounded-xl shadow p-4">
      <h3 class="font-bold text-slate-800 mb-2">{{ t('wellness.history') }}</h3>
      <ul class="divide-y text-sm">
        <li v-for="e in latestFirst" :key="e.date" class="py-1.5 flex items-center justify-between text-slate-700">
          <span>{{ formatDate(e.date) }}</span>
          <span class="flex items-center gap-2"><b class="tabular-nums">{{ fmt(e.kg) }} {{ unit }}</b>
            <button @click="remove(e)" :aria-label="t('home.remove')" :title="t('home.remove')" class="w-6 h-6 inline-flex items-center justify-center rounded text-slate-500 hover:text-danger hover:bg-slate-100">✕</button></span>
        </li>
      </ul>
    </section>
  </div>
</template>
