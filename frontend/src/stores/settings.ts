import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import api from '../api'
import { i18n, setLocale, LOCALES, type LocaleCode } from '../i18n'
import { useAuthStore } from './auth'

export type ThemeId = 'classic' | 'modern' | 'retro' | 'nautical' | 'explorer' | 'neon' | 'minimal'
export type ThemeMode = 'light' | 'dark' | 'system'

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

const THEME_KEY = 'theme'
const MODE_KEY = 'mode'
const NEEDLE_KEY = 'needleCursor'
const DEFAULT_THEME: ThemeId = 'classic'
const SAVE_DELAY_MS = 500

const isTheme = (v: unknown): v is ThemeId => THEMES.some((t) => t.id === v)
const isMode = (v: unknown): v is ThemeMode => MODES.includes(v as ThemeMode)
const isLocale = (v: unknown): v is LocaleCode => LOCALES.some((l) => l.code === v)

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

interface ServerSettings {
  theme: string
  mode: string
  needle_cursor: boolean
  language: string | null
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

  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  const systemDark = ref(mq.matches)
  mq.addEventListener('change', (e) => (systemDark.value = e.matches))
  const resolvedMode = computed<'light' | 'dark'>(() =>
    mode.value === 'system' ? (systemDark.value ? 'dark' : 'light') : mode.value,
  )

  function apply() {
    document.documentElement.dataset.theme = theme.value
    document.documentElement.dataset.mode = resolvedMode.value
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
        await pushToServer() // first time on this account: keep what this device has
        return
      }
      hydrating = true
      if (isTheme(data.theme)) theme.value = data.theme
      if (isMode(data.mode)) mode.value = data.mode
      needleCursor.value = data.needle_cursor
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

  function setTheme(id: ThemeId) {
    theme.value = id
  }

  function setMode(value: ThemeMode) {
    mode.value = value
  }

  return { theme, mode, resolvedMode, needleCursor, syncError, setTheme, setMode, loadFromServer }
})
