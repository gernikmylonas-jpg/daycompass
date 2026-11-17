<script setup lang="ts">
import { computed } from 'vue'

// Draws the Moon as seen from the northern hemisphere: the lit part grows on the right while
// the Moon waxes and shrinks on the left while it wanes.
const props = withDefaults(defineProps<{ cycle: number; size?: number }>(), { size: 32 })

const R = 20
const C = 24

const lit = computed(() => {
  const cycle = ((props.cycle % 1) + 1) % 1
  const waxing = cycle < 0.5
  const gibbous = cycle > 0.25 && cycle < 0.75
  const rx = R * Math.abs(Math.cos(2 * Math.PI * cycle))
  if (cycle < 0.004 || cycle > 0.996) return ''
  if (Math.abs(cycle - 0.5) < 0.004) return `M ${C} ${C - R} A ${R} ${R} 0 1 1 ${C} ${C + R} A ${R} ${R} 0 1 1 ${C} ${C - R} Z`
  const outer = waxing ? 1 : 0
  const inner = waxing ? (gibbous ? 1 : 0) : (gibbous ? 0 : 1)
  return `M ${C} ${C - R} A ${R} ${R} 0 0 ${outer} ${C} ${C + R} A ${rx.toFixed(2)} ${R} 0 0 ${inner} ${C} ${C - R} Z`
})
</script>

<template>
  <svg viewBox="0 0 48 48" :width="size" :height="size" aria-hidden="true" class="shrink-0">
    <circle :cx="C" :cy="C" :r="R" fill="#2b3446" stroke="var(--color-slate-400)" stroke-width="1.2" />
    <path v-if="lit" :d="lit" fill="#f4efd6" />
  </svg>
</template>
