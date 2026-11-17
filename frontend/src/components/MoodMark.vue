<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MoodStyle } from '../stores/settings'
import { MOOD_EMOJI, moodFill, moodInk } from '../mood'

// One mood score (1-10) drawn in the style the user chose: an emoji, a colour, or a word.
const props = withDefaults(defineProps<{ score: number; styleKind: MoodStyle; size?: 'sm' | 'md' }>(), { size: 'md' })
const { t } = useI18n()

const word = computed(() => t(`mood.words.${props.score}`))
const box = computed(() => (props.size === 'sm' ? 'min-w-7 h-7 text-xs' : 'min-w-10 h-10 text-sm'))
</script>

<template>
  <span v-if="styleKind === 'emoji'" :class="['inline-flex items-center justify-center', size === 'sm' ? 'text-lg' : 'text-2xl']" aria-hidden="true">{{ MOOD_EMOJI[score - 1] }}</span>
  <span v-else-if="styleKind === 'colors'" :class="['inline-flex items-center justify-center rounded-full font-bold tabular-nums', box]"
    :style="{ background: moodFill(score), color: moodInk(score) }" aria-hidden="true">{{ score }}</span>
  <span v-else :class="['inline-flex items-center justify-center rounded-full px-2 font-medium border border-slate-400 text-slate-700', box]" aria-hidden="true">{{ word }}</span>
</template>
