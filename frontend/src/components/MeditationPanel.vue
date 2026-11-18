<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { formatDateTime } from '../i18n/dates'
import { useAuthStore } from '../stores/auth'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'

// A meditation timer with an optional breathing guide. A finished session is saved (+5 points).
interface Item { id: string; kind: string; duration_minutes: number; session_date: string; completed_at: string }
interface Summary { today_minutes: number; today_sessions: number; total_minutes: number; total_sessions: number; current_streak: number; recent: Item[] }
interface Result { points_awarded: number; new_badges: BadgeInfo[] }

type Kind = 'breathing' | 'silent'
type PatternId = 'box' | 'relax' | 'coherent' | 'calm' | 'triangle'
// seconds for [breathe in, hold, breathe out, hold]
const PATTERNS: Record<PatternId, [number, number, number, number]> = { box: [4, 4, 4, 4], relax: [4, 7, 8, 0], coherent: [5, 0, 5, 0], calm: [4, 0, 6, 0], triangle: [4, 4, 4, 0] }
const PRESETS = [5, 10, 15, 20, 30]
const PHASES = ['in', 'holdIn', 'out', 'holdOut'] as const

const { t } = useI18n()
const auth = useAuthStore()
const badges = useBadgesStore()
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

const minutes = ref(10)
const kind = ref<Kind>('breathing')
const pattern = ref<PatternId>('box')
const sound = ref(localStorage.getItem('meditationSound') !== 'off')

const state = ref<'idle' | 'running' | 'paused'>('idle')
const remaining = ref(minutes.value * 60)
const elapsed = ref(0)
const summary = ref<Summary | null>(null)
const message = ref('')
const error = ref('')

let timer: number | undefined
let endAt = 0
let plannedSeconds = 0

const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

// ── breathing guide ──────────────────────────────────────────────────────
const phaseIndex = computed(() => {
  const lens = PATTERNS[pattern.value]
  const cycle = lens.reduce((a, b) => a + b, 0)
  let at = elapsed.value % cycle
  for (let i = 0; i < 4; i++) {
    if (lens[i] > 0 && at < lens[i]) return i
    at -= lens[i]
  }
  return 0
})
const phase = computed(() => PHASES[phaseIndex.value])
const phaseSeconds = computed(() => PATTERNS[pattern.value][phaseIndex.value])
// the circle grows while breathing in and shrinks while breathing out
const circleScale = computed(() => {
  if (state.value !== 'running' || reducedMotion) return 0.7
  return phase.value === 'in' || phase.value === 'holdIn' ? 1 : 0.55
})

// ── a soft bell (no audio files needed) ─────────────────────────────────
function bell() {
  if (!sound.value) return
  try {
    const ctx = new AudioContext()
    for (const [freq, delay] of [[528, 0], [792, 0.02]] as const) {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.value = freq
      gain.gain.setValueAtTime(0.0001, ctx.currentTime + delay)
      gain.gain.exponentialRampToValueAtTime(0.25, ctx.currentTime + delay + 0.03)
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + delay + 3)
      osc.connect(gain).connect(ctx.destination)
      osc.start(ctx.currentTime + delay)
      osc.stop(ctx.currentTime + delay + 3.2)
    }
    window.setTimeout(() => ctx.close(), 3500)
  } catch {
    // audio unavailable: the session still works silently
  }
}

function toggleSound() {
  sound.value = !sound.value
  localStorage.setItem('meditationSound', sound.value ? 'on' : 'off')
}

// ── timer ────────────────────────────────────────────────────────────────
function clamp(m: number) {
  return Math.min(180, Math.max(1, Math.floor(m || 10)))
}

function setMinutes(m: number) {
  if (state.value !== 'idle') return
  minutes.value = clamp(m)
  remaining.value = minutes.value * 60
}

function tick() {
  remaining.value = Math.max(0, Math.round((endAt - Date.now()) / 1000))
  elapsed.value = plannedSeconds - remaining.value
  if (remaining.value <= 0) finish(true)
}

function start() {
  message.value = ''
  error.value = ''
  if (state.value === 'idle') {
    plannedSeconds = minutes.value * 60
    remaining.value = plannedSeconds
    elapsed.value = 0
  }
  endAt = Date.now() + remaining.value * 1000
  state.value = 'running'
  timer = window.setInterval(tick, 250)
}

function pause() {
  window.clearInterval(timer)
  state.value = 'paused'
}

function reset() {
  window.clearInterval(timer)
  state.value = 'idle'
  remaining.value = minutes.value * 60
  elapsed.value = 0
}

async function finish(completed: boolean) {
  window.clearInterval(timer)
  const doneSeconds = completed ? plannedSeconds : elapsed.value
  const doneMinutes = completed ? minutes.value : Math.round(doneSeconds / 60)
  reset()
  if (completed) bell()
  if (doneMinutes < 1) return // too short to count
  try {
    const { data } = await api.post<Result>('/api/meditation', { duration_minutes: doneMinutes, kind: kind.value })
    message.value = t('meditation.done', { n: doneMinutes, points: data.points_awarded })
    await auth.refreshUser().catch(() => {})
    await badges.announce(data.new_badges)
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

function finishEarly() {
  if (elapsed.value < 60) {
    reset()
    return
  }
  finish(false)
}

async function load() {
  try {
    summary.value = (await api.get<Summary>('/api/meditation/summary')).data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

onMounted(load)
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <div class="space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
    <p v-if="message" role="status" class="text-ok text-sm font-medium">{{ message }}</p>

    <section class="bg-surface rounded-xl shadow p-4 border-t-4 border-purple-500 text-center space-y-4">
      <!-- breathing circle -->
      <div class="mx-auto relative w-44 h-44 flex items-center justify-center" aria-hidden="true">
        <div class="absolute inset-0 rounded-full border border-slate-300"></div>
        <div v-if="kind === 'breathing'" class="rounded-full w-full h-full"
          :style="{ transform: `scale(${circleScale})`, transition: reducedMotion ? 'none' : `transform ${Math.max(phaseSeconds, 1)}s ease-in-out`,
            background: 'color-mix(in srgb, var(--color-purple-500) 28%, transparent)', border: '2px solid var(--color-purple-500)' }"></div>
        <div v-else class="rounded-full w-24 h-24" style="background: color-mix(in srgb, var(--color-purple-500) 18%, transparent)"></div>
        <p class="absolute text-4xl font-bold text-slate-800 tabular-nums" style="font-family: var(--font-display)">{{ mmss(remaining) }}</p>
      </div>
      <p v-if="kind === 'breathing' && state === 'running'" role="status" aria-live="polite" class="text-lg text-slate-700 min-h-7">
        {{ t(`meditation.phase.${phase}`) }}
      </p>
      <p v-else class="text-sm text-slate-500 min-h-7">{{ state === 'paused' ? t('meditation.paused') : '' }}</p>

      <div class="flex flex-wrap justify-center gap-2">
        <button v-if="state !== 'running'" @click="start"
          class="bg-primary text-on-primary rounded-lg px-5 py-2 text-sm hover:bg-primary-hover">
          {{ state === 'paused' ? t('meditation.resume') : t('meditation.start') }}
        </button>
        <button v-else @click="pause" class="bg-primary text-on-primary rounded-lg px-5 py-2 text-sm hover:bg-primary-hover">{{ t('pomodoro.pause') }}</button>
        <button v-if="state !== 'idle'" @click="finishEarly" class="border border-slate-400 text-slate-700 rounded-lg px-4 py-2 text-sm hover:bg-slate-50">
          {{ elapsed >= 60 ? t('meditation.finishEarly') : t('pomodoro.reset') }}
        </button>
      </div>

      <div v-if="state === 'idle'" class="space-y-3 text-sm text-slate-600">
        <div class="flex flex-wrap items-center justify-center gap-1.5" role="radiogroup" :aria-label="t('meditation.length')">
          <button v-for="m in PRESETS" :key="m" type="button" role="radio" :aria-checked="minutes === m" @click="setMinutes(m)"
            :class="['rounded-full border px-3 py-1', minutes === m ? 'border-slate-800 bg-slate-100 font-semibold text-slate-900' : 'border-slate-300 hover:bg-slate-50']">
            {{ t('pomodoro.minutes', { n: m }) }}
          </button>
          <label class="flex items-center gap-1">
            <input :value="minutes" @change="setMinutes(Number(($event.target as HTMLInputElement).value))" type="number" min="1" max="180"
              :aria-label="t('meditation.custom')" class="border rounded-lg px-2 py-1 w-16 text-center" />
            <span>{{ t('wellness.minutes') }}</span>
          </label>
        </div>
        <div class="flex flex-wrap items-center justify-center gap-4">
          <label class="flex items-center gap-2">
            {{ t('meditation.type') }}
            <select v-model="kind" class="border rounded-lg px-2 py-1">
              <option value="breathing">{{ t('meditation.breathing') }}</option>
              <option value="silent">{{ t('meditation.silent') }}</option>
            </select>
          </label>
          <label v-if="kind === 'breathing'" class="flex items-center gap-2">
            {{ t('meditation.pattern') }}
            <select v-model="pattern" class="border rounded-lg px-2 py-1">
              <option value="box">{{ t('meditation.box') }}</option>
              <option value="relax">{{ t('meditation.relax') }}</option>
              <option value="coherent">{{ t('meditation.coherent') }}</option>
              <option value="calm">{{ t('meditation.calm') }}</option>
              <option value="triangle">{{ t('meditation.triangle') }}</option>
            </select>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" :checked="sound" @change="toggleSound" class="h-4 w-4" />
            {{ t('meditation.bell') }}
          </label>
        </div>
      </div>
    </section>

    <section v-if="summary" class="grid grid-cols-3 gap-3 text-center">
      <div class="bg-surface rounded-xl shadow p-3">
        <p class="text-xs text-slate-500">{{ t('pomodoro.today') }}</p>
        <p class="text-xl font-bold text-slate-800 tabular-nums">{{ t('pomodoro.minutes', { n: summary.today_minutes }) }}</p>
      </div>
      <div class="bg-surface rounded-xl shadow p-3">
        <p class="text-xs text-slate-500">{{ t('pomodoro.total') }}</p>
        <p class="text-xl font-bold text-slate-800 tabular-nums">{{ t('pomodoro.minutes', { n: summary.total_minutes }) }}</p>
      </div>
      <div class="bg-surface rounded-xl shadow p-3">
        <p class="text-xs text-slate-500">{{ t('meditation.streak') }}</p>
        <p class="text-xl font-bold text-streak tabular-nums">🔥 {{ summary.current_streak }}</p>
      </div>
    </section>

    <section v-if="summary" class="bg-surface rounded-xl shadow p-4">
      <h3 class="font-bold text-slate-800 mb-2">{{ t('pomodoro.history') }}</h3>
      <ul v-if="summary.recent.length" class="divide-y">
        <li v-for="r in summary.recent" :key="r.id" class="flex justify-between py-2 text-sm text-slate-700">
          <span>{{ t(`meditation.${r.kind}`) }} · {{ t('pomodoro.minutes', { n: r.duration_minutes }) }}</span>
          <span class="text-slate-500">{{ formatDateTime(new Date(r.completed_at + 'Z')) }}</span>
        </li>
      </ul>
      <p v-else class="text-sm text-slate-500">{{ t('meditation.empty') }}</p>
    </section>
  </div>
</template>
