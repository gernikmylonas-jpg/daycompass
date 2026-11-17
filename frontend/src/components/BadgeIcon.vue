<script setup lang="ts">
import { computed } from 'vue'
import { BADGE_GROUPS, GLYPHS, TIER_METAL, artFor } from '../badgeArt'

// A badge drawn as a medal: a metal rim (bronze / silver / gold for how far you have come), the
// symbol in the colour of its compass direction, and small pips for the level. Locked badges
// are drawn in grey. Falls back to the stored emoji for codes without artwork.
const props = withDefaults(defineProps<{ code: string; fallback?: string; earned?: boolean; size?: number }>(), {
  earned: true,
  size: 56,
  fallback: '🏅',
})

const art = computed(() => artFor(props.code))
const accent = computed(() => {
  const group = BADGE_GROUPS.find((g) => g.key === art.value?.group)
  return `var(${group?.accent ?? '--color-slate-500'})`
})
const metal = computed(() => TIER_METAL[art.value?.tier ?? 1])
const gid = computed(() => `medal-${props.code}`)
const glyph = computed(() => GLYPHS[art.value?.glyph ?? ''] ?? '')
</script>

<template>
  <svg v-if="art && glyph" viewBox="0 0 64 64" :width="size" :height="size" aria-hidden="true"
    :style="earned ? undefined : 'filter: grayscale(1); opacity: 0.55'" class="shrink-0">
    <defs>
      <linearGradient :id="gid" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" :stop-color="metal.light" />
        <stop offset="1" :stop-color="metal.dark" />
      </linearGradient>
    </defs>
    <circle cx="32" cy="31" r="28" :fill="`url(#${gid})`" />
    <circle cx="32" cy="31" r="22.5" fill="var(--color-surface)" />
    <circle cx="32" cy="31" r="22.5" fill="none" stroke="rgb(0 0 0 / 0.18)" stroke-width="1" />
    <g transform="translate(17.5 16.5) scale(1.21)" :style="{ color: accent }" fill="none" stroke="currentColor"
      stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" v-html="glyph" />
    <circle v-for="i in art.tier" :key="i" :cx="32 + (i - (art.tier + 1) / 2) * 7" cy="59" r="2.2" :fill="metal.dark" />
  </svg>
  <span v-else class="inline-flex items-center justify-center rounded-full bg-surface border border-slate-300 shrink-0"
    :style="{ width: size + 'px', height: size + 'px', fontSize: size * 0.5 + 'px', filter: earned ? '' : 'grayscale(1)', opacity: earned ? 1 : 0.55 }"
    aria-hidden="true">{{ fallback }}</span>
</template>
