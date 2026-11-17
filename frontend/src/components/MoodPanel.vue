<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { formatDate, toIso } from '../i18n/dates'
import { moodFill } from '../mood'
import { MOOD_STYLES, useSettingsStore, type MoodStyle } from '../stores/settings'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'
import DateField from './DateField.vue'
import MoodMark from './MoodMark.vue'

// Daily mood from 1 to 10, shown as emoji, colours or words (your choice, saved to your account).
interface MoodDay { date: string; score: number; note: string | null }
interface Summary { days: MoodDay[]; today: number | null; avg_7d: number | null; avg_30d: number | null; logged_total: number }

const { t } = useI18n()
const settings = useSettingsStore()
const badges = useBadgesStore()

const SCORES = Array.from({ length: 10 }, (_, i) => i + 1)
const STYLE_ICON: Record<MoodStyle, string> = { emoji: '😊', colors: '🎨', words: 'Aa' }
const BACKFILL_DAYS = 365

const todayDate = new Date()
const today = toIso(todayDate)
const earliest = toIso(new Date(todayDate.getFullYear(), todayDate.getMonth(), todayDate.getDate() - BACKFILL_DAYS))

const summary = ref<Summary | null>(null)
const date = ref(today)
const score = ref<number | null>(null)
const note = ref('')
const error = ref('')
const message = ref('')
const busy = ref(false)

const byDate = computed(() => new Map((summary.value?.days ?? []).map((d) => [d.date, d])))

// last 30 days, oldest first, for the bar chart
const chart = computed(() => {
  const out: { date: string; score: number | null }[] = []
  for (let i = 29; i >= 0; i--) {
    const day = toIso(new Date(todayDate.getFullYear(), todayDate.getMonth(), todayDate.getDate() - i))
    out.push({ date: day, score: byDate.value.get(day)?.score ?? null })
  }
  return out
})

function pickDay(day: string) {
  date.value = day
  const existing = byDate.value.get(day)
  score.value = existing?.score ?? null
  note.value = existing?.note ?? ''
  message.value = ''
}

async function load() {
  try {
    const { data } = await api.get<Summary>('/api/mood', { params: { days: 90 } })
    summary.value = data
    pickDay(date.value)
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function save() {
  if (score.value === null || !date.value) return
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const { data } = await api.put<{ new_badges: BadgeInfo[] }>('/api/mood', { score: score.value, log_date: date.value, note: note.value || null })
    message.value = t('mood.saved')
    await badges.announce(data.new_badges)
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  } finally {
    busy.value = false
  }
}

async function remove(day: string) {
  if (!confirm(t('mood.confirmDelete', { date: formatDate(day) }))) return
  try {
    await api.delete(`/api/mood/${day}`)
    if (date.value === day) {
      score.value = null
      note.value = ''
    }
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
    <p v-if="message" role="status" class="text-ok text-sm font-medium">{{ message }}</p>

    <section v-if="summary" class="grid grid-cols-3 gap-3 text-center">
      <div class="bg-surface rounded-xl shadow p-3 border-t-4 border-purple-500">
        <p class="text-xs text-slate-500">{{ t('mood.today') }}</p>
        <div class="min-h-10 flex items-center justify-center">
          <MoodMark v-if="summary.today" :score="summary.today" :style-kind="settings.moodStyle" />
          <span v-else class="text-slate-500">—</span>
        </div>
      </div>
      <div class="bg-surface rounded-xl shadow p-3">
        <p class="text-xs text-slate-500">{{ t('mood.avg7') }}</p>
        <p class="text-xl font-bold text-slate-800 tabular-nums">{{ summary.avg_7d ?? '—' }}</p>
      </div>
      <div class="bg-surface rounded-xl shadow p-3">
        <p class="text-xs text-slate-500">{{ t('mood.avg30') }}</p>
        <p class="text-xl font-bold text-slate-800 tabular-nums">{{ summary.avg_30d ?? '—' }}</p>
      </div>
    </section>

    <section class="bg-surface rounded-xl shadow p-4 space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h3 class="font-bold text-slate-800">{{ t('mood.question') }}</h3>
        <DateField :model-value="date" @update:model-value="(v: string) => v && pickDay(v)" :min="earliest" :max="today" :label="t('wellness.date')" required />
      </div>

      <!-- how the scale looks: your choice -->
      <div role="radiogroup" :aria-label="t('mood.style')" class="flex items-center gap-1 text-xs">
        <span class="text-slate-500 mr-1">{{ t('mood.style') }}</span>
        <button v-for="s in MOOD_STYLES" :key="s" type="button" role="radio" :aria-checked="settings.moodStyle === s"
          @click="settings.setMoodStyle(s)"
          :class="['rounded-full border px-3 py-1', settings.moodStyle === s ? 'border-slate-800 bg-slate-100 font-semibold text-slate-900' : 'border-slate-300 text-slate-600 hover:bg-slate-50']">
          <span aria-hidden="true">{{ STYLE_ICON[s] }}</span> {{ t(`mood.styles.${s}`) }}
        </button>
      </div>

      <div role="radiogroup" :aria-label="t('mood.question')"
        :class="['grid gap-2', settings.moodStyle === 'words' ? 'grid-cols-2 sm:grid-cols-5' : 'grid-cols-5']">
        <button v-for="n in SCORES" :key="n" type="button" role="radio" :aria-checked="score === n"
          :aria-label="`${n}: ${t(`mood.words.${n}`)}`" :title="`${n}: ${t(`mood.words.${n}`)}`" @click="score = n"
          :class="['rounded-lg border p-1.5 flex flex-col items-center gap-0.5 transition-transform',
            score === n ? 'border-slate-800 bg-slate-50 scale-105 ring-2 ring-slate-800' : 'border-slate-200 hover:bg-slate-50']">
          <MoodMark :score="n" :style-kind="settings.moodStyle" />
          <span class="text-[0.7rem] text-slate-500 tabular-nums">{{ n }}</span>
        </button>
      </div>

      <input v-model="note" type="text" maxlength="200" :placeholder="t('mood.notePlaceholder')" :aria-label="t('mood.notePlaceholder')"
        class="w-full border rounded-lg px-3 py-2 text-sm" />
      <button @click="save" :disabled="score === null || !date || busy"
        class="bg-primary text-on-primary rounded-lg px-4 py-1.5 text-sm hover:bg-primary-hover disabled:opacity-50">
        {{ t('common.save') }}
      </button>
    </section>

    <section v-if="summary" class="bg-surface rounded-xl shadow p-4">
      <h3 class="font-bold text-slate-800 mb-2">{{ t('mood.last30') }}</h3>
      <div class="flex items-end gap-0.5 h-24" role="img" :aria-label="t('mood.chartLabel', { n: summary.days.length })">
        <button v-for="c in chart" :key="c.date" type="button" @click="pickDay(c.date)"
          :title="c.score ? `${formatDate(c.date)}: ${c.score} — ${t(`mood.words.${c.score}`)}` : formatDate(c.date)"
          class="flex-1 min-w-0 h-full flex items-end rounded-sm hover:bg-slate-100" :aria-label="formatDate(c.date)">
          <span class="block w-full rounded-sm"
            :style="{ height: c.score ? c.score * 10 + '%' : '4%', background: c.score ? moodFill(c.score) : 'var(--color-slate-200)' }" />
        </button>
      </div>

      <ul v-if="summary.days.length" class="divide-y mt-3">
        <li v-for="d in summary.days.slice(0, 14)" :key="d.date" class="py-2 flex items-center gap-3 text-sm">
          <MoodMark :score="d.score" :style-kind="settings.moodStyle" size="sm" />
          <div class="flex-1 min-w-0">
            <p class="font-medium text-slate-800">{{ formatDate(d.date) }}</p>
            <p v-if="d.note" class="text-xs text-slate-500 break-words">{{ d.note }}</p>
          </div>
          <button @click="pickDay(d.date)" :aria-label="t('home.edit')" :title="t('home.edit')"
            class="w-7 h-7 inline-flex items-center justify-center rounded text-slate-500 hover:text-slate-900 hover:bg-slate-100">✎</button>
          <button @click="remove(d.date)" :aria-label="t('home.remove')" :title="t('home.remove')"
            class="w-7 h-7 inline-flex items-center justify-center rounded text-slate-500 hover:text-danger hover:bg-slate-100">✕</button>
        </li>
      </ul>
      <p v-else class="text-sm text-slate-500 mt-2">{{ t('mood.empty') }}</p>
    </section>
  </div>
</template>
