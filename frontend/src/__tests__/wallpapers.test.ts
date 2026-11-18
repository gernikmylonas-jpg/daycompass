import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { ART, wallpaperSvg } from '../wallpapers/art'
import en from '../i18n/locales/en'
import es from '../i18n/locales/es'
import fr from '../i18n/locales/fr'
import el from '../i18n/locales/el'

const source = readFileSync(new URL('../../../backend/app/application/services/wallpapers.py', import.meta.url), 'utf-8')
const ids = [...source.matchAll(/\{"id": "([a-z_]+)", "cost": (\d+)/g)].map((m) => ({ id: m[1], cost: Number(m[2]) }))

describe('wallpapers', () => {
  it('found the catalog', () => expect(ids.length).toBeGreaterThanOrEqual(10))

  it('every wallpaper has artwork and a name and description in all four languages', () => {
    for (const { id } of ids) {
      expect(ART[id], `art for ${id}`).toBeDefined()
      for (const [code, locale] of Object.entries({ en, es, fr, el })) {
        const entry = (locale.wallpapers as Record<string, { name: string; description: string }>)[id]
        expect(entry?.name, `${code} name of ${id}`).toBeTruthy()
        expect(entry?.description, `${code} description of ${id}`).toBeTruthy()
      }
    }
  })

  it('draws valid SVG markup and has no art without a catalog entry', () => {
    for (const id of Object.keys(ART)) {
      expect(ids.map((i) => i.id), `${id} is in the backend catalog`).toContain(id)
      const svg = wallpaperSvg(id)
      expect(svg.startsWith('<svg')).toBe(true)
      expect(svg.endsWith('</svg>')).toBe(true)
      expect(svg).not.toMatch(/NaN|undefined/)
      expect(svg.length).toBeGreaterThan(500)
    }
    expect(wallpaperSvg('nope')).toBe('')
  })

  it('has sensible, distinct prices', () => {
    for (const { cost } of ids) expect(cost).toBeGreaterThanOrEqual(5)
    expect(new Set(ids.map((i) => i.id)).size).toBe(ids.length)
  })
})
