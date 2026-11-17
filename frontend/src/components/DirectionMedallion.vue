<script setup lang="ts">
import { computed } from 'vue'

// One compass direction as a button. The ring around the letter fills with that direction's
// progress today; activating it opens the direction's panel. "placeholder" directions are the
// intermediate points reserved for features that are not built yet.
const props = withDefaults(defineProps<{
  letter: string
  done?: number
  total?: number
  accent: string // CSS variable name, e.g. --color-teal-500
  label: string
  active?: boolean
  bump?: boolean
  north?: boolean
  placeholder?: boolean
  size?: 'lg' | 'sm'
  controls?: string
}>(), { done: 0, total: 0, size: 'lg' })

const RADIUS = 17
const CIRCUMFERENCE = 2 * Math.PI * RADIUS
const offset = computed(() => {
  const ratio = props.total > 0 ? Math.min(1, props.done / props.total) : 0
  return CIRCUMFERENCE * (1 - ratio)
})
</script>

<template>
  <button type="button" :aria-label="label"
    :aria-disabled="placeholder ? 'true' : undefined"
    :aria-expanded="placeholder ? undefined : !!active"
    :aria-controls="placeholder ? undefined : controls"
    :title="label"
    :class="['relative rounded-full bg-surface flex items-center justify-center transition-transform duration-200',
      size === 'lg' ? 'w-12 h-12' : 'w-10 h-10',
      placeholder ? 'opacity-70' : '',
      active ? 'scale-110' : '', bump ? 'medallion-bump' : '']"
    :style="active ? { boxShadow: `0 0 0 3px color-mix(in srgb, var(${accent}) 40%, transparent)` } : undefined">
    <svg viewBox="0 0 40 40" class="absolute inset-0 w-full h-full" aria-hidden="true">
      <circle cx="20" cy="20" :r="RADIUS" fill="none" stroke="var(--color-slate-300)" stroke-width="3"
        :stroke-dasharray="placeholder ? '3 4' : undefined" />
      <circle v-if="total > 0" cx="20" cy="20" :r="RADIUS" fill="none" :stroke="`var(${accent})`" stroke-width="3"
        stroke-linecap="round" :stroke-dasharray="CIRCUMFERENCE" :stroke-dashoffset="offset"
        transform="rotate(-90 20 20)" style="transition: stroke-dashoffset 0.6s ease" />
    </svg>
    <span :class="['relative font-bold leading-none', size === 'lg' ? 'text-xl' : 'text-sm']"
      :style="{ color: north ? 'var(--color-compass-north)' : placeholder ? 'var(--color-slate-500)' : 'var(--color-slate-700)', fontFamily: 'var(--font-display)' }">{{ letter }}</span>
  </button>
</template>
