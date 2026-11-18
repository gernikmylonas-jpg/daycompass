// A small .ics reader: just enough of iCalendar (all-day or timed VEVENTs, title, notes, yearly/weekly repeat)
// to bring events from another calendar app into DayCompass. Anything else in the file is ignored.
export interface IcsEvent { title: string; date: string; notes: string | null; yearly: boolean; weekly: boolean }

const unescapeText = (s: string) => s.replace(/\\n/gi, '\n').replace(/\\([,;\\])/g, '$1')

export function parseIcs(text: string): IcsEvent[] {
  // lines that start with a space or tab continue the previous one
  const lines = text.replace(/\r\n?/g, '\n').replace(/\n[ \t]/g, '').split('\n')
  const out: IcsEvent[] = []
  let cur: Partial<IcsEvent> & { rrule?: string } | null = null
  for (const line of lines) {
    if (line === 'BEGIN:VEVENT') { cur = {}; continue }
    if (line === 'END:VEVENT') {
      if (cur?.title && cur.date) {
        out.push({
          title: cur.title.slice(0, 100), date: cur.date, notes: cur.notes ? cur.notes.slice(0, 500) : null,
          yearly: /FREQ=YEARLY/i.test(cur.rrule ?? ''), weekly: /FREQ=WEEKLY/i.test(cur.rrule ?? ''),
        })
      }
      cur = null
      continue
    }
    if (!cur) continue
    const colon = line.indexOf(':')
    if (colon < 0) continue
    const name = line.slice(0, colon).split(';')[0].toUpperCase()
    const value = line.slice(colon + 1)
    if (name === 'SUMMARY') cur.title = unescapeText(value).trim()
    else if (name === 'DESCRIPTION') cur.notes = unescapeText(value).trim()
    else if (name === 'RRULE') cur.rrule = value
    else if (name === 'DTSTART') {
      const m = /^(\d{4})(\d{2})(\d{2})/.exec(value)
      if (m) cur.date = `${m[1]}-${m[2]}-${m[3]}`
    }
  }
  return out
}
