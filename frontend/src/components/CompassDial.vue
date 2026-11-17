<script setup lang="ts">
import { ref } from 'vue'

// Decorative compass face: bezel rings, tick marks ("degrees") and the north marker.
// The page calls highlight(angle) as the pointer moves: ticks near that bearing glow and grow,
// and a small degree readout rides the outside of the bezel. highlight(null) clears it.
// The N/E/S/W letters and the centre symbol are real controls laid over this face by the page.
const CENTER = 100
const SIGMA = 13 // degrees: how wide the glow around the pointer's bearing is

function polar(radius: number, degrees: number) {
  const rad = (degrees * Math.PI) / 180
  return { x: CENTER + radius * Math.sin(rad), y: CENTER - radius * Math.cos(rad) }
}

const ticks = Array.from({ length: 72 }, (_, i) => {
  const deg = i * 5
  const length = deg % 90 === 0 ? 12 : deg % 45 === 0 ? 9 : deg % 15 === 0 ? 6 : 3.5
  const a = polar(95, deg)
  const b = polar(95 - length, deg)
  return { deg, x1: a.x, y1: a.y, x2: b.x, y2: b.y, major: deg % 45 === 0 }
})

const tickEls = ref<SVGLineElement[]>([])
const readout = ref<{ text: string; x: number; y: number } | null>(null)
let lastRounded = -1

function highlight(angle: number | null) {
  if (angle === null) {
    for (const el of tickEls.value) el?.style.setProperty('--k', '0')
    readout.value = null
    lastRounded = -1
    return
  }
  for (let i = 0; i < ticks.length; i++) {
    const diff = Math.abs((((ticks[i].deg - angle) % 360) + 540) % 360 - 180)
    tickEls.value[i]?.style.setProperty('--k', Math.exp(-(diff * diff) / (2 * SIGMA * SIGMA)).toFixed(3))
  }
  const rounded = (Math.round(angle / 5) * 5) % 360
  if (rounded !== lastRounded) {
    lastRounded = rounded
    const p = polar(108, rounded)
    readout.value = { text: `${rounded}°`, x: p.x, y: p.y }
  }
}

defineExpose({ highlight })
</script>

<template>
  <svg viewBox="0 0 200 200" class="block overflow-visible" aria-hidden="true">
    <circle cx="100" cy="100" r="98" fill="none" stroke="var(--color-slate-300)" stroke-width="1.5" />
    <circle cx="100" cy="100" r="82" fill="none" stroke="var(--color-slate-200)" stroke-width="1" />

    <line v-for="(tick, i) in ticks" :key="i" :ref="(el) => { if (el) tickEls[i] = el as SVGLineElement }"
      :x1="tick.x1" :y1="tick.y1" :x2="tick.x2" :y2="tick.y2" class="tick" stroke-linecap="round"
      :style="{ '--base': tick.major ? 'var(--color-slate-500)' : 'var(--color-slate-300)', '--w': tick.major ? 1.6 : 1 }" />

    <polygon points="100,1 94.5,12 105.5,12" fill="var(--color-compass-north)" />

    <text v-if="readout" :x="readout.x" :y="readout.y" text-anchor="middle" dominant-baseline="central"
      font-size="7.5" font-weight="700" fill="var(--color-compass-north)" class="readout"
      style="font-family: var(--font-display); paint-order: stroke; stroke: var(--color-page); stroke-width: 2.5px">{{ readout.text }}</text>
  </svg>
</template>

<style scoped>
.tick {
  stroke: color-mix(in srgb, var(--color-compass-north) calc(var(--k, 0) * 100%), var(--base));
  stroke-width: calc(var(--w) * 1px + var(--k, 0) * 2.2px);
  transition: stroke-width 0.12s, stroke 0.12s;
}
</style>
