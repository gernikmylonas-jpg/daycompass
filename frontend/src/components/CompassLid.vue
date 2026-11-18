<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useSettingsStore } from '../stores/settings'

// The compass lid: when the option is on, the compass starts closed and the lid flips open by itself
// (or at once on any click or key). Its colour and engraving follow the compass style.
// It is decoration only: it never stays in the way of the controls for more than a moment.
const settings = useSettingsStore()
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
const state = ref<'off' | 'closed' | 'opening' | 'gone'>(settings.lidAnimation && !reduced ? 'closed' : 'off')
let autoTimer: number | undefined
let doneTimer: number | undefined

function open() {
  if (state.value !== 'closed') return
  window.clearTimeout(autoTimer)
  state.value = 'opening'
  doneTimer = window.setTimeout(() => (state.value = 'gone'), 1200)
}

onMounted(() => {
  if (state.value !== 'closed') return
  autoTimer = window.setTimeout(open, 600)
  window.addEventListener('keydown', open)
  window.addEventListener('pointerdown', open)
})
onBeforeUnmount(() => {
  window.clearTimeout(autoTimer)
  window.clearTimeout(doneTimer)
  window.removeEventListener('keydown', open)
  window.removeEventListener('pointerdown', open)
})

const STAR = '100,28 108,92 172,100 108,108 100,172 92,108 28,100 92,92'
</script>

<template>
  <div v-if="state === 'closed' || state === 'opening'" :class="['compass-lid', state === 'opening' && 'opening']" aria-hidden="true">
    <svg viewBox="0 0 200 200" class="w-full h-full" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
      <!-- classic: engraved rose in two rings -->
      <g v-if="settings.theme === 'classic'">
        <circle cx="100" cy="100" r="86" stroke-width="1.5" /><circle cx="100" cy="100" r="76" stroke-width="0.8" />
        <polygon :points="STAR" fill="currentColor" fill-opacity="0.25" stroke-width="1.4" />
        <circle cx="100" cy="100" r="6" stroke-width="1.4" />
      </g>
      <!-- modern: brushed metal, one thin ring and a north tick -->
      <g v-else-if="settings.theme === 'modern'">
        <circle cx="100" cy="100" r="70" stroke-width="1" /><path d="M100 22v22" stroke-width="2" /><circle cx="100" cy="100" r="3" fill="currentColor" />
      </g>
      <!-- retro: bronze with rivets and a star -->
      <g v-else-if="settings.theme === 'retro'">
        <circle cx="100" cy="100" r="84" stroke-width="2" stroke-dasharray="2 5" />
        <circle v-for="a in 8" :key="a" :cx="100 + 92 * Math.sin((a * Math.PI) / 4)" :cy="100 - 92 * Math.cos((a * Math.PI) / 4)" r="3.2" fill="currentColor" fill-opacity="0.55" stroke-width="1" />
        <polygon :points="STAR" fill="currentColor" fill-opacity="0.3" stroke-width="1.6" />
        <circle cx="100" cy="100" r="40" stroke-width="1" /><path d="M100 14v10" stroke-width="3" />
      </g>
      <!-- nautical: anchor inside a rope ring -->
      <g v-else-if="settings.theme === 'nautical'">
        <circle cx="100" cy="100" r="82" stroke-width="5" stroke-dasharray="3 3" />
        <circle cx="100" cy="62" r="8" stroke-width="3" /><path d="M100 70v62M80 86h40M62 112c4 22 22 32 38 32s34-10 38-32M62 112l-8 8M138 112l8 8" stroke-width="4" />
      </g>
      <!-- explorer: stitched leather, mountain and arrow -->
      <g v-else-if="settings.theme === 'explorer'">
        <circle cx="100" cy="100" r="88" stroke-width="2" stroke-dasharray="6 5" />
        <path d="M52 132l32-52 20 30 14-18 30 40z" stroke-width="3" fill="currentColor" fill-opacity="0.2" />
        <path d="M94 38l6-8 6 8" stroke-width="3" />
      </g>
      <!-- neon: circuit traces and a glowing ring -->
      <g v-else-if="settings.theme === 'neon'">
        <circle cx="100" cy="100" r="84" stroke-width="2" />
        <path d="M30 100h34l12-20h48l12 20h34M100 80V40M76 120l-14 26h-22M124 120l14 26h22" stroke-width="2" />
        <circle cx="100" cy="100" r="10" stroke-width="2" /><circle cx="100" cy="40" r="3" fill="currentColor" /><circle cx="40" cy="146" r="3" fill="currentColor" /><circle cx="160" cy="146" r="3" fill="currentColor" />
      </g>
      <!-- minimal: nothing but an N -->
      <g v-else>
        <circle cx="100" cy="100" r="60" stroke-width="1" />
        <path d="M88 116V84l24 32V84" stroke-width="3" />
      </g>
    </svg>
  </div>
</template>
