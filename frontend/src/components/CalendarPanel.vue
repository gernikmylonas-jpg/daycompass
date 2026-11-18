<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { intlLocale } from '../i18n'
import { formatDate } from '../i18n/dates'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'
import DateField from './DateField.vue'
import type { Category } from '../stores/habits'

// Month / week calendar for the years 2000-2100: habit check-ins plus the user's own notes
// (birthdays that repeat every year, reminders, events, free notes) on any day.

type Kind = 'birthday' | 'reminder' | 'event' | 'note'

interface CheckInEntry {
  date: string
  habit_id: string
  habit_name: string
  category: Category
}

interface CalEvent {
  id: string
  title: string
  kind: Kind
  notes: string | null
  repeat_yearly: boolean
  repeat_weekly: boolean
  date: string
  original_date: string
}

import { useSettingsStore } from '../stores/settings'
import { namesOn } from '../calendars/nameDays'
import { historyOn, formatYear } from '../calendars/history'
import { parseIcs } from '../calendars/ics'
import { nationalDaysOn, flagOf } from '../calendars/nationalDays'

const MIN_YEAR = 2000
const MAX_YEAR = 2100
const KINDS: Kind[] = ['birthday', 'reminder', 'event', 'note']
const KIND_ICON: Record<Kind, string> = { birthday: '🎂', reminder: '⏰', event: '📌', note: '📝' }
const YEARS = Array.from({ length: MAX_YEAR - MIN_YEAR + 1 }, (_, i) => MIN_YEAR + i)

const dotColor: Record<Category, string> = {
  body: 'bg-teal-500',
  work: 'bg-orange-500',
  schedule: 'bg-pink-500',
  mind: 'bg-purple-500',
}

const { t, locale } = useI18n()
const badgesStore = useBadgesStore()
const settings = useSettingsStore()
const layers = settings.calendarLayers
const loc = computed(() => intlLocale(locale.value))

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
const iso = (y: number, m: number, d: number) => `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
const parse = (s: string) => {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}
const toIso = (d: Date) => iso(d.getFullYear(), d.getMonth() + 1, d.getDate())
const addDays = (s: string, n: number) => {
  const d = parse(s)
  d.setDate(d.getDate() + n)
  return toIso(d)
}
const mondayOf = (d: Date) => {
  const copy = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  copy.setDate(copy.getDate() - ((copy.getDay() + 6) % 7))
  return toIso(copy)
}

const now = new Date()
const todayIso = toIso(now)

const view = ref<'month' | 'week'>('month')
const year = ref(Math.min(MAX_YEAR, Math.max(MIN_YEAR, now.getFullYear())))
const month = ref(now.getMonth() + 1)
const weekStart = ref(mondayOf(now))
const entries = ref<CheckInEntry[]>([])
const events = ref<CalEvent[]>([])
const restDays = ref<string[]>([])
const selected = ref<string | null>(todayIso)
const error = ref('')

// note form (add or edit)
const form = ref<{ id: string | null; title: string; kind: Kind; notes: string; repeat: boolean; weekly: boolean; date: string } | null>(null)
const busy = ref(false)

const monthNames = computed(() => {
  const f = new Intl.DateTimeFormat(loc.value, { month: 'long' })
  return Array.from({ length: 12 }, (_, i) => cap(f.format(new Date(2024, i, 1))))
})

// 2024-01-01 was a Monday, so these are Monday..Sunday in the active language.
const WEEKDAYS = computed(() => {
  const f = new Intl.DateTimeFormat(loc.value, { weekday: 'short' })
  return Array.from({ length: 7 }, (_, i) => cap(f.format(new Date(2024, 0, 1 + i))))
})

const byDateEntries = computed(() => {
  const map = new Map<string, CheckInEntry[]>()
  for (const e of entries.value) map.set(e.date, [...(map.get(e.date) ?? []), e])
  return map
})

const byDateEvents = computed(() => {
  const map = new Map<string, CalEvent[]>()
  for (const e of events.value) map.set(e.date, [...(map.get(e.date) ?? []), e])
  return map
})

const cells = computed(() => {
  const firstWeekday = (new Date(year.value, month.value - 1, 1).getDay() + 6) % 7
  const daysInMonth = new Date(year.value, month.value, 0).getDate()
  const result: ({ day: number; date: string } | null)[] = []
  for (let i = 0; i < firstWeekday; i++) result.push(null)
  for (let d = 1; d <= daysInMonth; d++) result.push({ day: d, date: iso(year.value, month.value, d) })
  return result
})

const weekDays = computed(() =>
  WEEKDAYS.value.map((label, i) => {
    const date = addDays(weekStart.value, i)
    return { label, date, day: parse(date).getDate() }
  }),
)

const title = computed(() => {
  if (view.value === 'month') return `${monthNames.value[month.value - 1]} ${year.value}`
  const short = new Intl.DateTimeFormat(loc.value, { day: 'numeric', month: 'short' })
  const a = parse(weekStart.value)
  const b = parse(addDays(weekStart.value, 6))
  return `${short.format(a)} – ${short.format(b)} ${b.getFullYear()}`
})

function fullDate(s: string) {
  const f = new Intl.DateTimeFormat(loc.value, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  return cap(f.format(parse(s)))
}

const selectedEntries = computed(() => (selected.value ? (byDateEntries.value.get(selected.value) ?? []) : []))
const selectedEvents = computed(() => (selected.value ? (byDateEvents.value.get(selected.value) ?? []) : []))

function currentRange(): [string, string] {
  if (view.value === 'week') return [weekStart.value, addDays(weekStart.value, 6)]
  const last = new Date(year.value, month.value, 0).getDate()
  return [iso(year.value, month.value, 1), iso(year.value, month.value, last)]
}

// ── extra calendars the user can switch on ──────────────────────────────
const LAYER_DEFS = [
  { key: 'holidays', icon: '🏛' },
  { key: 'nameDays', icon: '✝' },
  { key: 'national', icon: '🏳' },
  { key: 'history', icon: '📜' },
  { key: 'journal', icon: '📓' },
] as const

const regionNames = computed(() => new Intl.DisplayNames([loc.value], { type: 'region' }))
const countryCodes = ref<string[]>([])
const countryOptions = computed(() =>
  countryCodes.value
    .map((cc) => ({ cc, name: regionNames.value.of(cc) ?? cc }))
    .sort((a, b) => a.name.localeCompare(b.name, loc.value)),
)
const countryName = (cc: string) => { try { return regionNames.value.of(cc) ?? cc } catch { return cc } }

const holidayCache = ref<Record<string, { date: string; name: string }[]>>({})
async function loadHolidays() {
  if (!layers.holidays) return
  if (!countryCodes.value.length) {
    try { countryCodes.value = (await api.get<string[]>('/api/calendars/countries')).data } catch (e) { error.value = apiErrorMessage(e); return }
  }
  const [start, end] = currentRange()
  const years = new Set([Number(start.slice(0, 4)), Number(end.slice(0, 4))])
  for (const y of years) {
    const k = `${layers.country}-${y}-${locale.value}`
    if (holidayCache.value[k]) continue
    try {
      holidayCache.value[k] = (await api.get('/api/calendars/holidays', { params: { country: layers.country, year: y, lang: locale.value } })).data
    } catch (e) {
      error.value = apiErrorMessage(e)
    }
  }
}
const holidaysByDate = computed(() => {
  const map = new Map<string, string[]>()
  for (const [k, list] of Object.entries(holidayCache.value)) {
    if (!k.startsWith(`${layers.country}-`) || !k.endsWith(`-${locale.value}`)) continue
    for (const h of list) map.set(h.date, [...(map.get(h.date) ?? []), h.name])
  }
  return map
})

const nameDaysFor = (d: string) => (layers.nameDays ? namesOn(parse(d)) : [])
const historyFor = (d: string) => (layers.history ? historyOn(Number(d.slice(5, 7)), Number(d.slice(8, 10))) : [])
const nationalFor = (d: string) => (layers.national ? nationalDaysOn(Number(d.slice(5, 7)), Number(d.slice(8, 10))) : [])
const journalDays = ref<Record<string, { entries: number; recordings: number }>>({})
async function loadJournalDays() {
  if (!layers.journal) return
  const [start, end] = currentRange()
  try {
    const { data } = await api.get<{ date: string; entries: number; recordings: number }[]>('/api/journal/days', { params: { start, end } })
    journalDays.value = Object.fromEntries(data.map((d) => [d.date, { entries: d.entries, recordings: d.recordings }]))
  } catch {
    journalDays.value = {}
  }
}
const journalFor = (d: string) => (layers.journal ? journalDays.value[d] ?? null : null)
const holidaysFor = (d: string) => (layers.holidays ? holidaysByDate.value.get(d) ?? [] : [])
const historyText = (h: { en: string; el: string }) => (locale.value === 'el' ? h.el : h.en)
// small glyphs under a day's number: which of the switched-on calendars have something that day
const dayGlyphs = (d: string) => [
  holidaysFor(d).length ? '🏛' : '',
  nameDaysFor(d).length ? '✝' : '',
  nationalFor(d).length ? '🏳' : '',
  historyFor(d).length ? '📜' : '',
  journalFor(d) ? (journalFor(d)!.recordings ? '🎙' : '📓') : '',
].filter(Boolean).join('')

watch(() => [layers.holidays, layers.country, locale.value], loadHolidays)
watch(() => layers.journal, loadJournalDays)

// ── .ics: take your notes to another calendar app, or bring events in from one ──
const icsInput = ref<HTMLInputElement | null>(null)
const icsMessage = ref('')
async function exportIcs() {
  error.value = ''
  try {
    const { data } = await api.get<Blob>('/api/calendar/events/ics', { responseType: 'blob' })
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'daycompass.ics'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
async function importIcs(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  error.value = icsMessage.value = ''
  // what is already there (same title on the same day), so importing the same file twice adds nothing new
  let existing = new Set<string>()
  try {
    const { data } = await api.get<Blob>('/api/calendar/events/ics', { responseType: 'blob' })
    existing = new Set(parseIcs(await data.text()).map((e) => `${e.date}|${e.title.toLowerCase()}`))
  } catch { /* if this fails, just import everything */ }
  const found = parseIcs(await file.text()).filter((e) => !existing.has(`${e.date}|${e.title.toLowerCase()}`)).filter((e) => Number(e.date.slice(0, 4)) >= 1900 && Number(e.date.slice(0, 4)) <= 2100).slice(0, 300)
  let added = 0
  for (const e of found) {
    try {
      await api.post('/api/calendar/events', { title: e.title, event_date: e.date, kind: 'event', notes: e.notes, repeat_yearly: e.yearly, repeat_weekly: e.weekly && !e.yearly })
      added++
    } catch (err) {
      error.value = apiErrorMessage(err)
      break
    }
  }
  icsMessage.value = t('calendar.ics.done', { n: added })
  await load()
}

const isRest = (d: string) => restDays.value.includes(d)
// a rest day can be set from a week back to three days ahead (the server enforces it too)
const canRest = (d: string) => d >= addDays(todayIso, -7) && d <= addDays(todayIso, 3)
async function toggleRest(d: string) {
  error.value = ''
  try {
    if (isRest(d)) await api.delete(`/api/rest-days/${d}`)
    else await api.put(`/api/rest-days/${d}`)
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function load() {
  error.value = ''
  const [start, end] = currentRange()
  try {
    const [checkIns, notes, rest] = await Promise.all([
      api.get<CheckInEntry[]>('/api/stats/calendar-range', { params: { start, end } }),
      api.get<CalEvent[]>('/api/calendar/events', { params: { start, end } }),
      api.get<string[]>('/api/rest-days', { params: { start, end } }),
    ])
    restDays.value = rest.data
    loadHolidays()
    loadJournalDays()
    entries.value = checkIns.data
    events.value = notes.data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

function inRange(dateIso: string) {
  const y = parse(dateIso).getFullYear()
  return y >= MIN_YEAR && y <= MAX_YEAR
}

const canPrev = computed(() =>
  view.value === 'month' ? !(year.value === MIN_YEAR && month.value === 1) : inRange(addDays(weekStart.value, -7)),
)
const canNext = computed(() =>
  view.value === 'month' ? !(year.value === MAX_YEAR && month.value === 12) : inRange(addDays(weekStart.value, 13)),
)

function shift(delta: number) {
  selected.value = null
  form.value = null
  if (view.value === 'week') {
    weekStart.value = addDays(weekStart.value, delta * 7)
    return
  }
  let m = month.value + delta
  let y = year.value
  if (m < 1) { m = 12; y-- }
  if (m > 12) { m = 1; y++ }
  if (y < MIN_YEAR || y > MAX_YEAR) return
  month.value = m
  year.value = y
}

function goToday() {
  year.value = Math.min(MAX_YEAR, Math.max(MIN_YEAR, now.getFullYear()))
  month.value = now.getMonth() + 1
  weekStart.value = mondayOf(now)
  selected.value = todayIso
}

function setView(v: 'month' | 'week') {
  if (v === view.value) return
  form.value = null
  if (v === 'week') {
    const showingCurrentMonth = year.value === now.getFullYear() && month.value === now.getMonth() + 1
    weekStart.value = showingCurrentMonth ? mondayOf(now) : mondayOf(new Date(year.value, month.value - 1, 1))
  } else {
    const d = parse(weekStart.value)
    year.value = Math.min(MAX_YEAR, Math.max(MIN_YEAR, d.getFullYear()))
    month.value = d.getMonth() + 1
  }
  view.value = v
}

function select(date: string) {
  selected.value = date
  form.value = null
}

function uniqueCategories(list: CheckInEntry[]) {
  return [...new Set(list.map((e) => e.category))]
}

// ── notes ────────────────────────────────────────────────────────────────
function startNew() {
  if (!selected.value) return
  form.value = { id: null, title: '', kind: 'note', notes: '', repeat: false, weekly: false, date: selected.value }
}

function startEdit(ev: CalEvent) {
  form.value = { id: ev.id, title: ev.title, kind: ev.kind, notes: ev.notes ?? '', repeat: ev.repeat_yearly, weekly: ev.repeat_weekly, date: ev.original_date }
}

// a birthday repeats every year by default
watch(() => form.value?.kind, (kind) => {
  if (form.value && !form.value.id && kind === 'birthday') form.value.repeat = true
})

async function save() {
  const f = form.value
  if (!f || !f.title.trim() || !f.date) return
  busy.value = true
  error.value = ''
  try {
    const payload = { title: f.title, event_date: f.date, kind: f.kind, notes: f.notes || null, repeat_yearly: f.repeat, repeat_weekly: f.weekly }
    if (f.id) await api.put(`/api/calendar/events/${f.id}`, payload)
    else {
      const { data } = await api.post<{ new_badges?: BadgeInfo[] }>('/api/calendar/events', payload)
      await badgesStore.announce(data.new_badges)
    }
    form.value = null
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  } finally {
    busy.value = false
  }
}

async function removeEvent(ev: CalEvent) {
  if (!confirm(t('calendar.confirmDelete'))) return
  error.value = ''
  try {
    await api.delete(`/api/calendar/events/${ev.id}`)
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

// ── right-click menu: add something to the day you clicked ──────────────
const menu = ref<{ x: number; y: number; date: string } | null>(null)
const menuEl = ref<HTMLElement | null>(null)
const titleInput = ref<HTMLInputElement | null>(null)
let menuReturnFocus: HTMLElement | null = null

async function openMenu(ev: MouseEvent, date: string) {
  ev.preventDefault() // also fires for the keyboard "context menu" key / Shift+F10
  select(date)
  menuReturnFocus = ev.currentTarget as HTMLElement
  const W = 220
  const H = 230
  menu.value = {
    x: Math.max(8, Math.min(ev.clientX, window.innerWidth - W - 8)),
    y: Math.max(8, Math.min(ev.clientY, window.innerHeight - H - 8)),
    date,
  }
  await nextTick()
  menuEl.value?.querySelector<HTMLElement>('[role="menuitem"]')?.focus()
}

function closeMenu(restoreFocus = false) {
  menu.value = null
  if (restoreFocus) menuReturnFocus?.focus()
}

async function addFromMenu(kind: Kind) {
  const date = menu.value?.date
  closeMenu()
  if (!date) return
  selected.value = date
  form.value = { id: null, title: '', kind, notes: '', repeat: kind === 'birthday', weekly: false, date }
  await nextTick()
  titleInput.value?.focus()
}

function onMenuKey(ev: KeyboardEvent) {
  const items = [...(menuEl.value?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])]
  const i = items.indexOf(document.activeElement as HTMLElement)
  if (ev.key === 'ArrowDown') items[(i + 1) % items.length]?.focus()
  else if (ev.key === 'ArrowUp') items[(i - 1 + items.length) % items.length]?.focus()
  else if (ev.key === 'Home') items[0]?.focus()
  else if (ev.key === 'End') items[items.length - 1]?.focus()
  else if (ev.key === 'Escape') {
    ev.stopPropagation()
    closeMenu(true)
    return
  } else if (ev.key === 'Tab') {
    closeMenu()
    return
  } else return
  ev.preventDefault()
}

function onOutside(ev: Event) {
  if (menu.value && !menuEl.value?.contains(ev.target as Node)) closeMenu()
}
const dismiss = () => closeMenu()

watch([view, year, month, weekStart], load)
onMounted(() => {
  load()
  document.addEventListener('pointerdown', onOutside)
  window.addEventListener('scroll', dismiss, true)
  window.addEventListener('resize', dismiss)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onOutside)
  window.removeEventListener('scroll', dismiss, true)
  window.removeEventListener('resize', dismiss)
})
</script>

<template>
  <div class="@container space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>

    <section class="bg-surface rounded-xl shadow p-4 border-t-4 border-slate-400">
      <!-- year / month pickers (2000-2100) and view switch -->
      <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div class="flex items-center gap-2">
          <label class="sr-only" :for="`cal-month-${view}`">{{ t('calendar.monthLabel') }}</label>
          <select :id="`cal-month-${view}`" v-model.number="month" :disabled="view === 'week'"
            class="border rounded-lg px-2 py-1 text-sm">
            <option v-for="(name, i) in monthNames" :key="i" :value="i + 1">{{ name }}</option>
          </select>
          <label class="sr-only" for="cal-year">{{ t('calendar.year') }}</label>
          <select id="cal-year" v-model.number="year" :disabled="view === 'week'" class="border rounded-lg px-2 py-1 text-sm">
            <option v-for="y in YEARS" :key="y" :value="y">{{ y }}</option>
          </select>
          <button type="button" @click="goToday"
            class="border border-slate-400 text-slate-600 rounded-lg px-3 py-1 text-sm hover:bg-slate-50">
            {{ t('calendar.today') }}
          </button>
        </div>
        <div class="flex gap-2">
          <button @click="setView('month')" :aria-pressed="view === 'month'"
            :class="['px-3 py-1 rounded-lg text-sm', view === 'month' ? 'bg-primary text-on-primary' : 'border border-slate-400 text-slate-600 hover:bg-slate-50']">
            {{ t('calendar.month') }}
          </button>
          <button @click="setView('week')" :aria-pressed="view === 'week'"
            :class="['px-3 py-1 rounded-lg text-sm', view === 'week' ? 'bg-primary text-on-primary' : 'border border-slate-400 text-slate-600 hover:bg-slate-50']">
            {{ t('calendar.week') }}
          </button>
        </div>
      </div>

      <div class="flex items-center justify-between mb-3">
        <button @click="shift(-1)" :disabled="!canPrev" :aria-label="t('calendar.prev')"
          class="px-3 py-1 rounded-lg hover:bg-slate-100 text-slate-600 disabled:opacity-30">‹</button>
        <h2 class="text-lg font-bold text-slate-800">{{ title }}</h2>
        <button @click="shift(1)" :disabled="!canNext" :aria-label="t('calendar.next')"
          class="px-3 py-1 rounded-lg hover:bg-slate-100 text-slate-600 disabled:opacity-30">›</button>
      </div>

      <div class="flex flex-wrap items-center gap-2 mb-3" role="group" :aria-label="t('calendar.layers.title')">
        <span class="text-xs text-slate-500">{{ t('calendar.layers.title') }}:</span>
        <button v-for="l in LAYER_DEFS" :key="l.key" type="button" :aria-pressed="layers[l.key]" @click="layers[l.key] = !layers[l.key]"
          :class="['rounded-full border px-3 py-1 text-xs flex items-center gap-1',
            layers[l.key] ? 'border-slate-700 bg-slate-100 font-semibold text-slate-900' : 'border-slate-300 text-slate-600 hover:bg-slate-50']">
          <span aria-hidden="true">{{ l.icon }}</span>{{ t(`calendar.layers.${l.key}`) }}
        </button>
        <select v-if="layers.holidays" v-model="layers.country" :aria-label="t('calendar.layers.country')" class="border rounded-lg px-2 py-1 text-xs max-w-44">
          <option v-if="!countryOptions.length" :value="layers.country">{{ countryName(layers.country) }}</option>
          <option v-for="o in countryOptions" :key="o.cc" :value="o.cc">{{ flagOf(o.cc) }} {{ o.name }}</option>
        </select>
      </div>

      <div class="flex flex-wrap items-center gap-2 mb-3 text-xs">
        <button type="button" @click="exportIcs" class="border border-slate-400 text-slate-700 rounded-lg px-3 py-1 hover:bg-slate-50">⬇ {{ t('calendar.ics.exportIcs') }}</button>
        <button type="button" @click="icsInput?.click()" class="border border-slate-400 text-slate-700 rounded-lg px-3 py-1 hover:bg-slate-50">⬆ {{ t('calendar.ics.importIcs') }}</button>
        <input ref="icsInput" type="file" accept=".ics,text/calendar" class="hidden" @change="importIcs" />
        <span v-if="icsMessage" role="status" class="text-ok">{{ icsMessage }}</span>
      </div>

      <template v-if="view === 'month'">
        <div class="grid grid-cols-7 gap-1 text-center text-xs text-slate-500 mb-1">
          <div v-for="w in WEEKDAYS" :key="w">{{ w }}</div>
        </div>
        <div class="grid grid-cols-7 gap-1">
          <template v-for="(c, i) in cells" :key="i">
            <div v-if="!c" />
            <button v-else @click="select(c.date)" @contextmenu="openMenu($event, c.date)" :aria-pressed="selected === c.date"
              :aria-label="fullDate(c.date)"
              :class="['h-14 rounded-lg border text-sm flex flex-col items-center justify-start pt-1 relative',
                selected === c.date ? 'border-slate-800 bg-slate-50' : 'border-transparent hover:bg-slate-50',
                c.date === todayIso ? 'font-bold text-teal-700' : 'text-slate-700']">
              <span>{{ c.day }}</span>
              <span v-if="isRest(c.date)" class="text-[0.7rem] leading-none" aria-hidden="true">🛌</span>
              <span v-if="dayGlyphs(c.date)" class="text-[0.6rem] leading-none text-slate-500" aria-hidden="true">{{ dayGlyphs(c.date) }}</span>
              <span v-if="byDateEvents.get(c.date)?.length" class="text-[0.7rem] leading-none mt-0.5" aria-hidden="true">
                {{ KIND_ICON[byDateEvents.get(c.date)![0].kind] }}<span v-if="byDateEvents.get(c.date)!.length > 1" class="text-slate-500">+{{ byDateEvents.get(c.date)!.length - 1 }}</span>
              </span>
              <span class="flex gap-0.5 mt-1" aria-hidden="true">
                <span v-for="cat in uniqueCategories(byDateEntries.get(c.date) ?? [])" :key="cat"
                  :class="['w-1.5 h-1.5 rounded-full', dotColor[cat]]" />
              </span>
            </button>
          </template>
        </div>
      </template>

      <div v-else class="grid grid-cols-1 @lg:grid-cols-7 gap-2">
        <button v-for="d in weekDays" :key="d.date" @click="select(d.date)" @contextmenu="openMenu($event, d.date)" :aria-pressed="selected === d.date"
          :aria-label="fullDate(d.date)"
          :class="['text-left rounded-lg border p-2 min-h-24',
            selected === d.date ? 'border-slate-800' : d.date === todayIso ? 'border-teal-500 bg-teal-50' : 'border-slate-200']">
          <p :class="['text-xs mb-1', d.date === todayIso ? 'font-bold text-teal-700' : 'text-slate-500']">{{ d.label }} {{ d.day }} <span v-if="isRest(d.date)" aria-hidden="true">🛌</span> <span class="text-[0.6rem]" aria-hidden="true">{{ dayGlyphs(d.date) }}</span></p>
          <ul class="space-y-0.5">
            <li v-for="ev in byDateEvents.get(d.date) ?? []" :key="ev.id + d.date" class="text-xs text-slate-700 break-words">
              <span aria-hidden="true">{{ KIND_ICON[ev.kind] }}</span> {{ ev.title }}
            </li>
            <li v-for="e in byDateEntries.get(d.date) ?? []" :key="e.habit_id" class="flex items-start gap-1.5 text-xs text-slate-700">
              <span :class="['w-2 h-2 rounded-full mt-1 shrink-0', dotColor[e.category]]" aria-hidden="true" />
              <span class="break-words">{{ e.habit_name }}</span>
            </li>
          </ul>
        </button>
      </div>
      <p class="text-xs text-slate-500 mt-3">{{ t('calendar.rightClickHint') }}</p>
    </section>

    <Teleport to="body">
      <div v-if="menu" id="calendar-context-menu" ref="menuEl" role="menu"
        :aria-label="t('calendar.addOn', { date: formatDate(menu.date) })"
        :style="{ left: menu.x + 'px', top: menu.y + 'px' }" @keydown="onMenuKey"
        class="fixed z-[3000] w-52 bg-surface border border-slate-300 rounded-lg shadow-lg py-1 text-sm">
        <p class="px-3 py-1 text-xs text-slate-500">{{ t('calendar.addOn', { date: formatDate(menu.date) }) }}</p>
        <button v-for="k in KINDS" :key="k" type="button" role="menuitem" tabindex="-1" @click="addFromMenu(k)"
          class="w-full flex items-center gap-2 px-3 py-1.5 text-left text-slate-700 hover:bg-slate-50 focus-visible:bg-slate-100">
          <span aria-hidden="true">{{ KIND_ICON[k] }}</span> {{ t(`calendar.kinds.${k}`) }}
        </button>
      </div>
    </Teleport>

    <!-- what the switched-on calendars say about the chosen day -->
    <section v-if="selected && (journalFor(selected) || holidaysFor(selected).length || nameDaysFor(selected).length || nationalFor(selected).length || historyFor(selected).length)"
      class="bg-surface rounded-xl shadow p-4 space-y-3 border-t-4 border-sky-500">
      <div v-if="journalFor(selected)">
        <h4 class="text-sm font-bold text-slate-800">📓 {{ t('calendar.layers.journal') }}</h4>
        <p class="text-sm text-slate-700">{{ t('calendar.journalDay', { entries: journalFor(selected)!.entries, recordings: journalFor(selected)!.recordings }) }}</p>
      </div>
      <div v-if="holidaysFor(selected).length">
        <h4 class="text-sm font-bold text-slate-800">🏛 {{ t('calendar.layers.holidays') }} · {{ countryName(layers.country) }}</h4>
        <ul class="text-sm text-slate-700 list-disc pl-5"><li v-for="h in holidaysFor(selected)" :key="h">{{ h }}</li></ul>
      </div>
      <div v-if="nameDaysFor(selected).length">
        <h4 class="text-sm font-bold text-slate-800">✝ {{ t('calendar.layers.nameDays') }}</h4>
        <p class="text-sm text-slate-700">{{ nameDaysFor(selected).join(', ') }}</p>
      </div>
      <div v-if="nationalFor(selected).length">
        <h4 class="text-sm font-bold text-slate-800">🏳 {{ t('calendar.layers.national') }}</h4>
        <p class="text-sm text-slate-700">{{ nationalFor(selected).map((cc) => `${flagOf(cc)} ${countryName(cc)}`).join(' · ') }}</p>
      </div>
      <div v-if="historyFor(selected).length">
        <h4 class="text-sm font-bold text-slate-800">📜 {{ t('calendar.layers.history') }}</h4>
        <ul class="text-sm text-slate-700 space-y-1">
          <li v-for="(h, i) in historyFor(selected)" :key="i">
            <b v-if="h.year" class="tabular-nums">{{ formatYear(h.year) }}</b>
            <span class="text-xs text-slate-500"> {{ h.kind === 'fact' ? '· ' + t('calendar.layers.funFact') : '' }}</span>
            — {{ historyText(h) }}
          </li>
        </ul>
      </div>
    </section>

    <!-- the chosen day: habits done, notes, and the note form -->
    <section v-if="selected" class="bg-surface rounded-xl shadow p-4 space-y-3" aria-live="polite">
      <div class="flex items-start justify-between gap-2">
        <h3 class="font-bold text-slate-800">{{ fullDate(selected) }}</h3>
        <div class="flex flex-wrap justify-end gap-2">
          <button v-if="canRest(selected)" @click="toggleRest(selected)" :aria-pressed="isRest(selected)"
            class="border border-slate-400 text-slate-700 rounded-lg px-3 py-1 text-sm hover:bg-slate-50 shrink-0">
            🛌 {{ isRest(selected) ? t('calendar.clearRest') : t('calendar.markRest') }}
          </button>
          <button v-if="!form" @click="startNew"
            class="bg-primary text-on-primary rounded-lg px-3 py-1 text-sm hover:bg-primary-hover shrink-0">
            + {{ t('calendar.addNote') }}
          </button>
        </div>
      </div>
      <p v-if="isRest(selected)" class="text-xs text-slate-500">{{ t('calendar.restHint') }}</p>

      <ul v-if="selectedEvents.length" class="space-y-2">
        <li v-for="ev in selectedEvents" :key="ev.id" class="flex items-start gap-2 text-sm text-slate-700">
          <span class="text-lg leading-none" aria-hidden="true">{{ KIND_ICON[ev.kind] }}</span>
          <div class="flex-1 min-w-0">
            <p class="font-medium break-words">
              {{ ev.title }}
              <span v-if="ev.repeat_yearly" class="text-xs font-normal text-slate-500">· {{ t('calendar.yearly') }}</span>
              <span v-if="ev.repeat_weekly" class="text-xs font-normal text-slate-500">· {{ t('calendar.weekly') }}</span>
            </p>
            <p v-if="ev.notes" class="text-xs text-slate-500 break-words whitespace-pre-line">{{ ev.notes }}</p>
          </div>
          <button @click="startEdit(ev)" :aria-label="t('home.edit')" :title="t('home.edit')"
            class="w-7 h-7 inline-flex items-center justify-center rounded text-slate-500 hover:text-slate-900 hover:bg-slate-100">✎</button>
          <button @click="removeEvent(ev)" :aria-label="t('home.remove')" :title="t('home.remove')"
            class="w-7 h-7 inline-flex items-center justify-center rounded text-slate-500 hover:text-danger hover:bg-slate-100">✕</button>
        </li>
      </ul>

      <ul v-if="selectedEntries.length" class="space-y-1">
        <li v-for="e in selectedEntries" :key="e.habit_id" class="flex items-center gap-2 text-sm text-slate-700">
          <span :class="['w-2 h-2 rounded-full', dotColor[e.category]]" aria-hidden="true" />
          {{ e.habit_name }}
        </li>
      </ul>

      <p v-if="!selectedEvents.length && !selectedEntries.length && !form" class="text-slate-500 text-sm">{{ t('calendar.nothing') }}</p>

      <form v-if="form" @submit.prevent="save" class="space-y-2 border-t border-slate-200 pt-3">
        <input ref="titleInput" v-model="form.title" type="text" maxlength="100" required
          :placeholder="t('calendar.titlePlaceholder')" :aria-label="t('calendar.titlePlaceholder')"
          class="w-full border rounded-lg px-3 py-2 text-sm" />
        <div class="flex flex-wrap gap-2">
          <label class="text-xs text-slate-600 flex-1 min-w-32">
            {{ t('calendar.kind') }}
            <select v-model="form.kind" class="mt-1 border rounded-lg px-2 py-1.5 text-sm w-full">
              <option v-for="k in KINDS" :key="k" :value="k">{{ KIND_ICON[k] }} {{ t(`calendar.kinds.${k}`) }}</option>
            </select>
          </label>
          <div class="text-xs text-slate-600 flex-1 min-w-52">
            <span>{{ t('wellness.date') }}</span>
            <DateField v-model="form.date" min="1900-01-01" max="2100-12-31" :label="t('wellness.date')" required class="mt-1" />
          </div>
        </div>
        <textarea v-model="form.notes" rows="2" maxlength="500"
          :placeholder="t('calendar.details')" :aria-label="t('calendar.details')"
          class="w-full border rounded-lg px-3 py-2 text-sm"></textarea>
        <div class="flex flex-wrap gap-x-5 gap-y-1">
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="form.repeat" type="checkbox" class="h-4 w-4" @change="form!.weekly = false" />
            {{ t('calendar.repeatYearly') }}
          </label>
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="form.weekly" type="checkbox" class="h-4 w-4" @change="form!.repeat = false" />
            {{ t('calendar.repeatWeekly') }}
          </label>
        </div>
        <div class="flex gap-2">
          <button type="submit" :disabled="busy"
            class="bg-primary text-on-primary rounded-lg px-4 py-1.5 text-sm hover:bg-primary-hover disabled:opacity-50">
            {{ t('common.save') }}
          </button>
          <button type="button" @click="form = null"
            class="border border-slate-400 text-slate-600 rounded-lg px-4 py-1.5 text-sm hover:bg-slate-50">
            {{ t('common.cancel') }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>
