// One place that decides how dates look: always day / month / year, in every language.

const two = (n: number) => String(n).padStart(2, '0')

export function parseIso(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function toIso(d: Date): string {
  return `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())}`
}

/** "2026-11-17" or a Date -> "17/11/2026" */
export function formatDate(value: string | Date): string {
  const d = typeof value === 'string' ? parseIso(value) : value
  return `${two(d.getDate())}/${two(d.getMonth() + 1)}/${d.getFullYear()}`
}

/** 24-hour clock, e.g. "18:05" */
export function formatTime(d: Date): string {
  return `${two(d.getHours())}:${two(d.getMinutes())}`
}

/** "17/11/2026, 18:05" */
export function formatDateTime(d: Date): string {
  return `${formatDate(d)}, ${formatTime(d)}`
}

export function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}
