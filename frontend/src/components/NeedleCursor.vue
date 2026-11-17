<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useSettingsStore } from '../stores/settings'

// A compass needle that replaces the mouse pointer.
// - The tip points at the compass (the big dial on the home page, the emblem in the top bar elsewhere).
// - It is a damped spring, so it overshoots and settles like a real needle, and shaking the
//   mouse sideways makes it swing.
// - Over the dial itself it rests at north.
// - Clicking sends out a small ripple.
// Off on touch devices, when switched off in settings, in forced-colors mode; static for reduced motion.

const settings = useSettingsStore()
const root = ref<HTMLElement | null>(null)
const needle = ref<SVGElement | null>(null)

const finePointer = ref(false)
const reducedMotion = ref(false)
const forcedColors = ref(false)
const enabled = computed(() => settings.needleCursor && finePointer.value && !forcedColors.value)

interface Ripple { id: number; x: number; y: number }
const ripples = ref<Ripple[]>([])
let rippleId = 0
function removeRipple(id: number) {
  ripples.value = ripples.value.filter((r) => r.id !== id)
}

const FIELD =
  'input:not([type="checkbox"]):not([type="radio"]):not([type="button"]):not([type="submit"]), textarea, select, [contenteditable="true"]'
const ACTION =
  'button, a, label, summary, [role="button"], [role="radio"], input[type="checkbox"], input[type="radio"], input[type="button"], input[type="submit"]'

// spring: stiffness / damping ratio (0.42 => a couple of visible swings)
const STIFFNESS = 220
const DAMPING = 2 * Math.sqrt(STIFFNESS) * 0.42

let x = -100
let y = -100
let angle = 0
let velocity = 0 // degrees per second
let scale = 1
let visible = false
let overField = false
let overAction = false
let pressed = false
let raf = 0
let lastTime = 0
let running = false

const mqFine = window.matchMedia('(pointer: fine)')
const mqMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
const mqForced = window.matchMedia('(forced-colors: active)')
function syncMedia() {
  finePointer.value = mqFine.matches
  reducedMotion.value = mqMotion.matches
  forcedColors.value = mqForced.matches
}

function compassRect(): DOMRect | null {
  const el =
    document.querySelector('[data-compass-target="main"]') ??
    document.querySelector('[data-compass-target="logo"]')
  return el ? el.getBoundingClientRect() : null
}

const wrap180 = (deg: number) => ((((deg + 180) % 360) + 360) % 360) - 180

function frame(now: number) {
  raf = requestAnimationFrame(frame)
  const dt = Math.min(0.033, (now - (lastTime || now)) / 1000)
  lastTime = now

  let goal = angle
  const rect = compassRect()
  if (rect) {
    const dx = rect.left + rect.width / 2 - x
    const dy = rect.top + rect.height / 2 - y
    const onDial = Math.hypot(dx, dy) < (rect.width / 2) * 0.92
    goal = onDial ? 0 : (Math.atan2(dy, dx) * 180) / Math.PI + 90
  }

  if (reducedMotion.value) {
    angle = goal
    velocity = 0
  } else {
    const diff = wrap180(goal - angle)
    velocity += (STIFFNESS * diff - DAMPING * velocity) * dt
    angle += velocity * dt
  }

  const scaleGoal = pressed ? 0.85 : overAction ? 1.3 : 1
  scale += (scaleGoal - scale) * Math.min(1, dt * 18)

  if (root.value && needle.value) {
    root.value.style.transform = `translate3d(${x}px, ${y}px, 0)`
    root.value.style.opacity = visible && !overField ? '1' : '0'
    needle.value.style.transform = `rotate(${angle}deg) scale(${scale})`
  }
}

function onMove(e: PointerEvent) {
  if (e.pointerType && e.pointerType !== 'mouse') return
  // quick sideways movement kicks the needle, so it swings before settling again
  if (!reducedMotion.value) velocity += Math.max(-400, Math.min(400, e.movementX * 5))
  x = e.clientX
  y = e.clientY
  visible = true
  const el = e.target as Element | null
  overField = !!el?.closest?.(FIELD)
  overAction = !overField && !!el?.closest?.(ACTION)
}

function onDown(e: PointerEvent) {
  if (e.pointerType && e.pointerType !== 'mouse') return
  pressed = true
  if (!reducedMotion.value && !overField) ripples.value.push({ id: ++rippleId, x: e.clientX, y: e.clientY })
}
const onUp = () => (pressed = false)
const onLeave = () => (visible = false)

function start() {
  if (running) return
  running = true
  document.documentElement.classList.add('needle-cursor')
  window.addEventListener('pointermove', onMove, { passive: true })
  window.addEventListener('pointerdown', onDown, { passive: true })
  window.addEventListener('pointerup', onUp, { passive: true })
  document.documentElement.addEventListener('mouseleave', onLeave)
  lastTime = 0
  raf = requestAnimationFrame(frame)
}

function stop() {
  if (!running) return
  running = false
  cancelAnimationFrame(raf)
  document.documentElement.classList.remove('needle-cursor')
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerdown', onDown)
  window.removeEventListener('pointerup', onUp)
  document.documentElement.removeEventListener('mouseleave', onLeave)
  visible = false
  ripples.value = []
}

watch(enabled, (on) => (on ? start() : stop()))

onMounted(() => {
  syncMedia()
  for (const mq of [mqFine, mqMotion, mqForced]) mq.addEventListener('change', syncMedia)
  if (enabled.value) start()
})
onBeforeUnmount(() => {
  stop()
  for (const mq of [mqFine, mqMotion, mqForced]) mq.removeEventListener('change', syncMedia)
})
</script>

<template>
  <template v-if="enabled">
    <div v-for="r in ripples" :key="r.id" class="needle-ripple" aria-hidden="true"
      :style="{ left: r.x + 'px', top: r.y + 'px' }" @animationend="removeRipple(r.id)" />

    <div ref="root" aria-hidden="true"
      style="position: fixed; left: 0; top: 0; z-index: 2147483000; pointer-events: none; opacity: 0; will-change: transform; transition: opacity 0.12s">
      <svg ref="needle" width="36" height="36" viewBox="-18 -18 36 36"
        style="position: absolute; left: -18px; top: -18px; overflow: visible; filter: drop-shadow(0 1px 2px rgb(0 0 0 / 0.5))">
        <polygon points="0,-16 -4.6,0 4.6,0" fill="var(--color-compass-north)" stroke="rgb(255 255 255 / 0.9)" stroke-width="0.9" stroke-linejoin="round" />
        <polygon points="0,16 -4.6,0 4.6,0" fill="var(--color-needle-tail)" stroke="rgb(255 255 255 / 0.9)" stroke-width="0.9" stroke-linejoin="round" />
        <circle r="2.6" fill="#fff" stroke="var(--color-slate-800)" stroke-width="1" />
      </svg>
    </div>
  </template>
</template>
