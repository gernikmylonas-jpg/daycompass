<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate } from '../i18n/dates'
import type { HeatmapDay } from '../stores/habits'

const WEEKS = 17
const { t } = useI18n()
const props = defineProps<{ days: HeatmapDay[]; title?: string }>()
const heading = computed(() => props.title ?? t('heatmap.activity'))
const total = computed(() => props.days.reduce((sum, d) => sum + d.count, 0))

function iso(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const cells = computed(() => {
  const counts = new Map(props.days.map((h) => [h.date, h.count]))
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const mondayOffset = (today.getDay() + 6) % 7
  const start = new Date(today)
  start.setDate(today.getDate() - mondayOffset - (WEEKS - 1) * 7)

  const result: { date: string; count: number; future: boolean }[] = []
  for (let i = 0; i < WEEKS * 7; i++) {
    const d = new Date(start)
    d.setDate(start.getDate() + i)
    const key = iso(d)
    result.push({ date: key, count: counts.get(key) ?? 0, future: d > today })
  }
  return result
})

function color(count: number, future: boolean) {
  if (future) return 'bg-transparent'
  if (count === 0) return 'bg-slate-200'
  if (count === 1) return 'bg-green-300'
  if (count === 2) return 'bg-green-500'
  return 'bg-green-700'
}
</script>

<template>
  <section class="bg-surface rounded-xl shadow p-4">
    <h2 class="text-lg font-bold text-slate-800 mb-3">{{ heading }}</h2>
    <div class="overflow-x-auto" role="img" :aria-label="`${heading}: ${t('heatmap.checkins', total)}`">
      <div class="grid grid-flow-col grid-rows-7 gap-1 w-max">
        <div v-for="c in cells" :key="c.date"
          :title="c.future ? '' : `${formatDate(c.date)}: ${t('heatmap.checkins', c.count)}`"
          :class="['w-3.5 h-3.5 rounded-sm', color(c.count, c.future)]" />
      </div>
    </div>
    <div class="flex items-center gap-1 mt-3 text-xs text-slate-500">
      <span>{{ t('heatmap.less') }}</span>
      <span class="w-3.5 h-3.5 rounded-sm bg-slate-200" />
      <span class="w-3.5 h-3.5 rounded-sm bg-green-300" />
      <span class="w-3.5 h-3.5 rounded-sm bg-green-500" />
      <span class="w-3.5 h-3.5 rounded-sm bg-green-700" />
      <span>{{ t('heatmap.more') }}</span>
    </div>
  </section>
</template>
