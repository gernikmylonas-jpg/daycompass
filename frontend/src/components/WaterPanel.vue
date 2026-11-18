<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { intlLocale } from '../i18n'
import { parseIso, toIso } from '../i18n/dates'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'

// Glasses of water today (about 250 ml each): tap a glass, or use + and −. Nothing is saved until you tap.
interface Water { goal: number; today: number; goal_streak: number; days: { date: string; glasses: number | null }[] }
const { t, locale } = useI18n()
const data = ref<Water | null>(null)
const error = ref('')
const badges = useBadgesStore()
const loc = computed(() => intlLocale(locale.value))

async function load() {
  try {
    data.value = (await api.get<Water>('/api/water')).data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
async function set(n: number) {
  error.value = ''
  try {
    const { data: saved } = await api.put<{ new_badges?: BadgeInfo[] }>(`/api/water/${toIso(new Date())}`, { glasses: Math.max(0, Math.min(30, n)) })
    await badges.announce(saved.new_badges)
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

const slots = computed(() => Math.max(data.value?.goal ?? 8, data.value?.today ?? 0))
const max = computed(() => Math.max(data.value?.goal ?? 8, ...(data.value?.days.map((d) => d.glasses ?? 0) ?? [0])))
const weekday = (iso: string) => new Intl.DateTimeFormat(loc.value, { weekday: 'narrow' }).format(parseIso(iso))
const litres = computed(() => ((data.value?.today ?? 0) * 0.25).toLocaleString(loc.value, { maximumFractionDigits: 2 }))
onMounted(load)
</script>

<template>
  <div v-if="data" class="space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
    <section class="bg-surface rounded-xl shadow p-4 space-y-3 border-t-4 border-sky-500">
      <div class="flex items-baseline justify-between">
        <h3 class="font-bold text-slate-800">{{ t('water.title') }}</h3>
        <p class="text-sm text-slate-600 tabular-nums">{{ data.today }} / {{ data.goal }} · {{ t('water.litres', { n: litres }) }}</p>
      </div>
      <div class="flex flex-wrap gap-2 justify-center" role="group" :aria-label="t('water.title')">
        <button v-for="i in slots" :key="i" type="button" @click="set(data.today === i ? i - 1 : i)" :aria-pressed="data.today >= i" :aria-label="t('water.glass', { n: i })"
          :class="['w-9 h-11 rounded-b-xl rounded-t-sm border-2 flex items-end overflow-hidden transition', data.today >= i ? 'border-sky-500' : 'border-slate-300 hover:border-slate-500']">
          <span class="w-full transition-all" :class="data.today >= i ? 'h-4/5 bg-sky-400' : 'h-0'"></span>
        </button>
      </div>
      <div class="flex justify-center gap-2">
        <button type="button" @click="set(data.today - 1)" :disabled="data.today <= 0" :aria-label="t('water.less')" class="w-9 h-9 rounded-full border border-slate-400 text-lg hover:bg-slate-50 disabled:opacity-40">−</button>
        <button type="button" @click="set(data.today + 1)" :aria-label="t('water.more')" class="w-9 h-9 rounded-full border border-slate-400 text-lg hover:bg-slate-50">+</button>
      </div>
      <p class="text-center text-sm text-slate-600">
        <template v-if="data.today >= data.goal">💧 {{ t('water.reached') }}</template>
        <template v-else>{{ t('water.left', data.goal - data.today) }}</template>
        <span v-if="data.goal_streak > 0" class="text-streak"> · 🔥 {{ t('steps.streak', data.goal_streak) }}</span>
      </p>
    </section>
    <section class="bg-surface rounded-xl shadow p-4">
      <h3 class="font-bold text-slate-800 mb-2">{{ t('water.last14') }}</h3>
      <div class="flex items-end gap-1 h-20" role="img" :aria-label="t('water.last14')">
        <div v-for="d in data.days" :key="d.date" class="flex-1 flex flex-col items-center justify-end h-full gap-1" :title="`${d.date}: ${d.glasses ?? 0}`">
          <div class="w-full rounded-t" :class="(d.glasses ?? 0) >= data.goal ? 'bg-sky-500' : 'bg-slate-300'" :style="{ height: ((d.glasses ?? 0) / max) * 100 + '%', minHeight: d.glasses ? '3px' : '2px' }"></div>
          <span class="text-[0.6rem] text-slate-500">{{ weekday(d.date) }}</span>
        </div>
      </div>
      <p class="text-xs text-slate-500 mt-2">{{ t('water.hint') }}</p>
    </section>
  </div>
</template>
