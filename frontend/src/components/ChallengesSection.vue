<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { formatDate, toIso } from '../i18n/dates'
import DateField from './DateField.vue'

// Time-boxed challenges inside a group: every member has the same goal, measured from their own
// activity. Only the owner creates or deletes them; everyone sees everyone's progress.
interface Member { user_id: string; name: string; progress: number; done: boolean; is_me: boolean }
interface Challenge {
  id: string; title: string; metric: string; target: number; start_date: string; end_date: string
  status: 'upcoming' | 'active' | 'finished'; days_left: number; completed_count: number; members: Member[]
}

const METRICS = ['checkins', 'steps', 'meditation_minutes', 'pomodoros', 'sleep_nights', 'journal_entries', 'mood_logs']
const props = defineProps<{ groupId: string; isOwner: boolean }>()
const { t } = useI18n()

const challenges = ref<Challenge[]>([])
const error = ref('')
const creating = ref(false)

const day = (offset: number) => {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  return toIso(d)
}
const form = ref({ title: '', metric: 'checkins', target: 5, start: day(0), end: day(6) })

async function reload() {
  try {
    challenges.value = (await api.get<Challenge[]>(`/api/groups/${props.groupId}/challenges`)).data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function create() {
  if (!form.value.title.trim() || !form.value.start || !form.value.end) return
  error.value = ''
  try {
    await api.post(`/api/groups/${props.groupId}/challenges`, {
      title: form.value.title, metric: form.value.metric, target: form.value.target,
      start_date: form.value.start, end_date: form.value.end,
    })
    form.value.title = ''
    creating.value = false
    await reload()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function remove(c: Challenge) {
  if (!confirm(t('challenges.confirmDelete'))) return
  try {
    await api.delete(`/api/groups/${props.groupId}/challenges/${c.id}`)
    await reload()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

const percent = (m: Member, c: Challenge) => Math.min(100, Math.round((m.progress / c.target) * 100))

watch(() => props.groupId, reload, { immediate: true })
defineExpose({ reload })
</script>

<template>
  <section class="bg-surface rounded-xl shadow p-4 border-t-4 border-green-500 space-y-3">
    <div class="flex items-center justify-between gap-2">
      <h3 class="font-bold text-slate-800">{{ t('challenges.title') }}</h3>
      <button v-if="isOwner && !creating" @click="creating = true"
        class="bg-primary text-on-primary rounded-lg px-3 py-1 text-sm hover:bg-primary-hover">+ {{ t('challenges.new') }}</button>
    </div>
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>

    <form v-if="creating" @submit.prevent="create" class="space-y-2 rounded-lg border border-slate-200 p-3">
      <input v-model="form.title" type="text" maxlength="80" required :placeholder="t('challenges.titlePlaceholder')"
        :aria-label="t('challenges.titlePlaceholder')" class="w-full border rounded-lg px-3 py-2 text-sm" />
      <div class="flex flex-wrap gap-2">
        <label class="text-xs text-slate-600 flex-1 min-w-40">{{ t('challenges.metric') }}
          <select v-model="form.metric" class="mt-1 border rounded-lg px-2 py-1.5 text-sm w-full">
            <option v-for="m in METRICS" :key="m" :value="m">{{ t(`challenges.metrics.${m}`) }}</option>
          </select>
        </label>
        <label class="text-xs text-slate-600 w-32">{{ t('challenges.target') }}
          <input v-model.number="form.target" type="number" min="1" max="1000000" required class="mt-1 border rounded-lg px-2 py-1.5 text-sm w-full" />
        </label>
      </div>
      <div class="flex flex-wrap gap-3 text-xs text-slate-600">
        <div><span>{{ t('challenges.start') }}</span><DateField v-model="form.start" min="2000-01-01" max="2100-12-31" :label="t('challenges.start')" required class="mt-1" /></div>
        <div><span>{{ t('challenges.end') }}</span><DateField v-model="form.end" min="2000-01-01" max="2100-12-31" :label="t('challenges.end')" required class="mt-1" /></div>
      </div>
      <div class="flex gap-2">
        <button type="submit" class="bg-primary text-on-primary rounded-lg px-4 py-1.5 text-sm hover:bg-primary-hover">{{ t('challenges.create') }}</button>
        <button type="button" @click="creating = false" class="border border-slate-400 text-slate-600 rounded-lg px-4 py-1.5 text-sm hover:bg-slate-50">{{ t('common.cancel') }}</button>
      </div>
    </form>

    <ul v-if="challenges.length" class="space-y-4">
      <li v-for="c in challenges" :key="c.id" class="space-y-2">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="font-semibold text-slate-800 break-words">{{ c.title }}</p>
            <p class="text-xs text-slate-500">
              {{ t(`challenges.metrics.${c.metric}`) }} · {{ t('challenges.goal', { n: c.target.toLocaleString() }) }}<br />
              {{ formatDate(c.start_date) }} – {{ formatDate(c.end_date) }} ·
              <span :class="c.status === 'active' ? 'text-ok font-medium' : ''">{{ t(`challenges.status.${c.status}`) }}</span>
              <template v-if="c.status !== 'finished'"> · {{ t('challenges.daysLeft', c.days_left) }}</template>
            </p>
          </div>
          <button v-if="isOwner" @click="remove(c)" :aria-label="t('home.remove')" :title="t('home.remove')"
            class="w-7 h-7 inline-flex items-center justify-center rounded text-slate-500 hover:text-danger hover:bg-slate-100 shrink-0">✕</button>
        </div>
        <ul class="space-y-1.5">
          <li v-for="m in c.members" :key="m.user_id" class="text-sm">
            <div class="flex justify-between gap-2" :class="m.is_me ? 'font-semibold text-slate-900' : 'text-slate-700'">
              <span class="truncate">{{ m.name }}<span v-if="m.is_me" class="text-slate-500 font-normal"> ({{ t('groups.you') }})</span></span>
              <span class="tabular-nums text-xs">{{ m.progress.toLocaleString() }} / {{ c.target.toLocaleString() }} <span v-if="m.done" class="text-ok" aria-hidden="true">✓</span></span>
            </div>
            <div class="h-1.5 rounded bg-slate-100 overflow-hidden" role="progressbar" :aria-valuenow="percent(m, c)" aria-valuemin="0" aria-valuemax="100" :aria-label="m.name">
              <div class="h-full" :class="m.done ? 'bg-green-500' : 'bg-sky-500'" :style="{ width: percent(m, c) + '%' }" />
            </div>
          </li>
        </ul>
        <p class="text-xs text-slate-500">{{ t('challenges.completed', { n: c.completed_count, total: c.members.length }) }}</p>
      </li>
    </ul>
    <p v-else class="text-sm text-slate-500">{{ isOwner ? t('challenges.none') : t('challenges.noneMember') }}</p>
  </section>
</template>
