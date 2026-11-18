<script setup lang="ts">
import { computed } from 'vue'

// A radar (spider) chart for the compass report. Axes go clockwise from the top (north); values
// are 0-100 and null means "no data" (drawn at the centre and labelled as such).
export interface RadarAxis { key: string; label: string; value: number | null }

const props = defineProps<{ axes: RadarAxis[]; title: string; noData: string }>()

const SIZE = 320
const C = SIZE / 2
const R = 105

function point(index: number, fraction: number) {
  const angle = (index / props.axes.length) * 2 * Math.PI
  return { x: C + R * fraction * Math.sin(angle), y: C - R * fraction * Math.cos(angle) }
}

const rings = [0.25, 0.5, 0.75, 1]
const ringPath = (f: number) => props.axes.map((_, i) => point(i, f)).map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') + 'Z'
const shape = computed(() => props.axes.map((a, i) => point(i, (a.value ?? 0) / 100)).map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') + 'Z')
const labels = computed(() =>
  props.axes.map((a, i) => {
    const p = point(i, 1.22)
    const anchor = Math.abs(p.x - C) < 8 ? 'middle' : p.x > C ? 'start' : 'end'
    return { ...a, x: p.x, y: p.y, anchor }
  }),
)
const summary = computed(() => props.axes.map((a) => `${a.label}: ${a.value === null ? props.noData : Math.round(a.value) + '%'}`).join(', '))
</script>

<template>
  <svg :viewBox="`0 0 ${SIZE} ${SIZE}`" class="w-full max-w-sm mx-auto" role="img" :aria-label="`${title}. ${summary}`">
    <path v-for="f in rings" :key="f" :d="ringPath(f)" fill="none" stroke="var(--color-slate-300)" stroke-width="1" />
    <line v-for="(a, i) in axes" :key="a.key" :x1="C" :y1="C" :x2="point(i, 1).x" :y2="point(i, 1).y" stroke="var(--color-slate-200)" stroke-width="1" />
    <path :d="shape" fill="color-mix(in srgb, var(--color-teal-500) 30%, transparent)" stroke="var(--color-teal-500)" stroke-width="2" stroke-linejoin="round" />
    <circle v-for="(a, i) in axes" :key="a.key" :cx="point(i, (a.value ?? 0) / 100).x" :cy="point(i, (a.value ?? 0) / 100).y" r="3.5"
      :fill="a.value === null ? 'var(--color-surface)' : 'var(--color-teal-500)'" stroke="var(--color-teal-500)" stroke-width="1.5" />
    <text v-for="l in labels" :key="l.key" :x="l.x" :y="l.y" :text-anchor="l.anchor" dominant-baseline="middle" font-size="11"
      :fill="l.value === null ? 'var(--color-slate-500)' : 'var(--color-slate-700)'" style="font-family: var(--font-display)">
      {{ l.label }}<tspan v-if="l.value !== null" font-weight="700"> {{ Math.round(l.value) }}</tspan>
    </text>
  </svg>
</template>
