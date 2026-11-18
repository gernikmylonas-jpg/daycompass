<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

// A progress ring for the day's steps: the first lap fills towards the goal, going past it starts a second,
// lighter lap, and the ring turns green once the goal is reached.
const props = defineProps<{ steps: number; goal: number; streak: number }>()
const { t, locale } = useI18n()

const R = 52
const C = 2 * Math.PI * R
const ratio = computed(() => (props.goal > 0 ? props.steps / props.goal : 0))
const lap1 = computed(() => Math.min(ratio.value, 1))
const lap2 = computed(() => Math.min(Math.max(ratio.value - 1, 0), 1))
const reached = computed(() => ratio.value >= 1)
const percent = computed(() => Math.round(ratio.value * 100))
const remaining = computed(() => Math.max(props.goal - props.steps, 0))
const num = (n: number) => n.toLocaleString(locale.value)
</script>

<template>
  <div class="flex flex-col items-center gap-2">
    <svg viewBox="0 0 140 140" class="w-44 h-44" role="img"
      :aria-label="t('steps.ringLabel', { steps: num(steps), goal: num(goal), percent })">
      <circle cx="70" cy="70" :r="R" fill="none" stroke="var(--color-slate-200)" stroke-width="12" />
      <circle cx="70" cy="70" :r="R" fill="none" stroke-width="12" stroke-linecap="round" transform="rotate(-90 70 70)"
        :stroke="reached ? 'var(--color-ok)' : 'var(--color-teal-500)'"
        :stroke-dasharray="C" :stroke-dashoffset="C * (1 - lap1)" class="ring" />
      <circle v-if="lap2 > 0" cx="70" cy="70" :r="R" fill="none" stroke-width="12" stroke-linecap="round" transform="rotate(-90 70 70)"
        stroke="var(--color-ok)" stroke-opacity="0.45" :stroke-dasharray="C" :stroke-dashoffset="C * (1 - lap2)" class="ring" />
      <text x="70" y="66" text-anchor="middle" font-size="22" font-weight="700" fill="var(--color-slate-800)" style="font-family: var(--font-display)">{{ num(steps) }}</text>
      <text x="70" y="84" text-anchor="middle" font-size="9.5" fill="var(--color-slate-500)">{{ t('steps.ofGoal', { goal: num(goal) }) }}</text>
      <text v-if="reached" x="70" y="102" text-anchor="middle" font-size="14" aria-hidden="true">🎉</text>
    </svg>
    <p class="text-sm text-slate-700 text-center">
      <template v-if="reached">{{ t('steps.reached') }}</template>
      <template v-else>{{ t('steps.remaining', { n: num(remaining) }) }}</template>
    </p>
    <p v-if="streak > 0" class="text-xs text-streak">🔥 {{ t('steps.streak', streak) }}</p>
  </div>
</template>

<style scoped>
.ring { transition: stroke-dashoffset 0.7s ease-out, stroke 0.3s; }
</style>
