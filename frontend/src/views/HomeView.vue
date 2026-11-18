<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { apiErrorMessage } from '../i18n/errors'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { useHabitsStore, type Category, type Habit, type HeatmapDay } from '../stores/habits'
import Heatmap from '../components/Heatmap.vue'
import CompassDial from '../components/CompassDial.vue'
import CompassLid from '../components/CompassLid.vue'
import CompassEmblem from '../components/CompassEmblem.vue'
import DirectionMedallion from '../components/DirectionMedallion.vue'
import PomodoroPanel from '../components/PomodoroPanel.vue'
import GroupsPanel from '../components/GroupsPanel.vue'
import CalendarPanel from '../components/CalendarPanel.vue'
import WellnessPanel from '../components/WellnessPanel.vue'
import WeightPanel from '../components/WeightPanel.vue'
import AstronomyPanel from '../components/AstronomyPanel.vue'
import JournalPanel from '../components/JournalPanel.vue'
import MoodPanel from '../components/MoodPanel.vue'
import MeditationPanel from '../components/MeditationPanel.vue'
import HomeGuide, { type GuideItem } from '../components/HomeGuide.vue'
import BadgeToast from '../components/BadgeToast.vue'
import UserChip from '../components/UserChip.vue'
import { useStreakStore } from '../stores/streak'
import { useBadgesStore } from '../stores/badges'

const { t, locale } = useI18n()
const auth = useAuthStore()
const settings = useSettingsStore()
const habitsStore = useHabitsStore()
const badgesStore = useBadgesStore()
const streakStore = useStreakStore()
const router = useRouter()

const error = ref('')
const newNames = ref<Record<Category, string>>({
  body: '',
  mind: '',
  work: '',
  schedule: '',
})

const editingId = ref<string | null>(null)
const editName = ref('')
const editCategory = ref<Category>('body')
const editFreq = ref('daily')
const newFreq = ref('daily')
const FREQUENCIES = ['daily', 'weekly:1', 'weekly:2', 'weekly:3', 'weekly:4', 'weekly:5', 'weekly:6']

const selectedId = ref<string | null>(null)
const selectedDays = ref<HeatmapDay[]>([])

const selectedHabit = computed(
  () => habitsStore.habits.find((h) => h.id === selectedId.value) ?? null,
)

// ── the eight compass directions ─────────────────────────────────────────
type DirId = 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w' | 'nw'
type Kind = 'habits' | 'pomodoro' | 'groups' | 'calendar' | 'sleep' | 'soon'

interface Direction {
  id: DirId
  kind: Kind
  category?: Category
  angle: number // degrees clockwise from north
  title: string
  subtitle: string
  accentVar: string
  accentBorder: string
  side: 'left' | 'right' // which side of the compass its panel opens on (large screens)
}

const POMODORO_DAILY_TARGET = 4 // sessions shown as "full" on the Pomodoro letter
const pomodoroToday = ref(0)

const directions = computed<Direction[]>(() => [
  { id: 'n', kind: 'habits', category: 'body', angle: 0, title: t('home.north.title'), subtitle: t('home.north.subtitle'),
    accentVar: '--color-teal-500', accentBorder: 'border-teal-500', side: 'right' },
  { id: 'ne', kind: 'sleep', angle: 45, title: t('home.northeast.title'), subtitle: t('home.northeast.subtitle'),
    accentVar: '--color-indigo-500', accentBorder: 'border-indigo-500', side: 'right' },
  { id: 'e', kind: 'habits', category: 'schedule', angle: 90, title: t('home.east.title'), subtitle: t('home.east.subtitle'),
    accentVar: '--color-pink-500', accentBorder: 'border-pink-500', side: 'right' },
  { id: 'se', kind: 'calendar', angle: 135, title: t('home.southeast.title'), subtitle: t('home.southeast.subtitle'),
    accentVar: '--color-sky-500', accentBorder: 'border-sky-500', side: 'right' },
  { id: 's', kind: 'habits', category: 'mind', angle: 180, title: t('home.south.title'), subtitle: t('home.south.subtitle'),
    accentVar: '--color-purple-500', accentBorder: 'border-purple-500', side: 'right' },
  { id: 'sw', kind: 'pomodoro', angle: 225, title: t('home.southwest.title'), subtitle: t('home.southwest.subtitle'),
    accentVar: '--color-amber-500', accentBorder: 'border-amber-500', side: 'left' },
  { id: 'w', kind: 'habits', category: 'work', angle: 270, title: t('home.west.title'), subtitle: t('home.west.subtitle'),
    accentVar: '--color-orange-500', accentBorder: 'border-orange-500', side: 'left' },
  { id: 'nw', kind: 'groups', angle: 315, title: t('home.northwest.title'), subtitle: t('home.northwest.subtitle'),
    accentVar: '--color-green-500', accentBorder: 'border-green-500', side: 'left' },
])

const RING_RADIUS = 37 // letters sit on a circle of this many % of the dial width, from the centre

function medallionStyle(angle: number) {
  const rad = (angle * Math.PI) / 180
  return {
    left: `${50 + RING_RADIUS * Math.sin(rad)}%`,
    top: `${50 - RING_RADIUS * Math.cos(rad)}%`,
    transform: 'translate(-50%, -50%)',
  }
}

function habitsIn(category: Category) {
  return habitsStore.habits.filter((h) => h.category === category)
}

function doneIn(category: Category) {
  return habitsIn(category).filter((h) => h.checked_in_today).length
}

// sleep logged for today, for the ring on the sleep letter
const sleepToday = ref(0)
const sleepGoal = ref(420)

async function loadSleepToday() {
  try {
    const { data } = await api.get<{ sleep_goal_minutes: number; days: { sleep_minutes: number | null }[] }>('/api/wellness/summary')
    sleepGoal.value = data.sleep_goal_minutes
    sleepToday.value = data.days[data.days.length - 1]?.sleep_minutes ?? 0
  } catch {
    // the ring simply stays empty
  }
}

function progressOf(d: Direction) {
  if (d.kind === 'sleep') return { done: Math.min(sleepToday.value, sleepGoal.value), total: sleepGoal.value }
  if (d.kind === 'habits' && d.category) return { done: doneIn(d.category), total: habitsIn(d.category).length }
  if (d.kind === 'pomodoro') return { done: Math.min(pomodoroToday.value, POMODORO_DAILY_TARGET), total: POMODORO_DAILY_TARGET }
  return { done: 0, total: 0 }
}

function directionLabel(d: Direction) {
  if (d.kind === 'soon') return t('home.comingSoonLabel', { name: d.title })
  if (d.kind === 'groups' || d.kind === 'calendar') return `${d.title}: ${d.subtitle}`
  if (d.kind === 'sleep') {
    const time = t('wellness.duration', { h: Math.floor(sleepToday.value / 60), m: sleepToday.value % 60 })
    return t('home.sleepLabel', { name: d.title, time })
  }
  const p = progressOf(d)
  return t(d.kind === 'pomodoro' ? 'home.pomodoroLabel' : 'home.directionLabel', { name: d.title, done: p.done, total: p.total })
}

// ── panels: a direction's card opens only when its letter is activated ──
const openId = ref<DirId | null>(null)
const openDirection = computed(() => directions.value.find((d) => d.id === openId.value) ?? null)
const panelSide = computed(() => openDirection.value?.side ?? 'right')
const panelWidth = computed(() => (openDirection.value?.kind === 'calendar' ? 40 : 27)) // rem
const panelEl = ref<HTMLElement | null>(null)
const panelTitleEl = ref<HTMLElement | null>(null)
const medallionEls: Partial<Record<DirId, HTMLElement>> = {}

// An extra option inside a direction's card (like steps & sleep in the north)
type ExtraKey = 'wellness' | 'weight' | 'astronomy' | 'journal' | 'mood' | 'meditation'
const openExtra = ref<ExtraKey | null>(null)
const extras = computed<{ key: ExtraKey; icon: string; label: string }[]>(() => {
  switch (openDirection.value?.id) {
    case 'n': return [
      { key: 'wellness', icon: '👟', label: t('home.stepsHistory') },
      { key: 'weight', icon: '⚖️', label: t('home.weightOption') },
    ]
    case 'e': return [{ key: 'astronomy', icon: '🌙', label: t('home.astronomyOption') }]
    case 's': return [
      { key: 'journal', icon: '📓', label: t('home.journalOption') },
      { key: 'mood', icon: '🙂', label: t('home.moodOption') },
      { key: 'meditation', icon: '🧘', label: t('home.meditationOption') },
    ]
    default: return []
  }
})

// the meditation timer keeps running while you look at something else, so once opened it stays mounted
const meditationMounted = ref(false)
watch(openExtra, (key) => {
  if (key === 'meditation') meditationMounted.value = true
})

function setMedallion(id: DirId, el: unknown) {
  const node = (el as { $el?: unknown } | null)?.$el
  if (node instanceof HTMLElement) medallionEls[id] = node
}

async function toggleDirection(d: Direction) {
  if (d.kind === 'soon') return
  guideOpen.value = false
  if (openId.value === d.id) {
    closePanel(false)
    return
  }
  openId.value = d.id
  editingId.value = null
  openExtra.value = null
  await nextTick()
  panelTitleEl.value?.focus({ preventScroll: true })
  if (!window.matchMedia('(min-width: 1024px)').matches) {
    panelEl.value?.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'nearest' })
  }
}

function closePanel(restoreFocus: boolean) {
  const id = openId.value
  openId.value = null
  editingId.value = null
  if (restoreFocus && id) medallionEls[id]?.focus()
}

// ── guide: what each direction contains ──────────────────────────────────
const guideOpen = ref(false)
const guideButton = ref<HTMLButtonElement | null>(null)

const guideItems = computed<GuideItem[]>(() => [
  ...directions.value.map((d) => ({
    id: d.id,
    letter: t(`compass.${d.id}`),
    title: `${d.title} · ${d.subtitle}`,
    text: t(`home.guide.${d.id}`),
    accent: d.accentVar,
    soon: d.kind === 'soon',
  })),
  { id: 'center', letter: '✦', title: t('home.guide.centerTitle'), text: t('home.guide.center'), accent: '--color-slate-500' },
])

function toggleGuide() {
  guideOpen.value = !guideOpen.value
}

function closeGuide() {
  guideOpen.value = false
  guideButton.value?.focus()
}

// Esc closes the guide first, then the open direction panel — unless a menu is open (it takes Esc)
function onEscape(ev: KeyboardEvent) {
  if (ev.key !== 'Escape') return
  if (document.querySelector('#settings-panel, #language-menu, #calendar-context-menu')) return
  if (guideOpen.value) {
    closeGuide()
    return
  }
  if (openId.value) closePanel(true)
}

function onDocumentClick(ev: MouseEvent) {
  const target = ev.target as Node
  if (guideOpen.value && !(target as Element).closest?.('[data-guide-root]')) guideOpen.value = false
}

function showError(e: unknown) {
  error.value = apiErrorMessage(e)
}

async function loadSelected() {
  if (!selectedId.value) return
  try {
    selectedDays.value = await habitsStore.fetchHabitHeatmap(selectedId.value)
  } catch (e) {
    showError(e)
  }
}

async function selectHabit(habit: Habit) {
  if (selectedId.value === habit.id) {
    closeSelected()
    return
  }
  selectedId.value = habit.id
  selectedDays.value = []
  await loadSelected()
}

function closeSelected() {
  selectedId.value = null
  selectedDays.value = []
}

const freqLabel = (f: string) => (f === 'daily' ? t('home.freqDaily') : t('home.freqWeekly', Number(f.split(':')[1])))

function startEdit(habit: Habit) {
  editingId.value = habit.id
  editName.value = habit.name
  editCategory.value = habit.category
  editFreq.value = habit.frequency
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit(habit: Habit) {
  const name = editName.value.trim()
  if (!name) return
  error.value = ''
  try {
    await habitsStore.updateHabit(habit, { name, category: editCategory.value, frequency: editFreq.value })
    editingId.value = null
  } catch (e) {
    showError(e)
  }
}

async function add(category: Category) {
  const name = newNames.value[category].trim()
  if (!name) return
  error.value = ''
  try {
    await habitsStore.addHabit(name, category, newFreq.value)
    newNames.value[category] = ''
    newFreq.value = 'daily'
  } catch (e) {
    showError(e)
  }
}

const bumpId = ref<DirId | null>(null)

async function toggle(habit: Habit) {
  if (habit.checked_in_today) return
  error.value = ''
  try {
    const newBadges = await habitsStore.checkIn(habit)
    await auth.refreshUser()
    streakStore.fetch()
    bumpId.value = directions.value.find((d) => d.category === habit.category)?.id ?? null
    window.setTimeout(() => (bumpId.value = null), 600)
    await badgesStore.announce(newBadges)
    if (selectedId.value === habit.id) await loadSelected()
  } catch (e) {
    showError(e)
  }
}

async function remove(habit: Habit) {
  error.value = ''
  try {
    await habitsStore.removeHabit(habit.id)
    if (selectedId.value === habit.id) closeSelected()
    if (editingId.value === habit.id) editingId.value = null
  } catch (e) {
    showError(e)
  }
}

const reminderEnabled = ref(false)
const reminderReady = ref(false)

async function loadReminder() {
  try {
    const { data } = await api.get<{ enabled: boolean; language: string }>('/api/reminders')
    reminderEnabled.value = data.enabled
  } catch {
    // reminders are optional; leave the toggle off
  } finally {
    reminderReady.value = true
  }
}

async function saveReminder() {
  try {
    await api.put('/api/reminders', { enabled: reminderEnabled.value, language: locale.value })
  } catch (e) {
    reminderEnabled.value = !reminderEnabled.value
    showError(e)
  }
}

// keep the email language in sync with the language chosen in the app
watch(locale, () => {
  if (reminderReady.value && reminderEnabled.value) saveReminder()
})

function logout() {
  auth.logout()
  router.push('/login')
}

// ── compass: the degrees around the pointer's bearing light up ───────────
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
const dialEl = ref<HTMLElement | null>(null)
const dialFace = ref<InstanceType<typeof CompassDial> | null>(null)

// The centre symbol turns a full 360° to face the pointer, as a damped spring (it overshoots a
// little and settles). It keeps its last heading while the pointer is right over the middle,
// where the bearing is meaningless, and stays still for reduced motion.
const emblemEl = ref<HTMLElement | null>(null)
const EMBLEM_STIFFNESS = 55
const EMBLEM_DAMPING = 2 * Math.sqrt(EMBLEM_STIFFNESS) * 0.65
let emblemAngle = 0
let emblemTarget = 0
let emblemVelocity = 0
let emblemRaf = 0
let emblemLast = 0

const wrap180 = (deg: number) => ((((deg + 180) % 360) + 360) % 360) - 180

function emblemFrame(now: number) {
  const dt = Math.min(0.033, (now - (emblemLast || now)) / 1000)
  emblemLast = now
  const diff = wrap180(emblemTarget - emblemAngle)
  emblemVelocity += (EMBLEM_STIFFNESS * diff - EMBLEM_DAMPING * emblemVelocity) * dt
  emblemAngle += emblemVelocity * dt
  if (emblemEl.value) emblemEl.value.style.transform = `rotate(${emblemAngle.toFixed(2)}deg)`
  if (Math.abs(diff) < 0.05 && Math.abs(emblemVelocity) < 0.5) {
    emblemRaf = 0 // settled: stop the loop until the pointer moves again
    return
  }
  emblemRaf = requestAnimationFrame(emblemFrame)
}

function aimEmblem(bearing: number) {
  if (reducedMotion) return
  emblemTarget = bearing
  if (!emblemRaf) {
    emblemLast = 0
    emblemRaf = requestAnimationFrame(emblemFrame)
  }
}

function onPointerMove(e: PointerEvent) {
  if (e.pointerType === 'touch' || !dialEl.value) return
  const rect = dialEl.value.getBoundingClientRect()
  const dx = e.clientX - (rect.left + rect.width / 2)
  const dy = e.clientY - (rect.top + rect.height / 2)
  const bearing = (Math.atan2(dx, -dy) * 180) / Math.PI // clockwise from north
  dialFace.value?.highlight(((bearing % 360) + 360) % 360)
  if (Math.hypot(dx, dy) > rect.width * 0.08) aimEmblem(bearing)
  tiltDial(e, rect)
}
const onPointerGone = () => {
  dialFace.value?.highlight(null)
  resetTilt()
}

// 3D style: the dial leans slightly towards the pointer and the glass glare follows it
const reducedMotionTilt = window.matchMedia('(prefers-reduced-motion: reduce)').matches
function tiltDial(e: PointerEvent, rect: DOMRect) {
  const el = dialEl.value
  if (!el || document.documentElement.dataset.depth !== '3d') return
  const nx = Math.max(-1, Math.min(1, (e.clientX - (rect.left + rect.width / 2)) / (window.innerWidth / 2)))
  const ny = Math.max(-1, Math.min(1, (e.clientY - (rect.top + rect.height / 2)) / (window.innerHeight / 2)))
  el.style.setProperty('--tilt-y', reducedMotionTilt ? '0deg' : `${(nx * 7).toFixed(2)}deg`)
  el.style.setProperty('--tilt-x', reducedMotionTilt ? '0deg' : `${(-ny * 7).toFixed(2)}deg`)
  el.style.setProperty('--glare-x', `${(50 + nx * 38).toFixed(1)}%`)
  el.style.setProperty('--glare-y', `${(50 + ny * 38).toFixed(1)}%`)
}
function resetTilt() {
  const el = dialEl.value
  if (!el) return
  for (const k of ['--tilt-x', '--tilt-y', '--glare-x', '--glare-y']) el.style.removeProperty(k)
}

onMounted(async () => {
  document.addEventListener('keydown', onEscape)
  document.addEventListener('click', onDocumentClick)
  window.addEventListener('pointermove', onPointerMove, { passive: true })
  document.documentElement.addEventListener('mouseleave', onPointerGone)
  try {
    await Promise.all([habitsStore.fetchHabits(), habitsStore.fetchHeatmap(), auth.refreshUser(), loadReminder(), loadSleepToday()])
  } catch (e) {
    showError(e)
  }
})

onBeforeUnmount(() => {
  cancelAnimationFrame(emblemRaf)
  document.removeEventListener('keydown', onEscape)
  document.removeEventListener('click', onDocumentClick)
  window.removeEventListener('pointermove', onPointerMove)
  document.documentElement.removeEventListener('mouseleave', onPointerGone)
})
</script>

<template>
  <div class="min-h-[calc(100vh-3rem)] bg-page p-4 md:p-8">
    <div class="max-w-6xl mx-auto">
      <header class="flex flex-wrap items-center justify-between gap-3 mb-6">
        <!-- the name opens a plain-language guide to the compass -->
        <div class="relative" data-guide-root>
          <h1 class="text-2xl font-bold text-slate-800">
            <button ref="guideButton" type="button" @click.stop="toggleGuide"
              :aria-expanded="guideOpen" aria-controls="home-guide" :title="t('home.guide.open')"
              class="flex items-center gap-2 rounded-lg -mx-2 px-2 hover:bg-slate-100">
              DayCompass
              <span class="w-5 h-5 rounded-full border border-slate-500 text-slate-500 text-xs font-bold inline-flex items-center justify-center" aria-hidden="true">?</span>
              <span class="sr-only">{{ t('home.guide.open') }}</span>
            </button>
          </h1>
          <HomeGuide v-if="guideOpen" id="home-guide" :title="t('home.guide.title')" :intro="t('home.guide.intro')"
            :close-label="t('common.close')" :items="guideItems" @close="closeGuide" />
        </div>

        <nav class="flex flex-wrap items-center gap-x-4 gap-y-2" :aria-label="t('nav.label')">
          <UserChip />
          <button @click="logout"
            class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover">
            {{ t('nav.logout') }}
          </button>
        </nav>
      </header>

      <p v-if="error" role="alert" class="text-danger text-sm mb-4">{{ error }}</p>

      <!-- big compass in the middle; the panel of the activated letter slides in beside it -->
      <div class="grid grid-cols-1 lg:[grid-template-columns:var(--cols)] lg:transition-[grid-template-columns] lg:duration-300"
        :style="{ '--panel-inner': `${panelWidth - 1}rem`, '--cols': !openDirection ? '0px minmax(0,1fr) 0px'
          : panelSide === 'left' ? `${panelWidth}rem minmax(0,1fr) 0px` : `0px minmax(0,1fr) ${panelWidth}rem` }">

        <section ref="dialEl" data-compass-target="main"
          class="relative z-10 aspect-square w-[min(100%,44rem,calc(100vh-10rem))] min-w-64 mx-auto lg:col-start-2 lg:row-start-1">
          <div class="dial-bezel" aria-hidden="true"></div>
          <div class="dial-body absolute inset-0 rounded-full bg-surface shadow-lg"></div>
          <CompassDial ref="dialFace" class="dial-face absolute inset-0 w-full h-full" />
          <div class="dial-glass" aria-hidden="true"></div>
          <CompassLid />

          <!-- centre symbol (different for every compass style): opens points & badges -->
          <RouterLink to="/progress" :aria-label="`${t('home.centerLabel')}: ${auth.user?.total_points ?? 0}`"
            :title="`${t('home.centerLabel')}: ${auth.user?.total_points ?? 0}`"
            class="absolute rounded-full bg-surface flex items-center justify-center"
            style="inset: 26%; border: 1px dashed var(--color-slate-400); box-shadow: inset 0 1px 6px rgb(0 0 0 / 0.1)">
            <div ref="emblemEl" class="w-full h-full p-[12%] will-change-transform">
              <CompassEmblem :theme="settings.theme" />
            </div>
          </RouterLink>

          <div v-for="d in directions" :key="d.id" class="absolute" :style="medallionStyle(d.angle)">
            <DirectionMedallion :ref="(el) => setMedallion(d.id, el)"
              :letter="t(`compass.${d.id}`)" :done="progressOf(d).done" :total="progressOf(d).total"
              :accent="d.accentVar" :label="directionLabel(d)" :north="d.id === 'n'"
              :placeholder="d.kind === 'soon'" :size="d.id.length === 1 ? 'lg' : 'sm'"
              :active="openId === d.id" :bump="bumpId === d.id" controls="direction-panel"
              @click="toggleDirection(d)" />
          </div>
        </section>

        <aside v-show="openDirection" id="direction-panel" ref="panelEl" role="region"
          aria-labelledby="direction-panel-title"
          :class="['overflow-hidden lg:row-start-1 p-1 mt-6 lg:mt-0',
            panelSide === 'left' ? 'lg:col-start-1 lg:pr-5' : 'lg:col-start-3 lg:pl-5']">
          <div v-if="openDirection" class="lg:w-[var(--panel-inner)] space-y-4 pb-4">
            <div :class="['bg-surface rounded-xl shadow p-4 border-t-4', openDirection.accentBorder]">
              <div class="flex items-start justify-between gap-2">
                <div>
                  <h2 id="direction-panel-title" ref="panelTitleEl" tabindex="-1"
                    class="text-lg font-bold text-slate-800 outline-none">{{ openDirection.title }}</h2>
                  <p class="text-slate-500 text-sm">{{ openDirection.subtitle }}</p>
                </div>
                <div class="flex items-center gap-2">
                  <span v-if="progressOf(openDirection).total" class="text-xs text-slate-500 tabular-nums">
                    {{ progressOf(openDirection).done }}/{{ progressOf(openDirection).total }}
                  </span>
                  <button @click="closePanel(true)" :aria-label="t('home.closePanel')" :title="t('home.closePanel')"
                    class="w-7 h-7 inline-flex items-center justify-center rounded text-slate-500 hover:text-slate-900 hover:bg-slate-100">✕</button>
                </div>
              </div>

              <div v-if="openDirection.kind === 'habits' && openDirection.category" class="space-y-3 mt-3">
                <ul class="space-y-2">
                  <li v-for="h in habitsIn(openDirection.category)" :key="h.id">
                    <form v-if="editingId === h.id" @submit.prevent="saveEdit(h)" class="space-y-2">
                      <input v-model="editName" type="text" maxlength="100" @keyup.esc.stop="cancelEdit"
                        :aria-label="t('home.habitName')"
                        class="w-full border rounded-lg px-3 py-1.5 text-sm" />
                      <select v-model="editCategory" :aria-label="t('home.direction')"
                        class="w-full border rounded-lg px-2 py-1.5 text-sm">
                        <option v-for="o in directions.filter((x) => x.kind === 'habits')" :key="o.id" :value="o.category">
                          {{ o.title }} – {{ o.subtitle }}
                        </option>
                      </select>
                      <select v-model="editFreq" :aria-label="t('home.frequency')"
                        class="w-full border rounded-lg px-2 py-1.5 text-sm">
                        <option v-for="f in FREQUENCIES" :key="f" :value="f">{{ freqLabel(f) }}</option>
                      </select>
                      <div class="flex gap-2">
                        <button type="submit"
                          class="bg-primary text-on-primary rounded-lg px-3 py-1 text-sm hover:bg-primary-hover">
                          {{ t('common.save') }}
                        </button>
                        <button type="button" @click="cancelEdit"
                          class="border border-slate-400 text-slate-600 rounded-lg px-3 py-1 text-sm hover:bg-slate-50">
                          {{ t('common.cancel') }}
                        </button>
                      </div>
                    </form>

                    <div v-else class="flex items-center gap-1">
                      <button @click="toggle(h)" :disabled="h.checked_in_today"
                        :aria-label="h.name" :aria-pressed="h.checked_in_today"
                        :class="['w-6 h-6 mr-1 rounded-full border-2 flex items-center justify-center text-xs shrink-0',
                          h.checked_in_today ? 'bg-ok border-ok text-surface' : 'border-slate-400 hover:border-slate-700']">
                        <span v-if="h.checked_in_today" aria-hidden="true">✓</span>
                      </button>
                      <span :class="['flex-1 text-sm', h.checked_in_today ? 'line-through text-slate-500' : 'text-slate-700']">
                        {{ h.name }}
                      </span>
                      <span v-if="h.target_per_week" class="text-xs text-slate-600 whitespace-nowrap mr-1"
                        :title="t('home.weekProgress', { done: h.week_count, n: h.target_per_week })">{{ h.week_count }}/{{ h.target_per_week }}</span>
                      <span v-if="h.current_streak > 0" class="text-xs text-streak whitespace-nowrap mr-1"
                        :title="h.target_per_week ? t('home.bestWeeks', { n: h.best_streak }) : t('home.bestStreak', { n: h.best_streak })">🔥 {{ h.current_streak }}{{ h.target_per_week ? t('home.weekSuffix') : '' }}</span>
                      <button @click="selectHabit(h)" :aria-pressed="selectedId === h.id"
                        :aria-label="t('home.heatmap')" :title="t('home.heatmap')"
                        :class="['w-7 h-7 inline-flex items-center justify-center rounded text-sm hover:bg-slate-100',
                          selectedId === h.id ? 'text-ok' : 'text-slate-500 hover:text-slate-900']">📊</button>
                      <button @click="startEdit(h)" :aria-label="t('home.edit')" :title="t('home.edit')"
                        class="w-7 h-7 inline-flex items-center justify-center rounded text-sm text-slate-500 hover:text-slate-900 hover:bg-slate-100">✎</button>
                      <button @click="remove(h)" :aria-label="t('home.remove')" :title="t('home.remove')"
                        class="w-7 h-7 inline-flex items-center justify-center rounded text-sm text-slate-500 hover:text-danger hover:bg-slate-100">✕</button>
                    </div>
                  </li>
                  <li v-if="habitsIn(openDirection.category).length === 0" class="text-slate-500 text-sm">
                    {{ t('home.noHabits') }}
                  </li>
                </ul>

                <form @submit.prevent="add(openDirection.category)" class="flex flex-wrap gap-2">
                  <input v-model="newNames[openDirection.category]" data-add-input type="text" :placeholder="t('home.newHabit')"
                    :aria-label="`${openDirection.title}: ${t('home.newHabit')}`"
                    class="flex-1 min-w-0 border rounded-lg px-3 py-1.5 text-sm" />
                  <button type="submit" :aria-label="t('home.addHabit')"
                    class="bg-primary text-on-primary rounded-lg px-3 text-sm hover:bg-primary-hover">+</button>
                  <select v-model="newFreq" :aria-label="t('home.frequency')" class="basis-full border rounded-lg px-2 py-1 text-xs text-slate-600">
                    <option v-for="f in FREQUENCIES" :key="f" :value="f">{{ freqLabel(f) }}</option>
                  </select>
                </form>

                <!-- a separate option for this direction: steps & sleep (N), calendars (E), journal (S) -->
                <div v-if="extras.length" class="border-t border-slate-200 pt-3 space-y-1">
                  <button v-for="x in extras" :key="x.key" type="button" @click="openExtra = openExtra === x.key ? null : x.key"
                    :aria-expanded="openExtra === x.key"
                    class="w-full flex items-center justify-between rounded-lg px-2 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
                    <span><span aria-hidden="true">{{ x.icon }}</span> {{ x.label }}</span>
                    <span aria-hidden="true">{{ openExtra === x.key ? '▴' : '▾' }}</span>
                  </button>
                </div>
              </div>
            </div>

            <WellnessPanel v-if="openExtra === 'wellness'" :parts="['steps']" />
            <WeightPanel v-if="openExtra === 'weight'" />
            <WellnessPanel v-if="openDirection.kind === 'sleep'" :parts="['sleep']" @saved="loadSleepToday" />
            <AstronomyPanel v-if="openExtra === 'astronomy'" />
            <JournalPanel v-if="openExtra === 'journal'" />
            <MoodPanel v-if="openExtra === 'mood'" />
            <GroupsPanel v-if="openDirection.kind === 'groups'" />
            <CalendarPanel v-if="openDirection.kind === 'calendar'" />
          </div>

          <div v-if="meditationMounted" v-show="openDirection?.id === 's' && openExtra === 'meditation'" class="lg:w-[var(--panel-inner)] pb-4">
            <MeditationPanel />
          </div>

          <!-- stays mounted while hidden, so a running timer keeps going when you open another letter -->
          <div v-show="openDirection?.kind === 'pomodoro'" class="lg:w-[var(--panel-inner)] pb-4">
            <PomodoroPanel @summary="(n) => (pomodoroToday = n)" />
          </div>
        </aside>
      </div>

      <div class="mt-6 space-y-4">
        <div v-if="selectedHabit" class="space-y-2">
          <div class="flex items-center justify-between text-sm text-slate-600 px-1">
            <span>{{ t('home.streakSummary', { current: selectedHabit.current_streak, best: selectedHabit.best_streak }) }}</span>
            <button @click="closeSelected" class="hover:text-slate-900 px-2 py-1">{{ t('common.close') }} ✕</button>
          </div>
          <Heatmap :days="selectedDays" :title="t('home.heatmapFor', { name: selectedHabit.name })" />
        </div>

        <Heatmap :days="habitsStore.heatmap" :title="t('home.activityAll')" />
        <label v-if="reminderReady" class="bg-surface rounded-xl shadow p-4 flex items-start gap-3 cursor-pointer">
          <input v-model="reminderEnabled" @change="saveReminder" type="checkbox" class="mt-1 h-4 w-4" />
          <span>
            <span class="block text-sm font-medium text-slate-800">{{ t('reminders.label') }}</span>
            <span class="block text-xs text-slate-500">{{ t('reminders.hint') }}</span>
          </span>
        </label>
      </div>
      <BadgeToast />
    </div>
  </div>
</template>
