import { describe, expect, it } from 'vitest'
import { parseIcs } from '../calendars/ics'

const sample = [
  'BEGIN:VCALENDAR', 'VERSION:2.0',
  'BEGIN:VEVENT', 'UID:1', 'DTSTART;VALUE=DATE:20260314', 'SUMMARY:Mum\, birthday', 'RRULE:FREQ=YEARLY', 'END:VEVENT',
  'BEGIN:VEVENT', 'DTSTART:20260302T180000Z', 'SUMMARY:Gym', 'DESCRIPTION:Legs\\nand core', 'RRULE:FREQ=WEEKLY;BYDAY=MO', 'END:VEVENT',
  'BEGIN:VEVENT', 'DTSTART;VALUE=DATE:20260401', 'SUMMARY:A very long', ' title continues', 'END:VEVENT',
  'BEGIN:VEVENT', 'SUMMARY:No date', 'END:VEVENT',
  'END:VCALENDAR',
].join('\r\n')

describe('.ics import', () => {
  const events = parseIcs(sample)
  it('reads dates, titles and repeats', () => {
    expect(events).toHaveLength(3) // the one without a date is skipped
    expect(events[0]).toMatchObject({ title: 'Mum, birthday', date: '2026-03-14', yearly: true, weekly: false })
    expect(events[1]).toMatchObject({ title: 'Gym', date: '2026-03-02', weekly: true, yearly: false, notes: 'Legs\nand core' })
  })
  it('joins folded lines', () => expect(events[2].title).toBe('A very longtitle continues'))
  it('survives rubbish', () => expect(parseIcs('hello')).toEqual([]))
})
