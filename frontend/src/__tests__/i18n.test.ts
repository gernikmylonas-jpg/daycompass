import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import en from '../i18n/locales/en'
import es from '../i18n/locales/es'
import fr from '../i18n/locales/fr'
import el from '../i18n/locales/el'

const locales = { en, es, fr, el }

function flatten(obj: Record<string, unknown>, prefix = ''): [string, string][] {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === 'object' && v !== null ? flatten(v as Record<string, unknown>, `${prefix}${k}.`) : [[`${prefix}${k}`, String(v)] as [string, string]],
  )
}

const keys = (l: Record<string, unknown>) => flatten(l).map(([k]) => k).sort()
const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

describe('translations', () => {
  it.each(['es', 'fr', 'el'] as const)('%s has exactly the same keys as English', (code) => {
    expect(keys(locales[code])).toEqual(keys(en))
  })

  it.each(['es', 'fr', 'el'] as const)('%s uses the same {placeholders} as English in every message', (code) => {
    const english = new Map(flatten(en))
    for (const [key, text] of flatten(locales[code])) {
      expect(placeholders(text), `${code}:${key}`).toEqual(placeholders(english.get(key)!))
    }
  })

  it('has no empty messages', () => {
    for (const [code, locale] of Object.entries(locales)) {
      for (const [key, text] of flatten(locale)) expect(text.trim(), `${code}:${key}`).not.toBe('')
    }
  })

  it('every message compiles and resolves', () => {
    const params = { n: 3, h: 7, m: 30, steps: 1, sleep: 1, current: 1, best: 2, name: 'X', time: '1:05', date: '17/11/2026', days: 3, avg: '5', best_: 9, points: 5, done: 1, total: 2, a: 7, b: 6, axis: 'X', with: 1, without: 2 }
    for (const code of Object.keys(locales)) {
      const i18n = createI18n({ legacy: false, locale: code, fallbackLocale: 'en', messages: locales, missingWarn: false, fallbackWarn: false })
      for (const [key, text] of flatten(locales[code as keyof typeof locales])) {
        const out = text.includes('|') ? i18n.global.t(key, 2) : i18n.global.t(key, params)
        expect(out, `${code}:${key}`).not.toBe(key)
        expect(out, `${code}:${key}`).not.toMatch(/[{}]/)
      }
    }
  })
})
