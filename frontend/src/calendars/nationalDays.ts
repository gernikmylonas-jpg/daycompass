// The main national day (independence, constitution, republic or statehood day) of each country.
// Some countries celebrate several; this lists the one most often used. Names come from Intl.DisplayNames.
// [ISO country code, month, day]
export const NATIONAL_DAYS: [string, number, number][] = [
  ['AF', 8, 19], ['AL', 11, 28], ['DZ', 11, 1], ['AD', 9, 8], ['AO', 11, 11], ['AG', 11, 1], ['AR', 7, 9], ['AM', 9, 21],
  ['AU', 1, 26], ['AT', 10, 26], ['AZ', 5, 28], ['BS', 7, 10], ['BH', 12, 16], ['BD', 3, 26], ['BB', 11, 30], ['BY', 7, 3],
  ['BE', 7, 21], ['BZ', 9, 21], ['BJ', 8, 1], ['BT', 12, 17], ['BO', 8, 6], ['BA', 11, 25], ['BW', 9, 30], ['BR', 9, 7],
  ['BN', 2, 23], ['BG', 3, 3], ['BF', 12, 11], ['BI', 7, 1], ['KH', 11, 9], ['CM', 5, 20], ['CA', 7, 1], ['CV', 7, 5],
  ['CF', 12, 1], ['TD', 8, 11], ['CL', 9, 18], ['CN', 10, 1], ['CO', 7, 20], ['KM', 7, 6], ['CG', 8, 15], ['CD', 6, 30],
  ['CR', 9, 15], ['CI', 8, 7], ['HR', 5, 30], ['CU', 1, 1], ['CY', 10, 1], ['CZ', 10, 28], ['DK', 6, 5], ['DJ', 6, 27],
  ['DM', 11, 3], ['DO', 2, 27], ['EC', 8, 10], ['EG', 7, 23], ['SV', 9, 15], ['GQ', 10, 12], ['ER', 5, 24], ['EE', 2, 24],
  ['SZ', 9, 6], ['ET', 5, 28], ['FJ', 10, 10], ['FI', 12, 6], ['FR', 7, 14], ['GA', 8, 17], ['GM', 2, 18], ['GE', 5, 26],
  ['DE', 10, 3], ['GH', 3, 6], ['GR', 3, 25], ['GD', 2, 7], ['GT', 9, 15], ['GN', 10, 2], ['GW', 9, 24], ['GY', 5, 26],
  ['HT', 1, 1], ['HN', 9, 15], ['HU', 8, 20], ['IS', 6, 17], ['IN', 8, 15], ['ID', 8, 17], ['IR', 2, 11], ['IQ', 10, 3],
  ['IE', 3, 17], ['IT', 6, 2], ['JM', 8, 6], ['JP', 2, 11], ['JO', 5, 25], ['KZ', 12, 16], ['KE', 12, 12], ['KI', 7, 12],
  ['XK', 2, 17], ['KW', 2, 25], ['KG', 8, 31], ['LA', 12, 2], ['LV', 11, 18], ['LB', 11, 22], ['LS', 10, 4], ['LR', 7, 26],
  ['LY', 12, 24], ['LI', 8, 15], ['LT', 2, 16], ['LU', 6, 23], ['MG', 6, 26], ['MW', 7, 6], ['MY', 8, 31], ['MV', 7, 26],
  ['ML', 9, 22], ['MT', 9, 21], ['MH', 5, 1], ['MR', 11, 28], ['MU', 3, 12], ['MX', 9, 16], ['FM', 11, 3], ['MD', 8, 27],
  ['MC', 11, 19], ['ME', 5, 21], ['MA', 7, 30], ['MZ', 6, 25], ['MM', 1, 4], ['NA', 3, 21], ['NR', 1, 31], ['NP', 9, 20],
  ['NL', 4, 27], ['NZ', 2, 6], ['NI', 9, 15], ['NE', 8, 3], ['NG', 10, 1], ['KP', 9, 9], ['MK', 9, 8], ['NO', 5, 17],
  ['OM', 11, 18], ['PK', 8, 14], ['PW', 10, 1], ['PA', 11, 3], ['PG', 9, 16], ['PY', 5, 15], ['PE', 7, 28], ['PH', 6, 12],
  ['PL', 11, 11], ['PT', 6, 10], ['QA', 12, 18], ['RO', 12, 1], ['RU', 6, 12], ['RW', 7, 4], ['KN', 9, 19], ['LC', 2, 22],
  ['VC', 10, 27], ['WS', 6, 1], ['SM', 9, 3], ['ST', 7, 12], ['SA', 9, 23], ['SN', 4, 4], ['RS', 2, 15], ['SC', 6, 29],
  ['SL', 4, 27], ['SG', 8, 9], ['SK', 9, 1], ['SI', 6, 25], ['SB', 7, 7], ['SO', 7, 1], ['ZA', 4, 27], ['KR', 8, 15],
  ['SS', 7, 9], ['ES', 10, 12], ['LK', 2, 4], ['SD', 1, 1], ['SR', 11, 25], ['SE', 6, 6], ['CH', 8, 1], ['SY', 4, 17],
  ['TW', 10, 10], ['TJ', 9, 9], ['TZ', 12, 9], ['TH', 12, 5], ['TL', 5, 20], ['TG', 4, 27], ['TT', 8, 31], ['TN', 3, 20],
  ['TR', 10, 29], ['TM', 9, 27], ['TV', 10, 1], ['UG', 10, 9], ['UA', 8, 24], ['AE', 12, 2], ['US', 7, 4], ['UY', 8, 25],
  ['UZ', 9, 1], ['VU', 7, 30], ['VE', 7, 5], ['VN', 9, 2], ['YE', 5, 22], ['ZM', 10, 24], ['ZW', 4, 18],
]

const BY_DAY = new Map<string, string[]>()
for (const [cc, m, d] of NATIONAL_DAYS) BY_DAY.set(`${m}-${d}`, [...(BY_DAY.get(`${m}-${d}`) ?? []), cc])

/** ISO codes of the countries whose national day is on this month/day. */
export const nationalDaysOn = (month: number, day: number): string[] => BY_DAY.get(`${month}-${day}`) ?? []

/** A flag emoji from an ISO country code. */
export const flagOf = (cc: string) => String.fromCodePoint(...[...cc.toUpperCase()].map((c) => 0x1f1a5 + c.charCodeAt(0)))
