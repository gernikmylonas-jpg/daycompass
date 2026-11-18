import { describe, expect, it } from 'vitest'
import {
  eclipsesForYear, moonAltitudeAtLunarEclipse, moonStateAt, phaseEventsForYear, seasonsForYear, sunTimes,
} from '../astronomy'

const utc = (iso: string) => Date.parse(iso + ':00Z')
const minutesApart = (a: Date | number, b: string) => Math.abs(+a - utc(b)) / 60000

describe('phases of the Moon', () => {
  const find = (year: number, kind: string, month: number) =>
    phaseEventsForYear(year).find((e) => e.kind === kind && e.date.getUTCMonth() + 1 === month)!

  it.each([
    [2000, 'new', 1, '2000-01-06T18:14'],
    [2024, 'full', 1, '2024-01-25T17:54'],
    [2024, 'new', 4, '2024-04-08T18:21'],
    [2026, 'full', 3, '2026-03-03T11:38'],
    [2026, 'new', 8, '2026-08-12T17:37'],
  ])('%i %s moon in month %i is at %s (UT)', (year, kind, month, expected) => {
    expect(minutesApart(find(year, kind, month).date, expected)).toBeLessThan(5)
  })

  it('knows when the Moon is full or new', () => {
    expect(moonStateAt(new Date(utc('2026-03-03T11:38'))).illumination).toBeGreaterThan(0.99)
    expect(moonStateAt(new Date(utc('2026-08-12T17:37'))).illumination).toBeLessThan(0.01)
  })
})

describe('eclipses', () => {
  const known: [string, 'solar' | 'lunar', string][] = [
    ['2024-03-25T07:13', 'lunar', 'penumbral'], ['2024-04-08T18:17', 'solar', 'total'],
    ['2024-09-18T02:44', 'lunar', 'partial'], ['2024-10-02T18:46', 'solar', 'annular'],
    ['2025-03-14T06:59', 'lunar', 'total'], ['2025-03-29T10:48', 'solar', 'partial'],
    ['2025-09-07T18:11', 'lunar', 'total'], ['2025-09-21T19:43', 'solar', 'partial'],
    ['2026-02-17T12:12', 'solar', 'annular'], ['2026-03-03T11:33', 'lunar', 'total'],
    ['2026-08-12T17:46', 'solar', 'total'], ['2026-08-28T04:13', 'lunar', 'partial'],
    ['2027-02-06T16:00', 'solar', 'annular'], ['2027-02-20T23:13', 'lunar', 'penumbral'],
    ['2027-08-02T10:07', 'solar', 'total'],
  ]

  it.each(known)('%s %s eclipse is %s', (iso, kind, type) => {
    const year = Number(iso.slice(0, 4))
    const e = eclipsesForYear(year).filter((x) => x.kind === kind)
      .sort((a, b) => Math.abs(+a.date - utc(iso)) - Math.abs(+b.date - utc(iso)))[0]
    expect(e.type).toBe(type)
    expect(minutesApart(e.date, iso)).toBeLessThan(15)
  })

  it('finds a realistic number of eclipses in the century (about 450)', () => {
    let total = 0
    for (let y = 2000; y <= 2100; y++) {
      const n = eclipsesForYear(y).length
      expect(n).toBeGreaterThanOrEqual(4)
      expect(n).toBeLessThanOrEqual(7)
      total += n
    }
    expect(total).toBeGreaterThan(430)
    expect(total).toBeLessThan(480)
  })
})

describe('equinoxes and solstices 2026', () => {
  it('match the published times', () => {
    const [mar, jun, sep, dec] = seasonsForYear(2026)
    expect(minutesApart(mar.date, '2026-03-20T14:46')).toBeLessThan(5)
    expect(minutesApart(jun.date, '2026-06-21T08:24')).toBeLessThan(5)
    expect(minutesApart(sep.date, '2026-09-23T00:05')).toBeLessThan(5)
    expect(minutesApart(dec.date, '2026-12-21T20:50')).toBeLessThan(5)
  })
})

describe('the Sun from a place', () => {
  const athens = { lat: 37.98, lon: 23.73 }
  const london = { lat: 51.5, lon: -0.12 }

  it('sunrise and sunset at the 2026 June solstice', () => {
    const a = sunTimes(utc('2026-06-20T21:00'), athens) // local midnight in Athens (UTC+3)
    expect(minutesApart(a.sunrise!, '2026-06-21T03:00')).toBeLessThan(8)
    expect(minutesApart(a.sunset!, '2026-06-21T17:47')).toBeLessThan(8)
    const l = sunTimes(utc('2026-06-20T23:00'), london) // local midnight in London (UTC+1)
    expect(minutesApart(l.sunrise!, '2026-06-21T03:43')).toBeLessThan(8)
    expect(minutesApart(l.sunset!, '2026-06-21T20:21')).toBeLessThan(8)
  })

  it('day length is about 12 hours at an equinox and longest at the solstice', () => {
    const equinox = sunTimes(utc('2026-03-19T22:00'), athens)
    expect(Math.abs(equinox.dayLengthMinutes - 12 * 60 - 8)).toBeLessThan(12)
    expect(sunTimes(utc('2026-06-20T21:00'), athens).dayLengthMinutes).toBeGreaterThan(14 * 60 + 40)
  })

  it('reports the midnight sun and the polar night', () => {
    const tromso = { lat: 69.65, lon: 18.96 }
    expect(sunTimes(utc('2026-06-20T22:00'), tromso).polar).toBe('day')
    expect(sunTimes(utc('2026-12-20T23:00'), tromso).polar).toBe('night')
  })
})

describe('is a lunar eclipse visible from a place?', () => {
  const newYork = { lat: 40.71, lon: -74.0 }
  const tokyo = { lat: 35.68, lon: 139.69 }
  const athens = { lat: 37.98, lon: 23.73 }

  it('the March 2025 total lunar eclipse: seen from New York, not from Tokyo', () => {
    const t = utc('2025-03-14T06:59')
    expect(moonAltitudeAtLunarEclipse(t, newYork)).toBeGreaterThan(5)
    expect(moonAltitudeAtLunarEclipse(t, tokyo)).toBeLessThan(0)
  })

  it('the September 2025 total lunar eclipse: seen from Athens, not from New York', () => {
    const t = utc('2025-09-07T18:11')
    expect(moonAltitudeAtLunarEclipse(t, athens)).toBeGreaterThan(5)
    expect(moonAltitudeAtLunarEclipse(t, newYork)).toBeLessThan(0)
  })
})
