import { describe, expect, it } from 'vitest'
import { skyEventsForYear, planetsNow, type PlanetId } from '../planets'

const DAY = 86_400_000
const find = (year: number, kind: string, planet?: PlanetId, side?: string) =>
  skyEventsForYear(year).filter((e) => e.kind === kind && (!planet || e.planets[0] === planet) && (!side || e.side === side))
const near = (date: Date, iso: string, days = 2) => Math.abs(date.getTime() - Date.parse(iso)) <= days * DAY

describe('planetary events match published dates (within two days)', () => {
  it('oppositions', () => {
    expect(near(find(2025, 'opposition', 'mars')[0].date, '2025-01-16')).toBe(true)
    expect(find(2025, 'opposition', 'jupiter')).toHaveLength(0) // Jupiter was at opposition on 7 Dec 2024 and again on 10 Jan 2026
    expect(near(find(2024, 'opposition', 'jupiter')[0].date, '2024-12-07')).toBe(true)
    expect(near(find(2025, 'opposition', 'saturn')[0].date, '2025-09-21')).toBe(true)
    expect(near(find(2025, 'opposition', 'neptune')[0].date, '2025-09-23')).toBe(true)
    expect(near(find(2025, 'opposition', 'uranus')[0].date, '2025-11-21')).toBe(true)
    expect(near(find(2026, 'opposition', 'jupiter')[0].date, '2026-01-10')).toBe(true)
    expect(near(find(2026, 'opposition', 'saturn')[0].date, '2026-10-04')).toBe(true)
    expect(near(find(2027, 'opposition', 'mars')[0].date, '2027-02-19')).toBe(true)
  })
  it('greatest elongations of Mercury and Venus', () => {
    const venus = find(2025, 'greatestElongation', 'venus', 'west')[0]
    expect(near(venus.date, '2025-06-01', 3)).toBe(true)
    expect(venus.degrees).toBeGreaterThan(45)
    expect(venus.degrees).toBeLessThan(47)
    expect(near(find(2025, 'greatestElongation', 'mercury', 'east')[0].date, '2025-03-08', 3)).toBe(true)
    expect(near(find(2025, 'greatestElongation', 'mercury', 'west')[0].date, '2025-04-21', 3)).toBe(true)
  })
  it('the great conjunction of Jupiter and Saturn in 2020', () => {
    const c = skyEventsForYear(2020).find((e) => e.kind === 'conjunction' && e.planets.includes('jupiter') && e.planets.includes('saturn'))!
    expect(near(c.date, '2020-12-21')).toBe(true)
    expect(c.degrees!).toBeLessThan(0.5)
  })
  it("Earth's perihelion and aphelion", () => {
    expect(near(find(2025, 'perihelion')[0].date, '2025-01-04', 3)).toBe(true)
    expect(near(find(2025, 'aphelion')[0].date, '2025-07-03', 3)).toBe(true) // the elements give the Earth's distance to about a day or two
  })
})

describe('sky today', () => {
  it('classifies every planet', () => {
    const now = planetsNow(new Date('2025-01-10T12:00:00Z'))
    expect(now).toHaveLength(7)
    expect(now.find((p) => p.planet === 'jupiter')!.position).toBe('evening')
    expect(now.find((p) => p.planet === 'mars')!.position).toBe('allNight')
  })
  it('returns each year in order, quickly cached', () => {
    const a = skyEventsForYear(2030)
    expect(a).toBe(skyEventsForYear(2030))
    for (let i = 1; i < a.length; i++) expect(a[i].date.getTime()).toBeGreaterThanOrEqual(a[i - 1].date.getTime())
  })
})

