<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '../i18n'
import { formatDate, formatDateTime, formatTime } from '../i18n/dates'
import {
  phaseEventsForYear, moonStateAt, nextPhase, eclipsesForYear, seasonsForYear, METEOR_SHOWERS,
  type Eclipse, type PhaseEvent,
} from '../astronomy'
import MoonIcon from './MoonIcon.vue'

// Moon phases, eclipses and sky events for any year from 2000 to 2100, computed on the device.

const MIN_YEAR = 2000
const MAX_YEAR = 2100
const YEARS = Array.from({ length: MAX_YEAR - MIN_YEAR + 1 }, (_, i) => MIN_YEAR + i)

const { t, locale } = useI18n()
const loc = computed(() => intlLocale(locale.value))

const now = new Date()
const tab = ref<'moon' | 'eclipses' | 'sky'>('moon')
const year = ref(Math.min(MAX_YEAR, Math.max(MIN_YEAR, now.getFullYear())))
const month = ref(now.getMonth() + 1)
const selectedDay = ref<number | null>(now.getDate())

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

const monthNames = computed(() => {
  const f = new Intl.DateTimeFormat(loc.value, { month: 'long' })
  return Array.from({ length: 12 }, (_, i) => cap(f.format(new Date(2024, i, 1))))
})
const WEEKDAYS = computed(() => {
  const f = new Intl.DateTimeFormat(loc.value, { weekday: 'short' })
  return Array.from({ length: 7 }, (_, i) => cap(f.format(new Date(2024, 0, 1 + i))))
})

// ── the Moon right now ───────────────────────────────────────────────────
const moonNow = computed(() => moonStateAt(now))
const nextNew = computed(() => nextPhase('new', now))
const nextFull = computed(() => nextPhase('full', now))
const percent = (illumination: number) => Math.round(illumination * 100)

// ── month view ───────────────────────────────────────────────────────────
interface DayEvent { icon: string; label: string; at: Date }

function inThisMonth(d: Date) {
  return d.getFullYear() === year.value && d.getMonth() + 1 === month.value
}

const monthPhases = computed<PhaseEvent[]>(() =>
  [year.value - 1, year.value, year.value + 1]
    .flatMap((y) => (y >= MIN_YEAR - 1 && y <= MAX_YEAR + 1 ? phaseEventsForYear(y) : []))
    .filter((e) => inThisMonth(e.date)),
)

const monthEclipses = computed<Eclipse[]>(() =>
  [year.value - 1, year.value, year.value + 1]
    .flatMap((y) => (y >= MIN_YEAR && y <= MAX_YEAR ? eclipsesForYear(y) : []))
    .filter((e) => inThisMonth(e.date)),
)

const hasBlueMoon = computed(() => monthPhases.value.filter((e) => e.kind === 'full').length >= 2)

const eventsByDay = computed(() => {
  const map = new Map<number, DayEvent[]>()
  const add = (day: number, ev: DayEvent) => map.set(day, [...(map.get(day) ?? []), ev])
  for (const e of monthPhases.value) add(e.date.getDate(), { icon: '', label: t(`astro.events.${e.kind}`), at: e.date })
  for (const e of monthEclipses.value) {
    add(e.date.getDate(), { icon: e.kind === 'solar' ? '☉' : '☽', label: eclipseLabel(e), at: e.date })
  }
  return map
})

const cells = computed(() => {
  const firstWeekday = (new Date(year.value, month.value - 1, 1).getDay() + 6) % 7
  const days = new Date(year.value, month.value, 0).getDate()
  const out: ({ day: number; cycle: number; marks: DayEvent[] } | null)[] = []
  for (let i = 0; i < firstWeekday; i++) out.push(null)
  for (let d = 1; d <= days; d++) {
    out.push({ day: d, cycle: moonStateAt(new Date(year.value, month.value - 1, d, 12)).cycle, marks: eventsByDay.value.get(d) ?? [] })
  }
  return out
})

const selectedState = computed(() =>
  selectedDay.value ? moonStateAt(new Date(year.value, month.value - 1, selectedDay.value, 12)) : null,
)
const selectedMarks = computed(() => (selectedDay.value ? (eventsByDay.value.get(selectedDay.value) ?? []) : []))

function shiftMonth(delta: number) {
  let m = month.value + delta
  let y = year.value
  if (m < 1) { m = 12; y-- }
  if (m > 12) { m = 1; y++ }
  if (y < MIN_YEAR || y > MAX_YEAR) return
  month.value = m
  year.value = y
  selectedDay.value = null
}
const canPrev = computed(() => !(year.value === MIN_YEAR && month.value === 1))
const canNext = computed(() => !(year.value === MAX_YEAR && month.value === 12))

function goToday() {
  year.value = Math.min(MAX_YEAR, Math.max(MIN_YEAR, now.getFullYear()))
  month.value = now.getMonth() + 1
  selectedDay.value = now.getDate()
}

// ── eclipses ─────────────────────────────────────────────────────────────
const eclipses = computed(() => eclipsesForYear(year.value))
const nextEclipse = computed(() => {
  const all = [now.getFullYear(), now.getFullYear() + 1].filter((y) => y <= MAX_YEAR).flatMap((y) => eclipsesForYear(y))
  return all.find((e) => e.date.getTime() > now.getTime()) ?? null
})

function eclipseLabel(e: Eclipse) {
  return `${t(`astro.eclipse.${e.kind}`)} · ${t(`astro.eclipse.${e.type}`)}`
}

// ── sky events ───────────────────────────────────────────────────────────
const seasons = computed(() => seasonsForYear(year.value))
const showers = computed(() =>
  METEOR_SHOWERS.map((s) => {
    const peak = new Date(year.value, s.month - 1, s.day, 12)
    const light = moonStateAt(peak).illumination
    return { ...s, peak, light, quality: light < 0.25 ? 'dark' : light < 0.6 ? 'some' : 'bright' }
  }),
)
</script>

<template>
  <div class="space-y-4">
    <!-- the Moon today -->
    <section class="bg-surface rounded-xl shadow p-4 flex items-center gap-4 border-t-4 border-sky-500">
      <MoonIcon :cycle="moonNow.cycle" :size="72" />
      <div class="min-w-0">
        <p class="text-xs uppercase tracking-wider text-slate-500">{{ t('astro.today') }}</p>
        <p class="text-lg font-bold text-slate-800">{{ t(`astro.phases.${moonNow.name}`) }}</p>
        <p class="text-sm text-slate-600">
          {{ t('astro.illumination', { n: percent(moonNow.illumination) }) }} · {{ t('astro.age', { n: moonNow.ageDays.toFixed(1) }) }}
        </p>
        <p class="text-xs text-slate-500 mt-1">
          {{ t('astro.nextNew') }}: {{ formatDateTime(nextNew.date) }}<br />
          {{ t('astro.nextFull') }}: {{ formatDateTime(nextFull.date) }}
        </p>
      </div>
    </section>

    <section class="bg-surface rounded-xl shadow p-4">
      <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div class="flex gap-1" role="tablist" :aria-label="t('astro.title')">
          <button v-for="k in (['moon', 'eclipses', 'sky'] as const)" :key="k" role="tab" :aria-selected="tab === k"
            @click="tab = k"
            :class="['px-3 py-1 rounded-lg text-sm', tab === k ? 'bg-primary text-on-primary' : 'border border-slate-400 text-slate-600 hover:bg-slate-50']">
            {{ t(`astro.tabs.${k}`) }}
          </button>
        </div>
        <div class="flex items-center gap-2">
          <select v-if="tab === 'moon'" v-model.number="month" :aria-label="t('calendar.monthLabel')" class="border rounded-lg px-2 py-1 text-sm">
            <option v-for="(name, i) in monthNames" :key="i" :value="i + 1">{{ name }}</option>
          </select>
          <select v-model.number="year" :aria-label="t('calendar.year')" class="border rounded-lg px-2 py-1 text-sm">
            <option v-for="y in YEARS" :key="y" :value="y">{{ y }}</option>
          </select>
        </div>
      </div>

      <!-- MOON: month calendar with a Moon for every day -->
      <div v-if="tab === 'moon'">
        <div class="flex items-center justify-between mb-2">
          <button @click="shiftMonth(-1)" :disabled="!canPrev" :aria-label="t('calendar.prev')"
            class="px-3 py-1 rounded-lg hover:bg-slate-100 text-slate-600 disabled:opacity-30">‹</button>
          <h3 class="font-bold text-slate-800">{{ monthNames[month - 1] }} {{ year }}</h3>
          <div class="flex items-center gap-1">
            <button @click="goToday" class="text-xs border border-slate-400 text-slate-600 rounded-lg px-2 py-1 hover:bg-slate-50">{{ t('calendar.today') }}</button>
            <button @click="shiftMonth(1)" :disabled="!canNext" :aria-label="t('calendar.next')"
              class="px-3 py-1 rounded-lg hover:bg-slate-100 text-slate-600 disabled:opacity-30">›</button>
          </div>
        </div>

        <div class="grid grid-cols-7 gap-1 text-center text-xs text-slate-500 mb-1">
          <div v-for="w in WEEKDAYS" :key="w">{{ w }}</div>
        </div>
        <div class="grid grid-cols-7 gap-1">
          <template v-for="(c, i) in cells" :key="i">
            <div v-if="!c" />
            <button v-else @click="selectedDay = c.day" :aria-pressed="selectedDay === c.day"
              :aria-label="`${c.day} ${monthNames[month - 1]} ${year}: ${[...new Set(c.marks.map((m) => m.label))].join(', ')}`"
              :class="['rounded-lg border py-1 text-xs flex flex-col items-center gap-0.5 relative',
                selectedDay === c.day ? 'border-slate-800 bg-slate-50' : c.marks.length ? 'border-slate-300' : 'border-transparent hover:bg-slate-50',
                year === now.getFullYear() && month === now.getMonth() + 1 && c.day === now.getDate() ? 'font-bold text-teal-700' : 'text-slate-700']">
              <span>{{ c.day }}</span>
              <MoonIcon :cycle="c.cycle" :size="24" />
              <span v-if="c.marks.some((m) => m.icon)" class="absolute top-0 right-0.5 text-[0.65rem] leading-none" style="color: var(--color-compass-north)" aria-hidden="true">
                {{ c.marks.find((m) => m.icon)?.icon }}
              </span>
            </button>
          </template>
        </div>
        <p v-if="hasBlueMoon" class="text-xs text-slate-500 mt-2">🔵 {{ t('astro.blueMoon') }}</p>

        <div v-if="selectedDay && selectedState" class="mt-3 border-t border-slate-200 pt-3 flex items-start gap-3">
          <MoonIcon :cycle="selectedState.cycle" :size="48" />
          <div class="text-sm min-w-0">
            <p class="font-semibold text-slate-800">{{ formatDate(new Date(year, month - 1, selectedDay)) }}</p>
            <p class="text-slate-600">{{ t(`astro.phases.${selectedState.name}`) }} · {{ t('astro.illumination', { n: percent(selectedState.illumination) }) }}</p>
            <p class="text-slate-500">{{ t('astro.age', { n: selectedState.ageDays.toFixed(1) }) }}</p>
            <ul v-if="selectedMarks.length" class="mt-1 space-y-0.5 text-slate-700">
              <li v-for="(m, i) in selectedMarks" :key="i">
                <span aria-hidden="true">{{ m.icon || '•' }}</span> {{ m.label }} — {{ formatTime(m.at) }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- ECLIPSES of the year -->
      <div v-else-if="tab === 'eclipses'" class="space-y-3">
        <p v-if="nextEclipse" class="text-sm rounded-lg bg-slate-50 border border-slate-200 p-2 text-slate-700">
          <span class="font-semibold">{{ t('astro.eclipse.next') }}:</span>
          {{ eclipseLabel(nextEclipse) }} — {{ formatDateTime(nextEclipse.date) }}
        </p>
        <ul v-if="eclipses.length" class="divide-y">
          <li v-for="(e, i) in eclipses" :key="i" class="py-2 flex items-start gap-3 text-sm">
            <span class="text-2xl leading-none w-7 text-center" style="color: var(--color-compass-north)" aria-hidden="true">{{ e.kind === 'solar' ? '☉' : '☽' }}</span>
            <div class="min-w-0">
              <p class="font-medium text-slate-800">{{ eclipseLabel(e) }}</p>
              <p class="text-slate-600">{{ formatDateTime(e.date) }}</p>
              <p v-if="e.magnitude !== null" class="text-xs text-slate-500">{{ t('astro.eclipse.magnitude', { n: e.magnitude.toFixed(2) }) }}</p>
            </div>
          </li>
        </ul>
        <p v-else class="text-sm text-slate-500">{{ t('astro.eclipse.none') }}</p>
        <p class="text-xs text-slate-500">{{ t('astro.eclipse.note') }}</p>
      </div>

      <!-- SKY EVENTS: seasons and meteor showers -->
      <div v-else class="space-y-4">
        <div>
          <h3 class="font-semibold text-slate-800 mb-1">{{ t('astro.sky.seasonsTitle') }}</h3>
          <ul class="divide-y text-sm">
            <li v-for="s in seasons" :key="s.kind" class="py-1.5 flex justify-between gap-3">
              <span class="text-slate-700">{{ t(`astro.sky.seasons.${s.kind}`) }}</span>
              <span class="text-slate-600 tabular-nums">{{ formatDateTime(s.date) }}</span>
            </li>
          </ul>
        </div>
        <div>
          <h3 class="font-semibold text-slate-800 mb-1">{{ t('astro.sky.showersTitle') }}</h3>
          <ul class="divide-y text-sm">
            <li v-for="s in showers" :key="s.key" class="py-1.5">
              <div class="flex justify-between gap-3">
                <span class="text-slate-700 font-medium">{{ t(`astro.sky.showers.${s.key}`) }}</span>
                <span class="text-slate-600 tabular-nums">{{ formatDate(s.peak) }}</span>
              </div>
              <p class="text-xs text-slate-500">
                {{ t('astro.sky.zhr', { n: s.zhr }) }} · {{ t(`astro.sky.${s.quality}`) }} ({{ percent(s.light) }}%)
              </p>
            </li>
          </ul>
        </div>
      </div>

      <p class="text-xs text-slate-500 mt-3">{{ t('astro.localTime') }}</p>
    </section>
  </div>
</template>
