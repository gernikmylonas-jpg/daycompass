<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { formatDate, toIso } from '../i18n/dates'
import DateField from './DateField.vue'

// Personal goals with a deadline. Nothing exists until you create it.
interface Goal {
  id: string; title: string; metric: string; target: number; start_date: string; end_date: string
  progress: number; percent: number; status: 'active' | 'upcoming' | 'done' | 'missed'; days_left: number; needed_per_day: number | null
}
const METRICS = ['checkins', 'steps', 'meditation_minutes', 'pomodoros', 'sleep_nights', 'journal_entries', 'mood_logs']
const { t, locale } = useI18n()

const goals = ref<Goal[]>([])
const creating = ref(false)
const error = ref('')
const day = (offset: number) => { const d = new Date(); d.setDate(d.getDate() + offset); return toIso(d) }
const form = ref({ title: '', metric: 'steps', target: 20000, start: day(0), end: day(30) })
const num = (n: number) => n.toLocaleString(locale.value)

async function load() {
  try {
    goals.value = (await api.get<Goal[]>('/api/goals')).data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function create() {
  error.value = ''
  try {
    await api.post('/api/goals', { title: form.value.title, metric: form.value.metric, target: form.value.target, start_date: form.value.start, end_date: form.value.end })
    creating.value = false
    form.value.title = ''
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function remove(g: Goal) {
  if (!confirm(t('goals.confirmDelete'))) return
  try {
    await api.delete(`/api/goals/${g.id}`)
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

onMounted(load)
</script>

<template>
  <section class="bg-surface rounded-xl shadow p-4 space-y-3 border-t-4 border-teal-500">
    <div class="flex items-center justify-between gap-2">
      <h2 class="font-bold text-slate-800">{{ t('goals.title') }}</h2>
      <button type="button" @click="creating = !creating" :aria-expanded="creating"
        class="bg-primary text-on-primary rounded-lg px-3 py-1 text-sm hover:bg-primary-hover">+ {{ t('goals.new') }}</button>
    </div>
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>

    <form v-if="creating" @submit.prevent="create" class="rounded-lg border border-slate-200 p-3 space-y-2">
      <input v-model="form.title" type="text" maxlength="80" required :placeholder="t('goals.titlePlaceholder')" :aria-label="t('goals.titlePlaceholder')"
        class="w-full border rounded-lg px-3 py-2 text-sm" />
      <div class="flex flex-wrap gap-3 items-end">
        <label class="text-xs text-slate-600 flex-1 min-w-40">{{ t('challenges.metric') }}
          <select v-model="form.metric" class="mt-1 border rounded-lg px-2 py-1.5 text-sm w-full">
            <option v-for="m in METRICS" :key="m" :value="m">{{ t(`challenges.metrics.${m}`) }}</option>
          </select></label>
        <label class="text-xs text-slate-600 w-32">{{ t('challenges.target') }}
          <input v-model.number="form.target" type="number" min="1" required class="mt-1 border rounded-lg px-2 py-1.5 text-sm w-full" /></label>
      </div>
      <div class="flex flex-wrap gap-4 text-xs text-slate-600">
        <div><span>{{ t('challenges.start') }}</span><DateField v-model="form.start" min="2000-01-01" max="2100-12-31" :label="t('challenges.start')" required class="mt-1" /></div>
        <div><span>{{ t('goals.deadline') }}</span><DateField v-model="form.end" min="2000-01-01" max="2100-12-31" :label="t('goals.deadline')" required class="mt-1" /></div>
      </div>
      <div class="flex gap-2">
        <button type="submit" class="bg-primary text-on-primary rounded-lg px-4 py-1.5 text-sm hover:bg-primary-hover">{{ t('challenges.create') }}</button>
        <button type="button" @click="creating = false" class="border border-slate-400 text-slate-600 rounded-lg px-4 py-1.5 text-sm hover:bg-slate-50">{{ t('common.cancel') }}</button>
      </div>
    </form>

    <ul v-if="goals.length" class="space-y-3">
      <li v-for="g in goals" :key="g.id" class="rounded-lg border border-slate-200 p-3">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="font-medium text-slate-800 break-words">{{ g.title }}</p>
            <p class="text-xs text-slate-500">{{ t(`challenges.metrics.${g.metric}`) }} · {{ num(g.progress) }} / {{ num(g.target) }} · {{ t('goals.until', { date: formatDate(g.end_date) }) }}</p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span :class="['text-xs rounded-full border px-2 py-0.5', g.status === 'done' ? 'border-ok text-ok' : 'border-slate-300 text-slate-600']">{{ t(`goals.status.${g.status}`) }}</span>
            <button @click="remove(g)" :aria-label="t('home.remove')" :title="t('home.remove')" class="w-6 h-6 inline-flex items-center justify-center rounded text-slate-500 hover:text-danger hover:bg-slate-100">✕</button>
          </div>
        </div>
        <div class="mt-2 h-2 rounded bg-slate-100 overflow-hidden" role="progressbar" :aria-valuenow="g.percent" aria-valuemin="0" aria-valuemax="100" :aria-label="g.title">
          <div class="h-full" :class="g.status === 'done' ? 'bg-ok' : 'bg-teal-500'" :style="{ width: g.percent + '%' }"></div>
        </div>
        <p v-if="g.status === 'active'" class="text-xs text-slate-500 mt-1">
          {{ t('goals.daysLeft', g.days_left) }}<template v-if="g.needed_per_day"> · {{ t('goals.perDay', { n: num(g.needed_per_day) }) }}</template>
        </p>
      </li>
    </ul>
    <p v-else class="text-sm text-slate-500">{{ t('goals.none') }}</p>
  </section>
</template>
