import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { TOUR_STEPS } from '../tour'
import en from '../i18n/locales/en'
import es from '../i18n/locales/es'
import fr from '../i18n/locales/fr'
import el from '../i18n/locales/el'

describe('the first-visit tour', () => {
  it('has unique steps, each with a title and a text in every language', () => {
    expect(new Set(TOUR_STEPS.map((s) => s.id)).size).toBe(TOUR_STEPS.length)
    for (const [code, locale] of Object.entries({ en, es, fr, el })) {
      const steps = (locale.tour as { steps: Record<string, { title: string; text: string }> }).steps
      for (const s of TOUR_STEPS) {
        expect(steps[s.id]?.title, `${code} title of ${s.id}`).toBeTruthy()
        expect(steps[s.id]?.text, `${code} text of ${s.id}`).toBeTruthy()
      }
    }
  })

  it('points only at elements that are marked in the page', () => {
    const sources = ['views/HomeView.vue', 'components/SettingsMenu.vue', 'components/LanguageSwitcher.vue'].map((f) => readFileSync(new URL('../' + f, import.meta.url), 'utf-8')).join('\n')
    for (const s of TOUR_STEPS.filter((x) => x.target)) {
      const mark = s.target!.startsWith('dir-') ? 'data-tour="`dir-${d.id}`"' : `data-tour="${s.target}"`
      expect(sources, `data-tour for ${s.id}`).toContain(mark)
    }
  })

  it('keeps the texts short enough to read in a glance', () => {
    for (const s of TOUR_STEPS) {
      const text = (en.tour.steps as Record<string, { text: string }>)[s.id].text
      expect(text.length, s.id).toBeLessThan(150)
    }
  })
})
