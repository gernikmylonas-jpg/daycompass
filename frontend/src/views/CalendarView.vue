<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import axios from 'axios'
import api from '../api'
import type { Category } from '../stores/habits'

interface Entry {
  date: string
  habit_id: string
  habit_name: string
  category: Category
}

const MONTHS = [
  'Ιανουάριος', 'Φεβρουάριος', 'Μάρτιος', 'Απρίλιος', 'Μάιος', 'Ιούνιος',
  'Ιούλιος', 'Αύγουστος', 'Σεπτέμβριος', 'Οκτώβριος', 'Νοέμβριος', 'Δεκέμβριος',
]
const MONTHS_SHORT = ['Ιαν', 'Φεβ', 'Μαρ', 'Απρ', 'Μαΐ', 'Ιουν', 'Ιουλ', 'Αυγ', 'Σεπ', 'Οκτ', 'Νοε', 'Δεκ']
const WEEKDAYS = ['Δευ', 'Τρί', 'Τετ', 'Πέμ', 'Παρ', 'Σάβ', 'Κυρ']

const dotColor: Record<Category, string> = {
  body: 'bg-teal-500',
  work: 'bg-orange-500',
  schedule: 'bg-pink-500',
  mind: 'bg-purple-500',
}

function iso(y: number, m: number, d: number) {
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

function parse(s: string) {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function toIso(d: Date) {
  return iso(d.getFullYear(), d.getMonth() + 1, d.getDate())
}

function addDays(s: string, n: number) {
  const d = parse(s)
  d.setDate(d.getDate() + n)
  return toIso(d)
}

function mondayOf(d: Date) {
  const copy = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  copy.setDate(copy.getDate() - ((copy.getDay() + 6) % 7))
  return toIso(copy)
}

const now = new Date()
const todayIso = toIso(now)

const view = ref<'month' | 'week'>('month')
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)
const weekStart = ref(mondayOf(now))
const entries = ref<Entry[]>([])
const selected = ref<string | null>(null)
const error = ref('')

const byDate = computed(() => {
  const map = new Map<string, Entry[]>()
  for (const e of entries.value) {
    const list = map.get(e.date) ?? []
    list.push(e)
    map.set(e.date, list)
  }
  return map
})

const cells = computed(() => {
  const firstWeekday = (new Date(year.value, month.value - 1, 1).getDay() + 6) % 7
  const daysInMonth = new Date(year.value, month.value, 0).getDate()
  const result: ({ day: number; date: string } | null)[] = []
  for (let i = 0; i < firstWeekday; i++) result.push(null)
  for (let d = 1; d <= daysInMonth; d++) {
    result.push({ day: d, date: iso(year.value, month.value, d) })
  }
  return result
})

const weekDays = computed(() =>
  WEEKDAYS.map((label, i) => {
    const date = addDays(weekStart.value, i)
    return { label, date, day: parse(date).getDate() }
  }),
)

const title = computed(() => {
  if (view.value === 'month') return `${MONTHS[month.value - 1]} ${year.value}`
  const a = parse(weekStart.value)
  const b = parse(addDays(weekStart.value, 6))
  return `${a.getDate()} ${MONTHS_SHORT[a.getMonth()]} – ${b.getDate()} ${MONTHS_SHORT[b.getMonth()]} ${b.getFullYear()}`
})

const selectedEntries = computed(() =>
  selected.value ? (byDate.value.get(selected.value) ?? []) : [],
)

function currentRange(): [string, string] {
  if (view.value === 'week') return [weekStart.value, addDays(weekStart.value, 6)]
  const last = new Date(year.value, month.value, 0).getDate()
  return [iso(year.value, month.value, 1), iso(year.value, month.value, last)]
}

async function load() {
  error.value = ''
  const [start, end] = currentRange()
  try {
    const { data } = await api.get<Entry[]>('/api/stats/calendar-range', {
      params: { start, end },
    })
    entries.value = data
  } catch (e) {
    error.value = axios.isAxiosError(e)
      ? (e.response?.data?.detail ?? 'Κάτι πήγε στραβά')
      : 'Κάτι πήγε στραβά'
  }
}

function setView(v: 'month' | 'week') {
  if (v === view.value) return
  selected.value = null
  if (v === 'week') {
    const showingCurrentMonth = year.value === now.getFullYear() && month.value === now.getMonth() + 1
    weekStart.value = showingCurrentMonth
      ? mondayOf(now)
      : mondayOf(new Date(year.value, month.value - 1, 1))
  } else {
    const d = parse(weekStart.value)
    year.value = d.getFullYear()
    month.value = d.getMonth() + 1
  }
  view.value = v
}

function shift(delta: number) {
  selected.value = null
  if (view.value === 'week') {
    weekStart.value = addDays(weekStart.value, delta * 7)
    return
  }
  let m = month.value + delta
  let y = year.value
  if (m < 1) { m = 12; y-- }
  if (m > 12) { m = 1; y++ }
  month.value = m
  year.value = y
}

function uniqueCategories(list: Entry[]) {
  return [...new Set(list.map((e) => e.category))]
}

watch([view, year, month, weekStart], load)
onMounted(load)
</script>

<template>
  <div class="min-h-screen bg-slate-100 p-4 md:p-8">
    <div class="max-w-4xl mx-auto">
      <header class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-slate-800">Ημερολόγιο</h1>
        <RouterLink to="/"
          class="bg-slate-800 text-white rounded-lg px-4 py-2 text-sm hover:bg-slate-700">
          ← Πυξίδα
        </RouterLink>
      </header>

      <p v-if="error" class="text-red-600 text-sm mb-4">{{ error }}</p>

      <section class="bg-white rounded-xl shadow p-4">
        <div class="flex justify-center gap-2 mb-4">
          <button @click="setView('month')"
            :class="['px-4 py-1 rounded-lg text-sm', view === 'month' ? 'bg-slate-800 text-white' : 'border border-slate-300 text-slate-600 hover:bg-slate-50']">
            Μήνας
          </button>
          <button @click="setView('week')"
            :class="['px-4 py-1 rounded-lg text-sm', view === 'week' ? 'bg-slate-800 text-white' : 'border border-slate-300 text-slate-600 hover:bg-slate-50']">
            Εβδομάδα
          </button>
        </div>

        <div class="flex items-center justify-between mb-4">
          <button @click="shift(-1)" class="px-3 py-1 rounded-lg hover:bg-slate-100 text-slate-600">‹</button>
          <h2 class="text-lg font-bold text-slate-800">{{ title }}</h2>
          <button @click="shift(1)" class="px-3 py-1 rounded-lg hover:bg-slate-100 text-slate-600">›</button>
        </div>

        <template v-if="view === 'month'">
          <div class="grid grid-cols-7 gap-1 text-center text-xs text-slate-500 mb-1">
            <div v-for="w in WEEKDAYS" :key="w">{{ w }}</div>
          </div>

          <div class="grid grid-cols-7 gap-1">
            <template v-for="(c, i) in cells" :key="i">
              <div v-if="!c" />
              <button v-else @click="selected = c.date"
                :class="['h-14 rounded-lg border text-sm flex flex-col items-center justify-start pt-1',
                  selected === c.date ? 'border-slate-800 bg-slate-50' : 'border-transparent hover:bg-slate-50',
                  c.date === todayIso ? 'font-bold text-teal-700' : 'text-slate-700']">
                <span>{{ c.day }}</span>
                <span class="flex gap-0.5 mt-1">
                  <span v-for="cat in uniqueCategories(byDate.get(c.date) ?? [])" :key="cat"
                    :class="['w-1.5 h-1.5 rounded-full', dotColor[cat]]" />
                </span>
              </button>
            </template>
          </div>
        </template>

        <div v-else class="grid grid-cols-1 md:grid-cols-7 gap-2">
          <div v-for="d in weekDays" :key="d.date"
            :class="['rounded-lg border p-2 min-h-32', d.date === todayIso ? 'border-teal-500 bg-teal-50' : 'border-slate-200']">
            <p :class="['text-xs mb-2', d.date === todayIso ? 'font-bold text-teal-700' : 'text-slate-500']">
              {{ d.label }} {{ d.day }}
            </p>
            <ul class="space-y-1">
              <li v-for="e in byDate.get(d.date) ?? []" :key="e.habit_id"
                class="flex items-start gap-1.5 text-xs text-slate-700">
                <span :class="['w-2 h-2 rounded-full mt-1 shrink-0', dotColor[e.category]]" />
                <span>{{ e.habit_name }}</span>
              </li>
              <li v-if="!(byDate.get(d.date)?.length)" class="text-xs text-slate-300">—</li>
            </ul>
          </div>
        </div>
      </section>

      <section v-if="view === 'month' && selected" class="bg-white rounded-xl shadow p-4 mt-4">
        <h3 class="font-bold text-slate-800 mb-2">{{ selected }}</h3>
        <ul v-if="selectedEntries.length" class="space-y-1">
          <li v-for="e in selectedEntries" :key="e.habit_id" class="flex items-center gap-2 text-sm text-slate-700">
            <span :class="['w-2 h-2 rounded-full', dotColor[e.category]]" />
            {{ e.habit_name }}
          </li>
        </ul>
        <p v-else class="text-slate-400 text-sm">Κανένα check-in αυτή τη μέρα.</p>
      </section>
    </div>
  </div>
</template>
