// Small helpers shared by the budget and savings panels. Amounts travel as whole cents.
export const CATEGORY_ICON: Record<string, string> = {
  food: '🍽️', home: '🏠', transport: '🚌', health: '💊', fun: '🎬', shopping: '🛍️', bills: '🧾', travel: '✈️', other: '📦',
  salary: '💼', gift: '🎁', side: '🧰', other_income: '➕',
  lodging: '🛏️', activities: '🎟️',
}

export const CURRENCIES = ['EUR', 'USD', 'GBP', 'CHF', 'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RON', 'BGN', 'TRY', 'JPY', 'CNY', 'INR', 'AUD', 'CAD', 'NZD', 'BRL', 'MXN', 'AED', 'ZAR']

/** 1234 cents -> "€12.34" in the reader's language (no rounding of the cents). */
export function formatMoney(cents: number, currency: string, locale: string): string {
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(cents / 100)
  } catch {
    return `${(cents / 100).toFixed(2)} ${currency}`
  }
}

/** "12,5" or "12.5" typed by a person -> 12.5 (or null when it is not a number). */
export function parseAmount(text: string | number | null | undefined): number | null {
  if (text === null || text === undefined || text === '') return null
  const n = typeof text === 'number' ? text : Number(String(text).trim().replace(',', '.'))
  return Number.isFinite(n) ? n : null
}
