import { describe, expect, it } from 'vitest'
import { daysInMonth, formatDate, formatDateTime, parseIso, toIso } from '../i18n/dates'

describe('dates are always day / month / year', () => {
  it('formats ISO strings and Dates', () => {
    expect(formatDate('2026-02-17')).toBe('17/02/2026')
    expect(formatDate(new Date(2026, 10, 5))).toBe('05/11/2026')
    expect(formatDateTime(new Date(2026, 10, 5, 9, 7))).toBe('05/11/2026, 09:07')
  })

  it('round-trips without timezone drift', () => {
    for (const iso of ['2000-01-01', '2024-02-29', '2100-12-31']) expect(toIso(parseIso(iso))).toBe(iso)
  })

  it('knows the length of a month, including leap years', () => {
    expect(daysInMonth(2024, 2)).toBe(29)
    expect(daysInMonth(2026, 2)).toBe(28)
    expect(daysInMonth(2100, 2)).toBe(28) // 2100 is not a leap year
    expect(daysInMonth(2026, 11)).toBe(30)
  })
})
