<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { TOUR_STEPS } from '../tour'

// A guided tour: the page is dimmed, the thing being explained stays bright, and a small card says what it is.
// Next/Back (or the arrow keys), Skip (or Esc). It is shown once for a new account and can be started again from the guide.
const emit = defineEmits<{ close: [finished: boolean] }>()
const { t } = useI18n()

const index = ref(0)
const step = computed(() => TOUR_STEPS[index.value])
const last = computed(() => index.value === TOUR_STEPS.length - 1)
const rect = ref<{ top: number; left: number; width: number; height: number } | null>(null)
const cardEl = ref<HTMLElement | null>(null)
const cardPos = ref<{ top: number; left: number }>({ top: 0, left: 0 })
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
const PAD = 8
const GAP = 14
let returnFocus: HTMLElement | null = null
let frame = 0

function find(): HTMLElement | null {
  const target = step.value.target
  if (!target) return null
  const els = [...document.querySelectorAll<HTMLElement>(`[data-tour="${target}"]`)]
  return els.find((e) => e.offsetParent !== null || getComputedStyle(e).position === 'fixed') ?? els[0] ?? null
}

function measure() {
  const el = find()
  if (!el) {
    rect.value = null
  } else {
    const r = el.getBoundingClientRect()
    rect.value = { top: r.top - PAD, left: r.left - PAD, width: r.width + PAD * 2, height: r.height + PAD * 2 }
  }
  place()
}

function place() {
  const card = cardEl.value
  if (!card) return
  const w = card.offsetWidth
  const h = card.offsetHeight
  const vw = window.innerWidth
  const vh = window.innerHeight
  const r = rect.value
  if (!r) {
    cardPos.value = { top: Math.max(12, (vh - h) / 2), left: Math.max(12, (vw - w) / 2) }
    return
  }
  const below = r.top + r.height + GAP
  const above = r.top - GAP - h
  let top = below + h <= vh - 12 ? below : above >= 12 ? above : Math.max(12, vh - h - 12)
  // when neither fits above/below (a tall target), sit beside it
  if (below + h > vh - 12 && above < 12) top = Math.min(Math.max(12, r.top), vh - h - 12)
  const left = Math.min(Math.max(12, r.left + r.width / 2 - w / 2), vw - w - 12)
  cardPos.value = { top, left }
}

async function show(i: number) {
  index.value = i
  const el = find()
  if (el) el.scrollIntoView({ block: 'center', inline: 'center', behavior: reduced ? 'auto' : 'smooth' })
  await nextTick()
  measure()
  // the smooth scroll takes a moment: measure again when it has settled
  window.setTimeout(measure, reduced ? 0 : 350)
  cardEl.value?.querySelector<HTMLElement>('[data-tour-primary]')?.focus({ preventScroll: true })
}

const next = () => (last.value ? emit('close', true) : show(index.value + 1))
const back = () => { if (index.value > 0) show(index.value - 1) }
const skip = () => emit('close', false)

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') { e.preventDefault(); skip() }
  else if (e.key === 'ArrowRight') { e.preventDefault(); next() }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); back() }
  else if (e.key === 'Tab') { // keep the keyboard inside the card
    const items = [...(cardEl.value?.querySelectorAll<HTMLElement>('button') ?? [])]
    if (!items.length) return
    const first = items[0], lastItem = items[items.length - 1]
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); lastItem.focus() }
    else if (!e.shiftKey && document.activeElement === lastItem) { e.preventDefault(); first.focus() }
  }
}
function onMove() {
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(measure)
}

onMounted(() => {
  returnFocus = document.activeElement as HTMLElement | null
  document.addEventListener('keydown', onKey, true)
  window.addEventListener('resize', onMove)
  window.addEventListener('scroll', onMove, true)
  show(0)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey, true)
  window.removeEventListener('resize', onMove)
  window.removeEventListener('scroll', onMove, true)
  cancelAnimationFrame(frame)
  returnFocus?.focus?.({ preventScroll: true })
})

const spotStyle = computed(() => {
  const r = rect.value
  if (!r) return {}
  return {
    top: r.top + 'px', left: r.left + 'px', width: r.width + 'px', height: r.height + 'px',
    borderRadius: step.value.round ? '9999px' : '14px',
  }
})
</script>

<template>
  <div class="tour-root" role="dialog" aria-modal="true" :aria-label="t('tour.title')">
    <!-- the dim layer also blocks clicks on the page behind -->
    <div class="tour-block" @click.stop></div>
    <div v-if="rect" class="tour-spot" :class="{ still: reduced }" :style="spotStyle" aria-hidden="true"></div>
    <div v-else class="tour-dim" aria-hidden="true"></div>

    <div ref="cardEl" class="tour-card" :class="{ still: reduced }" :style="{ top: cardPos.top + 'px', left: cardPos.left + 'px' }" aria-live="polite">
      <p class="text-xs text-slate-500 tabular-nums">{{ t('tour.stepOf', { n: index + 1, total: TOUR_STEPS.length }) }}</p>
      <h2 class="text-lg font-bold text-slate-800 mt-0.5">{{ t(`tour.steps.${step.id}.title`) }}</h2>
      <p class="text-sm text-slate-700 mt-1">{{ t(`tour.steps.${step.id}.text`) }}</p>
      <div class="flex items-center justify-between gap-2 mt-4">
        <button type="button" @click="skip" class="text-sm text-slate-600 underline hover:text-slate-900">{{ last ? t('common.close') : t('tour.skip') }}</button>
        <div class="flex gap-2">
          <button v-if="index > 0" type="button" @click="back" class="border border-slate-400 text-slate-700 rounded-lg px-3 py-1.5 text-sm hover:bg-slate-50">{{ t('tour.back') }}</button>
          <button type="button" data-tour-primary @click="next" class="bg-primary text-on-primary rounded-lg px-4 py-1.5 text-sm hover:bg-primary-hover">{{ last ? t('tour.finish') : t('tour.next') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tour-root { position: fixed; inset: 0; z-index: 3000; }
.tour-block { position: absolute; inset: 0; }
.tour-dim { position: absolute; inset: 0; background: rgb(0 0 0 / 0.62); }
/* the lit window: its huge shadow is what dims everything else */
.tour-spot {
  position: absolute;
  box-shadow: 0 0 0 9999px rgb(0 0 0 / 0.62), 0 0 0 3px var(--color-primary), 0 0 24px 4px rgb(255 255 255 / 0.25);
  transition: top 0.25s ease, left 0.25s ease, width 0.25s ease, height 0.25s ease, border-radius 0.25s ease;
  pointer-events: none;
}
.tour-card {
  position: absolute;
  width: min(22rem, calc(100vw - 24px));
  background: var(--color-surface);
  color: var(--color-slate-800);
  border: 1px solid var(--color-slate-300);
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 12px 40px rgb(0 0 0 / 0.45);
  transition: top 0.25s ease, left 0.25s ease;
}
.still, .tour-spot.still, .tour-card.still { transition: none; }
</style>
