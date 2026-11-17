import { createI18n } from 'vue-i18n'
import en from './locales/en'
import es from './locales/es'
import fr from './locales/fr'
import el from './locales/el'

export type LocaleCode = 'en' | 'es' | 'fr' | 'el'

export interface LocaleOption {
  code: LocaleCode
  name: string // always shown in the language's own name
  intl: string // BCP-47 tag used for Intl date formatting
}

export const LOCALES: LocaleOption[] = [
  { code: 'en', name: 'English', intl: 'en-GB' },
  { code: 'es', name: 'Español', intl: 'es-ES' },
  { code: 'fr', name: 'Français', intl: 'fr-FR' },
  { code: 'el', name: 'Ελληνικά', intl: 'el-GR' },
]

const STORAGE_KEY = 'locale'
const FALLBACK: LocaleCode = 'en'

function isLocale(value: unknown): value is LocaleCode {
  return LOCALES.some((l) => l.code === value)
}

function initialLocale(): LocaleCode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (isLocale(stored)) return stored
  } catch {
    // storage unavailable
  }
  for (const lang of navigator.languages ?? [navigator.language]) {
    const base = lang.toLowerCase().split('-')[0]
    if (isLocale(base)) return base
  }
  return FALLBACK
}

export const i18n = createI18n({
  legacy: false,
  locale: initialLocale(),
  fallbackLocale: FALLBACK,
  messages: { en, es, fr, el },
})

function applyHtmlLang(code: LocaleCode) {
  document.documentElement.lang = code
}
applyHtmlLang(i18n.global.locale.value as LocaleCode)

export function setLocale(code: LocaleCode) {
  i18n.global.locale.value = code
  applyHtmlLang(code)
  try {
    localStorage.setItem(STORAGE_KEY, code)
  } catch {
    // storage unavailable
  }
}

export function intlLocale(code: string): string {
  return LOCALES.find((l) => l.code === code)?.intl ?? 'en-GB'
}
