<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import BadgesPanel from '../components/BadgesPanel.vue'
import BadgeToast from '../components/BadgeToast.vue'

interface Source {
  count: number
  points: number
}

interface Breakdown {
  total: number
  check_ins: Source
  pomodoros: Source
  steps: Source
  sleep: Source
  other: number
}

const { t } = useI18n()
const data = ref<Breakdown | null>(null)
const error = ref('')

const rows = computed(() => {
  const d = data.value
  if (!d) return []
  const list = [
    { key: 'checkIns', icon: '✅', count: d.check_ins.count, points: d.check_ins.points },
    { key: 'pomodoros', icon: '🍅', count: d.pomodoros.count, points: d.pomodoros.points },
    { key: 'steps', icon: '👟', count: d.steps.count, points: d.steps.points },
    { key: 'sleep', icon: '😴', count: d.sleep.count, points: d.sleep.points },
  ]
  return d.other !== 0 ? [...list, { key: 'other', icon: '🧭', count: null, points: d.other }] : list
})

onMounted(async () => {
  try {
    data.value = (await api.get<Breakdown>('/api/stats/points')).data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
})
</script>

<template>
  <div class="min-h-[calc(100vh-3rem)] bg-page p-4 md:p-8">
    <div class="max-w-3xl mx-auto space-y-4">
      <header class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-slate-800">{{ t('progress.title') }}</h1>
        <RouterLink to="/"
          class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover">
          {{ t('common.backToCompass') }}
        </RouterLink>
      </header>

      <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>

      <section v-if="data" class="bg-surface rounded-xl shadow p-6 text-center border-t-4 border-amber-500">
        <p class="text-sm uppercase tracking-wider text-slate-500">{{ t('progress.total') }}</p>
        <p class="text-6xl font-bold text-slate-800 tabular-nums" style="font-family: var(--font-display)">{{ data.total }}</p>
      </section>

      <section v-if="data" class="bg-surface rounded-xl shadow p-4">
        <h2 class="font-bold text-slate-800 mb-2">{{ t('progress.sources') }}</h2>
        <ul class="divide-y">
          <li v-for="r in rows" :key="r.key" class="flex items-center justify-between py-2 text-sm text-slate-700">
            <span><span aria-hidden="true">{{ r.icon }}</span> {{ t(`progress.${r.key}`) }}
              <span v-if="r.count !== null" class="text-slate-500">· {{ r.count }}</span></span>
            <span class="font-medium tabular-nums">{{ t('progress.pts', { n: r.points }) }}</span>
          </li>
        </ul>
      </section>

      <BadgesPanel />
    </div>
    <BadgeToast />
  </div>
</template>
