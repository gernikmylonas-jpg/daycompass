<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { useSettingsStore } from '../stores/settings'
import { useNuggetsStore } from '../stores/nuggets'
import NuggetIcon from './NuggetIcon.vue'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'

// Today's quest: one small challenge, worth one extra gold nugget. Shown only if quests are switched on in Settings.
interface Quest { id: string; metric: string; target: number; progress: number; done: boolean; claimed: boolean; reward_nuggets: number; completed_total: number }
const { t, locale } = useI18n()
const settings = useSettingsStore()
const nuggets = useNuggetsStore()
const badges = useBadgesStore()
const quest = ref<Quest | null>(null)
const error = ref('')
const percent = computed(() => (quest.value ? Math.min(100, Math.round((quest.value.progress / quest.value.target) * 100)) : 0))
const num = (n: number) => n.toLocaleString(locale.value)

async function load() {
  if (!settings.questsOn) return
  try {
    quest.value = (await api.get<Quest>('/api/quests/today')).data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
async function claim() {
  error.value = ''
  try {
    const { data } = await api.post<Quest & { new_badges?: BadgeInfo[] }>('/api/quests/today/claim')
    quest.value = data
    await badges.announce(data.new_badges)
    await nuggets.fetch()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
onMounted(load)
</script>

<template>
  <section v-if="settings.questsOn && quest" class="bg-surface rounded-xl shadow p-4 space-y-2 border-t-4 border-amber-500">
    <div class="flex items-center justify-between gap-2">
      <h2 class="font-bold text-slate-800">🎯 {{ t('quest.title') }}</h2>
      <span class="flex items-center gap-1 text-sm text-slate-700"><NuggetIcon :size="16" />+{{ quest.reward_nuggets }}</span>
    </div>
    <p class="text-slate-800">{{ t(`quest.${quest.id}`) }}</p>
    <div class="h-2 rounded bg-slate-100 overflow-hidden" role="progressbar" :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100" :aria-label="t('quest.title')">
      <div class="h-full" :class="quest.done ? 'bg-ok' : 'bg-amber-500'" :style="{ width: percent + '%' }"></div>
    </div>
    <div class="flex items-center justify-between gap-2">
      <p class="text-xs text-slate-500 tabular-nums">{{ num(quest.progress) }} / {{ num(quest.target) }} · {{ t('quest.total', quest.completed_total) }}</p>
      <p v-if="quest.claimed" class="text-sm text-ok">{{ t('quest.claimed') }}</p>
      <button v-else-if="quest.done" type="button" @click="claim" class="bg-primary text-on-primary rounded-lg px-4 py-1.5 text-sm hover:bg-primary-hover">{{ t('quest.claim') }}</button>
    </div>
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
  </section>
</template>
