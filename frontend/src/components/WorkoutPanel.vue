<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { formatDate, toIso } from '../i18n/dates'
import DateField from './DateField.vue'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'

// Log workouts (kind, minutes, optional note). They add up per week and per kind; nothing is created unless you log it.
interface Item { id: string; date: string; kind: string; minutes: number; note: string | null }
interface Data { week_minutes: number; week_sessions: number; total_minutes: number; total_sessions: number; by_kind: Record<string, number>; items: Item[] }
const KINDS = ['walk', 'run', 'cycle', 'swim', 'gym', 'yoga', 'sport', 'other']
const ICON: Record<string, string> = { walk: '🚶', run: '🏃', cycle: '🚴', swim: '🏊', gym: '🏋️', yoga: '🧘', sport: '⚽', other: '✨' }
const { t } = useI18n()
const badges = useBadgesStore()
const today = toIso(new Date())
const data = ref<Data | null>(null)
const error = ref('')
const form = ref({ kind: 'walk', minutes: 30 as number | null, date: today, note: '' })
const hours = (m: number) => t('wellness.duration', { h: Math.floor(m / 60), m: m % 60 })
const kinds = computed(() => Object.entries(data.value?.by_kind ?? {}).sort((a, b) => b[1] - a[1]))
const maxKind = computed(() => Math.max(1, ...kinds.value.map(([, m]) => m)))

async function load() {
  try {
    data.value = (await api.get<Data>('/api/workouts')).data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
async function add() {
  error.value = ''
  if (!form.value.minutes) return
  try {
    const { data: saved } = await api.post<{ new_badges?: BadgeInfo[] }>('/api/workouts', { kind: form.value.kind, minutes: form.value.minutes, workout_date: form.value.date, note: form.value.note || null })
    await badges.announce(saved.new_badges)
    form.value.note = ''
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
async function remove(i: Item) {
  if (!confirm(t('wellness.confirmDelete', { date: formatDate(i.date) }))) return
  try {
    await api.delete(`/api/workouts/${i.id}`)
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
    <section v-if="data" class="grid grid-cols-2 gap-3 text-center">
      <div class="bg-surface rounded-xl shadow p-3 border-t-4 border-orange-500"><p class="text-xs text-slate-500">{{ t('workouts.thisWeek') }}</p><p class="text-xl font-bold text-slate-800">{{ hours(data.week_minutes) }}</p><p class="text-xs text-slate-500">{{ t('workouts.sessions', data.week_sessions) }}</p></div>
      <div class="bg-surface rounded-xl shadow p-3"><p class="text-xs text-slate-500">{{ t('workouts.last90') }}</p><p class="text-xl font-bold text-slate-800">{{ hours(data.total_minutes) }}</p><p class="text-xs text-slate-500">{{ t('workouts.sessions', data.total_sessions) }}</p></div>
    </section>

    <section class="bg-surface rounded-xl shadow p-4 space-y-3">
      <h3 class="font-bold text-slate-800">{{ t('workouts.log') }}</h3>
      <form @submit.prevent="add" class="space-y-2">
        <div class="flex flex-wrap gap-2">
          <select v-model="form.kind" :aria-label="t('workouts.kind')" class="border rounded-lg px-2 py-1.5 text-sm">
            <option v-for="k in KINDS" :key="k" :value="k">{{ ICON[k] }} {{ t(`workouts.kinds.${k}`) }}</option>
          </select>
          <input v-model.number="form.minutes" type="number" min="1" max="600" required :aria-label="t('workouts.minutes')" class="border rounded-lg px-2 py-1.5 text-sm w-24" />
          <span class="self-center text-sm text-slate-600">{{ t('workouts.min') }}</span>
          <DateField v-model="form.date" min="2000-01-01" :max="today" :label="t('wellness.date')" required />
        </div>
        <div class="flex gap-2">
          <input v-model="form.note" type="text" maxlength="200" :placeholder="t('workouts.note')" :aria-label="t('workouts.note')" class="flex-1 min-w-0 border rounded-lg px-3 py-1.5 text-sm" />
          <button type="submit" class="bg-primary text-on-primary rounded-lg px-4 text-sm hover:bg-primary-hover">{{ t('common.save') }}</button>
        </div>
      </form>
    </section>

    <section v-if="kinds.length" class="bg-surface rounded-xl shadow p-4 space-y-2">
      <h3 class="font-bold text-slate-800">{{ t('workouts.byKind') }}</h3>
      <div v-for="[k, m] in kinds" :key="k" class="text-sm">
        <div class="flex justify-between text-slate-700"><span>{{ ICON[k] }} {{ t(`workouts.kinds.${k}`) }}</span><span class="tabular-nums">{{ hours(m) }}</span></div>
        <div class="h-1.5 rounded bg-slate-100 overflow-hidden"><div class="h-full bg-orange-500" :style="{ width: (m / maxKind) * 100 + '%' }"></div></div>
      </div>
    </section>

    <section v-if="data && data.items.length" class="bg-surface rounded-xl shadow p-4">
      <h3 class="font-bold text-slate-800 mb-2">{{ t('wellness.history') }}</h3>
      <ul class="divide-y text-sm">
        <li v-for="i in data.items.slice(0, 20)" :key="i.id" class="py-1.5 flex items-center justify-between gap-2 text-slate-700">
          <span class="min-w-0"><span aria-hidden="true">{{ ICON[i.kind] }}</span> {{ t(`workouts.kinds.${i.kind}`) }} · {{ i.minutes }} {{ t('workouts.min') }}<span class="text-xs text-slate-500"> · {{ formatDate(i.date) }}</span><span v-if="i.note" class="block text-xs text-slate-500 break-words">{{ i.note }}</span></span>
          <button @click="remove(i)" :aria-label="t('home.remove')" :title="t('home.remove')" class="w-6 h-6 shrink-0 inline-flex items-center justify-center rounded text-slate-500 hover:text-danger hover:bg-slate-100">✕</button>
        </li>
      </ul>
    </section>
  </div>
</template>
