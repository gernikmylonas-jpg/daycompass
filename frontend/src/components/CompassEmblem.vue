<script setup lang="ts">
import { computed } from 'vue'
import type { ThemeId } from '../stores/settings'

// The symbol in the middle of the compass, drawn differently for every compass style.
// Colours come from the theme's CSS variables, so light/dark mode follows automatically.
const props = defineProps<{ theme: ThemeId }>()

const C = 50

function pt(radius: number, degrees: number) {
  const rad = (degrees * Math.PI) / 180
  return [C + radius * Math.sin(rad), C - radius * Math.cos(rad)] as const
}

const fmt = (points: (readonly [number, number])[]) => points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')

// Compass rose: each point is two triangles (a light and a dark half) for a faceted look.
const rose = computed(() => {
  const out: { left: string; right: string; north: boolean }[] = []
  for (const deg of [0, 90, 180, 270]) {
    out.push({ left: fmt([pt(41, deg), pt(7, deg - 38), [C, C]]), right: fmt([pt(41, deg), pt(7, deg + 38), [C, C]]), north: deg === 0 })
  }
  for (const deg of [45, 135, 225, 315]) {
    out.push({ left: fmt([pt(26, deg), pt(5, deg - 42), [C, C]]), right: fmt([pt(26, deg), pt(5, deg + 42), [C, C]]), north: false })
  }
  return out
})

// Retro sunburst: alternating long and short rays.
const rays = computed(() =>
  Array.from({ length: 16 }, (_, i) => {
    const deg = i * 22.5
    const len = i % 2 === 0 ? 44 : 33
    return fmt([pt(len, deg), pt(14, deg - 7), pt(14, deg + 7)])
  }),
)

// Nautical wheel: spokes with handles.
const spokes = computed(() =>
  Array.from({ length: 8 }, (_, i) => {
    const [x1, y1] = pt(9, i * 45)
    const [x2, y2] = pt(40, i * 45)
    return { x1, y1, x2, y2, hx: pt(44, i * 45)[0], hy: pt(44, i * 45)[1] }
  }),
)

// Explorer seal: scalloped edge.
const scallops = computed(() =>
  Array.from({ length: 14 }, (_, i) => {
    const [x, y] = pt(40, i * (360 / 14))
    return { x, y }
  }),
)

const hexagon = computed(() => fmt(Array.from({ length: 6 }, (_, i) => pt(40, i * 60 + 30))))
</script>

<template>
  <svg viewBox="0 0 100 100" class="emblem block w-full h-full overflow-visible" aria-hidden="true">
    <!-- classic: compass rose -->
    <g v-if="props.theme === 'classic'">
      <circle :cx="C" :cy="C" r="46" fill="none" stroke="var(--color-slate-400)" stroke-width="1" />
      <circle :cx="C" :cy="C" r="43" fill="none" stroke="var(--color-slate-300)" stroke-width="0.6" stroke-dasharray="1.5 2" />
      <template v-for="(p, i) in rose" :key="i">
        <polygon :points="p.left" :fill="p.north ? 'var(--color-compass-north)' : 'var(--color-slate-700)'" />
        <polygon :points="p.right" :fill="p.north ? 'color-mix(in srgb, var(--color-compass-north) 70%, #fff)' : 'var(--color-slate-300)'" />
      </template>
      <circle :cx="C" :cy="C" r="3.4" fill="var(--color-surface)" stroke="var(--color-slate-700)" stroke-width="1.2" />
    </g>

    <!-- modern: crosshair and rings -->
    <g v-else-if="props.theme === 'modern'">
      <circle :cx="C" :cy="C" r="44" fill="none" stroke="var(--color-slate-300)" stroke-width="1.5" />
      <circle :cx="C" :cy="C" r="28" fill="none" stroke="var(--color-slate-400)" stroke-width="1.5" />
      <path d="M50 4v22M50 74v22M4 50h22M74 50h22" stroke="var(--color-slate-500)" stroke-width="2" stroke-linecap="round" />
      <polygon :points="fmt([pt(24, 0), pt(10, -45), pt(10, 45)])" fill="var(--color-compass-north)" />
      <circle :cx="C" :cy="C" r="5" fill="var(--color-primary)" />
    </g>

    <!-- retro: sunburst -->
    <g v-else-if="props.theme === 'retro'">
      <polygon v-for="(r, i) in rays" :key="i" :points="r" :fill="i % 2 === 0 ? 'var(--color-compass-north)' : 'var(--color-needle-tail)'" />
      <circle :cx="C" :cy="C" r="15" fill="var(--color-surface)" stroke="var(--color-primary)" stroke-width="3.5" />
      <circle :cx="C" :cy="C" r="6" fill="var(--color-primary)" />
    </g>

    <!-- nautical: ship's wheel -->
    <g v-else-if="props.theme === 'nautical'">
      <circle :cx="C" :cy="C" r="27" fill="none" stroke="var(--color-primary)" stroke-width="5" />
      <circle :cx="C" :cy="C" r="21" fill="none" stroke="var(--color-slate-400)" stroke-width="0.8" />
      <g v-for="(s, i) in spokes" :key="i">
        <line :x1="s.x1" :y1="s.y1" :x2="s.x2" :y2="s.y2" stroke="var(--color-primary)" stroke-width="3.5" stroke-linecap="round" />
        <circle :cx="s.hx" :cy="s.hy" r="3.6" :fill="i === 0 ? 'var(--color-compass-north)' : 'var(--color-primary)'" />
      </g>
      <circle :cx="C" :cy="C" r="8" fill="var(--color-surface)" stroke="var(--color-primary)" stroke-width="3" />
    </g>

    <!-- explorer: wax seal with a four-point star -->
    <g v-else-if="props.theme === 'explorer'">
      <circle v-for="(s, i) in scallops" :key="i" :cx="s.x" :cy="s.y" r="7" fill="var(--color-compass-north)" />
      <circle :cx="C" :cy="C" r="37" fill="var(--color-compass-north)" />
      <circle :cx="C" :cy="C" r="30" fill="none" stroke="var(--color-surface)" stroke-width="1.2" opacity="0.7" />
      <polygon :points="fmt([pt(27, 0), pt(7, 45), pt(27, 90), pt(7, 135), pt(27, 180), pt(7, 225), pt(27, 270), pt(7, 315)])" fill="var(--color-surface)" />
    </g>

    <!-- neon: glowing hexagon -->
    <g v-else-if="props.theme === 'neon'" style="filter: drop-shadow(0 0 3px var(--color-primary))">
      <polygon :points="hexagon" fill="none" stroke="var(--color-primary)" stroke-width="3" stroke-linejoin="round" />
      <polygon :points="fmt([pt(22, 0), pt(20, 140), pt(20, 220)])" fill="none" stroke="var(--color-compass-north)" stroke-width="3" stroke-linejoin="round" />
      <circle :cx="C" :cy="C" r="3" fill="var(--color-primary)" />
    </g>

    <!-- minimal: ring and north triangle -->
    <g v-else>
      <circle :cx="C" :cy="C" r="40" fill="none" stroke="var(--color-slate-400)" stroke-width="1.5" />
      <polygon :points="fmt([pt(30, 0), pt(14, -35), pt(14, 35)])" fill="var(--color-slate-800)" />
      <circle :cx="C" :cy="C" r="3" fill="none" stroke="var(--color-slate-800)" stroke-width="1.5" />
    </g>
  </svg>
</template>

<style scoped>
.emblem {
  transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}
:global(a:hover) > .emblem,
:global(a:focus-visible) > .emblem {
  transform: rotate(22.5deg) scale(1.04);
}
</style>
