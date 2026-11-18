import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { BADGE_ART, BADGE_GROUPS, GLYPHS } from '../badgeArt'
import en from '../i18n/locales/en'
import es from '../i18n/locales/es'
import fr from '../i18n/locales/fr'
import el from '../i18n/locales/el'

// the codes the backend can award, read straight from its catalog
const backendSource = readFileSync(new URL('../../../backend/app/application/services/badges.py', import.meta.url), 'utf-8')
const backendCodes = [...backendSource.matchAll(/(?:"code": |^\s+\()"([a-z0-9_]+)"/gm)].map((m) => m[1])

const translated = (locale: { badges: Record<string, unknown> }) =>
  Object.keys(locale.badges).filter((k) => !['title', 'newBadge', 'groups', 'earned', 'locked'].includes(k))

describe('badges', () => {
  it('found the backend catalog', () => {
    expect(backendCodes.length).toBeGreaterThanOrEqual(55)
  })

  it('every badge the backend can award has artwork and a translation in all four languages', () => {
    for (const code of backendCodes) {
      expect(BADGE_ART[code], `art for ${code}`).toBeDefined()
      for (const [name, locale] of Object.entries({ en, es, fr, el })) {
        expect(translated(locale), `${name} translation of ${code}`).toContain(code)
      }
    }
  })

  it('every artwork entry is a real badge, uses an existing symbol and a known section', () => {
    const groups = BADGE_GROUPS.map((g) => g.key)
    for (const [code, art] of Object.entries(BADGE_ART)) {
      expect(backendCodes, `${code} exists in the backend`).toContain(code)
      expect(GLYPHS[art.glyph], `symbol ${art.glyph}`).toBeDefined()
      expect(groups).toContain(art.group)
      expect([1, 2, 3]).toContain(art.tier)
    }
  })

  it('every section has a translated name', () => {
    for (const g of BADGE_GROUPS) {
      for (const locale of [en, es, fr, el]) expect((locale.badges.groups as Record<string, string>)[g.key]).toBeTruthy()
    }
  })
})
