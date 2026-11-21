import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import api from '../api'
import { i18n, setLocale, LOCALES, type LocaleCode } from '../i18n'
import { useAuthStore } from './auth'

export type ThemeId = 'classic' | 'modern' | 'retro' | 'nautical' | 'explorer' | 'neon' | 'minimal'
export type ThemeMode = 'light' | 'dark' | 'system'
export type MoodStyle = 'emoji' | 'colors' | 'words'

export interface ThemeInfo {
  id: ThemeId
  // colours for the little preview in the settings menu: page, card, ink/primary, north marker
  swatch: { page: string; surface: string; primary: string; north: string }
}

export const THEMES: ThemeInfo[] = [
  { id: 'classic', swatch: { page: '#f1ecdf', surface: '#fffdf8', primary: '#23364f', north: '#a4262c' } },
  { id: 'modern', swatch: { page: '#f1f5f9', surface: '#ffffff', primary: '#1e293b', north: '#dc2626' } },
  { id: 'retro', swatch: { page: '#efe3c8', surface: '#fbf4e2', primary: '#3b2a1a', north: '#d9622b' } },
  { id: 'nautical', swatch: { page: '#0a1a2f', surface: '#10294a', primary: '#c9a227', north: '#ef6b5b' } },
  { id: 'explorer', swatch: { page: '#e6d5b3', surface: '#f3e7c9', primary: '#5a3a1e', north: '#9c2f23' } },
  { id: 'neon', swatch: { page: '#0b0b14', surface: '#14142a', primary: '#00e5ff', north: '#ff2e93' } },
  { id: 'minimal', swatch: { page: '#ffffff', surface: '#ffffff', primary: '#18181b', north: '#18181b' } },
]

export const MODES: ThemeMode[] = ['light', 'dark', 'system']
export const MOOD_STYLES: MoodStyle[] = ['emoji', 'colors', 'words']

const THEME_KEY = 'theme'
const MODE_KEY = 'mode'
const NEEDLE_KEY = 'needleCursor'
const MOOD_KEY = 'moodStyle'
const DEPTH_KEY = 'depth3d'
const BRIGHT_KEY = 'brightness'
const LID_KEY = 'lid'
const TOUR_KEY = 'tutorialSeen'
const QUESTS_KEY = 'quests'
const WALL_ON_KEY = 'wallpapersOn'
const WALL_KEY = 'wallpaper'
export interface CalendarLayers {
  holidays: boolean // public holidays of `country`
  country: string // ISO code, e.g. GR
  nameDays: boolean // Greek Orthodox name days
  history: boolean // moments from world history and fun facts
  national: boolean // national days of all countries
  journal: boolean // days that have journal entries / recordings
  cycle: boolean // logged and expected period days
}
const LAYERS_KEY = 'calendarLayers'
const defaultCountry = () => {
  const lang = (i18n.global.locale.value as string) || 'en'
  return lang === 'el' ? 'GR' : lang === 'es' ? 'ES' : lang === 'fr' ? 'FR' : 'GB'
}
export const BRIGHTNESS_MIN = 50
export const BRIGHTNESS_MAX = 150
const DEFAULT_THEME: ThemeId = 'classic'
const SAVE_DELAY_MS = 500

const isTheme = (v: unknown): v is ThemeId => THEMES.some((t) => t.id === v)
const isMode = (v: unknown): v is ThemeMode => MODES.includes(v as ThemeMode)
const isLocale = (v: unknown): v is LocaleCode => LOCALES.some((l) => l.code === v)
const isMoodStyle = (v: unknown): v is MoodStyle => MOOD_STYLES.includes(v as MoodStyle)

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // storage unavailable: the setting still applies for this session
  }
}

function parseLayers(raw: string | null | undefined): CalendarLayers {
  const base: CalendarLayers = { holidays: false, country: defaultCountry(), nameDays: false, history: false, national: false, journal: false, cycle: false }
  if (!raw) return base
  try {
    const v = JSON.parse(raw)
    return {
      holidays: v.holidays === true,
      country: typeof v.country === 'string' && /^[A-Za-z]{2}$/.test(v.country) ? v.country.toUpperCase() : base.country,
      nameDays: v.nameDays === true,
      history: v.history === true,
      national: v.national === true,
      journal: v.journal === true,
      cycle: v.cycle === true,
    }
  } catch {
    return base
  }
}

interface ServerSettings {
  theme: string
  mode: string
  needle_cursor: boolean
  language: string | null
  mood_style?: string
  depth_3d?: boolean
  lid_open?: boolean
  wallpaper?: string | null
  wallpapers_on?: boolean
  quests_on?: boolean
  tutorial_seen?: boolean
  calendar_prefs?: string | null
  brightness?: number
  saved: boolean
}

// Preferences live in the browser for instant start-up and on the server so they follow the
// account to every device: once logged in, the server copy wins and every change is saved back.
export const useSettingsStore = defineStore('settings', () => {
  const auth = useAuthStore()

  const storedTheme = read(THEME_KEY)
  const storedMode = read(MODE_KEY)
  const theme = ref<ThemeId>(isTheme(storedTheme) ? storedTheme : DEFAULT_THEME)
  const mode = ref<ThemeMode>(isMode(storedMode) ? storedMode : 'system')
  const needleCursor = ref(read(NEEDLE_KEY) !== 'off')
  const storedMood = read(MOOD_KEY)
  const moodStyle = ref<MoodStyle>(isMoodStyle(storedMood) ? storedMood : 'emoji')

  const calendarLayers = ref<CalendarLayers>(parseLayers(read(LAYERS_KEY)))
  const depth3d = ref(read(DEPTH_KEY) === 'on')
  // null = not known yet (the account has not answered); true = finished or skipped; false = a new account: show the tour
  const tutorialSeen = ref<boolean | null>(read(TOUR_KEY) === 'on' ? true : null)
  const questsOn = ref(read(QUESTS_KEY) === 'on')
  const wallpapersOn = ref(read(WALL_ON_KEY) === 'on')
  const wallpaper = ref<string | null>(read(WALL_KEY) || null)
  const lidAnimation = ref(read(LID_KEY) === 'on')
  const storedBright = Number(read(BRIGHT_KEY))
  const brightness = ref(storedBright >= BRIGHTNESS_MIN && storedBright <= BRIGHTNESS_MAX ? storedBright : 100)

  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  const systemDark = ref(mq.matches)
  mq.addEventListener('change', (e) => (systemDark.value = e.matches))
  const resolvedMode = computed<'light' | 'dark'>(() =>
    mode.value === 'system' ? (systemDark.value ? 'dark' : 'light') : mode.value,
  )

  function apply() {
    document.documentElement.dataset.theme = theme.value
    document.documentElement.dataset.mode = resolvedMode.value
    document.documentElement.dataset.wallpaper = wallpapersOn.value && wallpaper.value ? 'on' : 'off'
    document.documentElement.dataset.depth = depth3d.value ? '3d' : 'flat'
    document.documentElement.style.setProperty('--lamp', String(brightness.value / 100))
  }
  apply() // before first paint, so there is no flash of the wrong theme

  // ── server sync ────────────────────────────────────────────────────────
  let hydrating = false
  let saveTimer: number | undefined
  const syncError = ref(false)

  async function pushToServer() {
    if (!auth.isLoggedIn) return
    try {
      await api.put('/api/settings', {
        theme: theme.value,
        mode: mode.value,
        needle_cursor: needleCursor.value,
        language: i18n.global.locale.value,
        mood_style: moodStyle.value,
        depth_3d: depth3d.value,
        lid_open: lidAnimation.value,
        wallpaper: wallpaper.value,
        wallpapers_on: wallpapersOn.value,
        quests_on: questsOn.value,
        tutorial_seen: tutorialSeen.value === true,
        calendar_prefs: JSON.stringify(calendarLayers.value),
        brightness: brightness.value,
      })
      syncError.value = false
    } catch {
      syncError.value = true // keep working locally; the next change retries
    }
  }

  function scheduleSave() {
    if (hydrating || !auth.isLoggedIn) return
    window.clearTimeout(saveTimer)
    saveTimer = window.setTimeout(pushToServer, SAVE_DELAY_MS)
  }

  async function loadFromServer() {
    if (!auth.isLoggedIn) return
    try {
      const { data } = await api.get<ServerSettings>('/api/settings')
      if (!data.saved) {
        if (tutorialSeen.value === null) tutorialSeen.value = false // a brand-new account
        await pushToServer() // first time on this account: keep what this device has
        return
      }
      hydrating = true
      if (isTheme(data.theme)) theme.value = data.theme
      if (isMode(data.mode)) mode.value = data.mode
      needleCursor.value = data.needle_cursor
      if (isMoodStyle(data.mood_style)) moodStyle.value = data.mood_style
      if (data.calendar_prefs) Object.assign(calendarLayers.value, parseLayers(data.calendar_prefs))
      tutorialSeen.value = data.tutorial_seen === true || read(TOUR_KEY) === 'on'
      if (typeof data.quests_on === 'boolean') questsOn.value = data.quests_on
      if (typeof data.wallpapers_on === 'boolean') wallpapersOn.value = data.wallpapers_on
      wallpaper.value = data.wallpaper ?? null
      if (typeof data.lid_open === 'boolean') lidAnimation.value = data.lid_open
      if (typeof data.depth_3d === 'boolean') depth3d.value = data.depth_3d
      if (typeof data.brightness === 'number' && data.brightness >= BRIGHTNESS_MIN && data.brightness <= BRIGHTNESS_MAX) brightness.value = data.brightness
      if (isLocale(data.language)) setLocale(data.language)
      // let the watchers below run once while hydrating, so they do not echo it back
      await Promise.resolve()
      await new Promise((r) => window.setTimeout(r, 0))
      hydrating = false
    } catch {
      hydrating = false
      syncError.value = true
    }
  }

  watch(theme, (value) => {
    apply()
    write(THEME_KEY, value)
    scheduleSave()
  })
  watch(mode, (value) => {
    write(MODE_KEY, value)
    scheduleSave()
  })
  watch(resolvedMode, apply)
  watch(needleCursor, (value) => {
    write(NEEDLE_KEY, value ? 'on' : 'off')
    scheduleSave()
  })
  watch(() => i18n.global.locale.value, scheduleSave)
  watch(moodStyle, (value) => {
    write(MOOD_KEY, value)
    scheduleSave()
  })

  watch(depth3d, (value) => {
    apply()
    write(DEPTH_KEY, value ? 'on' : 'off')
    scheduleSave()
  })
  watch(calendarLayers, (value) => {
    write(LAYERS_KEY, JSON.stringify(value))
    scheduleSave()
  }, { deep: true })
  watch([wallpapersOn, wallpaper], ([on, id]) => {
    apply()
    write(WALL_ON_KEY, on ? 'on' : 'off')
    write(WALL_KEY, id ?? '')
    scheduleSave()
  })
  watch(tutorialSeen, (value) => {
    if (value === null) return
    write(TOUR_KEY, value ? 'on' : 'off')
    scheduleSave()
  })
  watch(questsOn, (value) => {
    write(QUESTS_KEY, value ? 'on' : 'off')
    scheduleSave()
  })
  watch(lidAnimation, (value) => {
    write(LID_KEY, value ? 'on' : 'off')
    scheduleSave()
  })
  watch(brightness, (value) => {
    apply()
    write(BRIGHT_KEY, String(value))
    scheduleSave()
  })

  function setTheme(id: ThemeId) {
    theme.value = id
  }

  function setMode(value: ThemeMode) {
    mode.value = value
  }

  function setMoodStyle(value: MoodStyle) {
    moodStyle.value = value
  }

  return { theme, mode, resolvedMode, needleCursor, moodStyle, depth3d, brightness, lidAnimation, wallpapersOn, wallpaper, questsOn, tutorialSeen, calendarLayers, syncError, setTheme, setMode, setMoodStyle, loadFromServer }
})
