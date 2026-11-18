<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '../i18n'
import { formatDate, parseIso } from '../i18n/dates'

// Bars of steps for the last 7 days, 30 days or 12 months (monthly averages), with the goal as a dashed line.
export interface StepBucket { start: string; steps: number | null; days_logged: number; goal_days: number }
const props = defineProps<{ buckets: StepBucket[]; goal: number; period: 'week' | 'month' | 'year' }>()
const { t, locale } = useI18n()

const W = 320
const H = 150
const PAD = { l: 34, r: 6, t: 8, b: 20 }
const loc = computed(() => intlLocale(locale.value))

const max = computed(() => Math.max(props.goal * 1.2, ...props.buckets.map((b) => b.steps ?? 0)))
const niceMax = computed(() => Math.ceil(max.value / 2000) * 2000)
const innerW = W - PAD.l - PAD.r
const innerH = H - PAD.t - PAD.b
const slot = computed(() => innerW / props.buckets.length)
const y = (v: number) => PAD.t + innerH - (v / niceMax.value) * innerH
const bars = computed(() =>
  props.buckets.map((b, i) => ({
    ...b,
    x: PAD.l + i * slot.value + slot.value * 0.15,
    w: slot.value * 0.7,
    top: b.steps == null ? y(0) : y(b.steps),
    reached: b.steps != null && b.steps >= props.goal,
  })),
)

const labelOf = (b: StepBucket, i: number): string => {
  const d = parseIso(b.start)
  if (props.period === 'week') return new Intl.DateTimeFormat(loc.value, { weekday: 'short' }).format(d)
  if (props.period === 'month') return i % 5 === 0 || i === props.buckets.length - 1 ? String(d.getDate()) : ''
  return new Intl.DateTimeFormat(loc.value, { month: 'short' }).format(d)
}
const ticks = computed(() => [0, 0.5, 1].map((f) => Math.round((niceMax.value * f) / 1000) * 1000))
const kFmt = (n: number) => (n >= 1000 ? `${n / 1000}k` : String(n))
const titleOf = (b: StepBucket) =>
  b.steps == null
    ? `${formatDate(b.start)}: ${t('wellness.noData')}`
    : props.period === 'year'
      ? t('steps.monthTip', { month: new Intl.DateTimeFormat(loc.value, { month: 'long', year: 'numeric' }).format(parseIso(b.start)), avg: b.steps.toLocaleString(loc.value), days: b.days_logged, goal: b.goal_days })
      : `${formatDate(b.start)}: ${b.steps.toLocaleString(loc.value)}`
</script>

<template>
  <svg :viewBox="`0 0 ${W} ${H}`" class="w-full" role="img" :aria-label="t('steps.chartLabel')">
    <g v-for="v in ticks" :key="v">
      <line :x1="PAD.l" :x2="W - PAD.r" :y1="y(v)" :y2="y(v)" stroke="var(--color-slate-200)" stroke-width="0.7" />
      <text :x="PAD.l - 4" :y="y(v) + 3" text-anchor="end" font-size="8" fill="var(--color-slate-500)">{{ kFmt(v) }}</text>
    </g>
    <g v-for="(b, i) in bars" :key="b.start">
      <rect v-if="b.steps != null" :x="b.x" :y="b.top" :width="b.w" :height="Math.max(y(0) - b.top, 1)" rx="2"
        :fill="b.reached ? 'var(--color-ok)' : 'var(--color-teal-500)'"><title>{{ titleOf(b) }}</title></rect>
      <rect v-else :x="b.x" :y="y(0) - 1.5" :width="b.w" height="1.5" fill="var(--color-slate-300)"><title>{{ titleOf(b) }}</title></rect>
      <text :x="b.x + b.w / 2" :y="H - 6" text-anchor="middle" font-size="8" fill="var(--color-slate-500)">{{ labelOf(b, i) }}</text>
    </g>
    <line :x1="PAD.l" :x2="W - PAD.r" :y1="y(goal)" :y2="y(goal)" stroke="var(--color-compass-north)" stroke-width="1" stroke-dasharray="4 3" />
    <text :x="W - PAD.r" :y="y(goal) - 3" text-anchor="end" font-size="8" fill="var(--color-compass-north)">{{ t('steps.goalLine') }}</text>
  </svg>
</template>
