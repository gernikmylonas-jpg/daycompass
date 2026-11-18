import { describe, expect, it } from 'vitest'
import { namesOn, orthodoxEaster } from '../calendars/nameDays'
import { NATIONAL_DAYS, nationalDaysOn, flagOf } from '../calendars/nationalDays'
import { historyOn, HISTORY_COUNT } from '../calendars/history'

const ymd = (d: Date) => `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`

describe('Orthodox Easter', () => {
  it('matches the known dates', () => {
    expect(ymd(orthodoxEaster(2023))).toBe('2023-4-16')
    expect(ymd(orthodoxEaster(2024))).toBe('2024-5-5')
    expect(ymd(orthodoxEaster(2025))).toBe('2025-4-20')
    expect(ymd(orthodoxEaster(2026))).toBe('2026-4-12')
    expect(ymd(orthodoxEaster(2027))).toBe('2027-5-2')
  })
})

describe('name days', () => {
  it('knows fixed feasts', () => {
    expect(namesOn(new Date(2026, 11, 6))).toContain('Νικόλαος')
    expect(namesOn(new Date(2026, 2, 25))).toContain('Βαγγέλης')
    expect(namesOn(new Date(2026, 7, 15))).toContain('Μαρία')
  })
  it('knows the movable feasts around Easter', () => {
    const easter = orthodoxEaster(2026) // 12 April
    expect(namesOn(easter)).toContain('Λάμπρος')
    expect(namesOn(new Date(2026, 3, 5))).toContain('Βάιος') // Palm Sunday
  })
  it('moves St George to Easter Monday when 23 April falls before Easter', () => {
    // 2026: Easter is 12 April, so George stays on 23 April
    expect(namesOn(new Date(2026, 3, 23))).toContain('Γιώργος')
    // 2024: Easter is 5 May, so George moves to Monday 6 May
    expect(namesOn(new Date(2024, 3, 23))).not.toContain('Γιώργος')
    expect(namesOn(new Date(2024, 4, 6))).toContain('Γιώργος')
  })
})

describe('national days', () => {
  it('has unique countries with valid dates', () => {
    const codes = NATIONAL_DAYS.map(([cc]) => cc)
    expect(new Set(codes).size).toBe(codes.length)
    for (const [cc, m, d] of NATIONAL_DAYS) {
      expect(cc).toMatch(/^[A-Z]{2}$/)
      expect(new Date(2024, m - 1, d).getMonth()).toBe(m - 1) // a real day of that month
    }
  })
  it('looks countries up by day', () => {
    expect(nationalDaysOn(3, 25)).toContain('GR')
    expect(nationalDaysOn(7, 14)).toContain('FR')
    expect(flagOf('GR')).toBe('🇬🇷')
  })
})

describe('history', () => {
  it('is a sizeable collection with both languages on every item', () => {
    expect(HISTORY_COUNT).toBeGreaterThanOrEqual(100)
    for (let m = 1; m <= 12; m++) {
      for (let d = 1; d <= 31; d++) for (const h of historyOn(m, d)) {
        expect(h.en.length).toBeGreaterThan(10)
        expect(h.el.length).toBeGreaterThan(10)
      }
    }
  })
  it('finds items by date', () => {
    expect(historyOn(3, 25).some((h) => h.year === 1821)).toBe(true)
    expect(historyOn(7, 20).some((h) => h.year === 1969)).toBe(true)
    expect(historyOn(1, 31)).toEqual([])
  })
})
