// Moon phases, eclipses and the Sun's seasons, computed in the browser with the algorithms from
// Jean Meeus, "Astronomical Algorithms" (2nd ed.): ch. 27 (equinoxes and solstices),
// ch. 49 (phases of the Moon) and ch. 54 (eclipses). Accuracy is a few minutes for 1900-2100,
// which is far more than a calendar needs. All results are absolute instants (JavaScript Dates).

const RAD = Math.PI / 180
const rad = (deg: number) => deg * RAD
const sinD = (deg: number) => Math.sin(rad(deg))
const cosD = (deg: number) => Math.cos(rad(deg))

const UNIX_JD = 2440587.5 // Julian Day of 1970-01-01T00:00Z
const MS_PER_DAY = 86_400_000

/** Difference between dynamical time (what the formulas give) and UT, in seconds. */
function deltaT(year: number): number {
  if (year < 1900) {
    const t = (year - 1900)
    return -2.79 + 1.494119 * t - 0.0598939 * t ** 2 + 0.0061966 * t ** 3 - 0.000197 * t ** 4
  }
  if (year < 1920) {
    const t = year - 1900
    return -2.79 + 1.494119 * t - 0.0598939 * t ** 2 + 0.0061966 * t ** 3 - 0.000197 * t ** 4
  }
  if (year < 1941) {
    const t = year - 1920
    return 21.2 + 0.84493 * t - 0.0761 * t ** 2 + 0.0020936 * t ** 3
  }
  if (year < 1961) {
    const t = year - 1950
    return 29.07 + 0.407 * t - t ** 2 / 233 + t ** 3 / 2547
  }
  if (year < 1986) {
    const t = year - 1975
    return 45.45 + 1.067 * t - t ** 2 / 260 - t ** 3 / 718
  }
  if (year < 2005) {
    const t = year - 2000
    return 63.86 + 0.3345 * t - 0.060374 * t ** 2 + 0.0017275 * t ** 3 + 0.000651814 * t ** 4 + 0.00002373599 * t ** 5
  }
  if (year < 2050) {
    const t = year - 2000
    return 62.92 + 0.32217 * t + 0.005589 * t ** 2
  }
  const u = (year - 1820) / 100
  return year < 2150 ? -20 + 32 * u ** 2 - 0.5628 * (2150 - year) : -20 + 32 * u ** 2
}

/** Julian Ephemeris Day -> the instant in UT. */
function jdeToDate(jde: number): Date {
  const approxYear = 2000 + (jde - 2451545) / 365.25
  const jd = jde - deltaT(approxYear) / 86400
  return new Date((jd - UNIX_JD) * MS_PER_DAY)
}

// ── phases of the Moon (ch. 49) ──────────────────────────────────────────

export type PhaseKind = 'new' | 'first' | 'full' | 'last'

export interface PhaseEvent {
  kind: PhaseKind
  date: Date
}

interface Lunation {
  k: number
  T: number
  E: number
  M: number // Sun's mean anomaly
  Mp: number // Moon's mean anomaly
  F: number // Moon's argument of latitude
  Om: number // longitude of the ascending node
  meanJde: number
}

function lunation(k: number): Lunation {
  const T = k / 1236.85
  return {
    k,
    T,
    E: 1 - 0.002516 * T - 0.0000074 * T ** 2,
    M: 2.5534 + 29.1053567 * k - 0.0000014 * T ** 2 - 0.00000011 * T ** 3,
    Mp: 201.5643 + 385.81693528 * k + 0.0107582 * T ** 2 + 0.00001238 * T ** 3 - 0.000000058 * T ** 4,
    F: 160.7108 + 390.67050284 * k - 0.0016118 * T ** 2 - 0.00000227 * T ** 3 + 0.000000011 * T ** 4,
    Om: 124.7746 - 1.56375588 * k + 0.0020672 * T ** 2 + 0.00000215 * T ** 3,
    meanJde: 2451550.09766 + 29.530588861 * k + 0.00015437 * T ** 2 - 0.00000015 * T ** 3 + 0.00000000073 * T ** 4,
  }
}

// [coefficient for new moon, for full moon, power of E, M, M', F, Omega]
const NEW_FULL_TERMS: [number, number, number, number, number, number, number][] = [
  [-0.4072, -0.40614, 0, 0, 1, 0, 0], // M' (new moon: -0.40720)
  [0.17241, 0.17302, 1, 1, 0, 0, 0],
  [0.01608, 0.01614, 0, 0, 2, 0, 0],
  [0.01039, 0.01043, 0, 0, 0, 2, 0],
  [0.00739, 0.00734, 1, -1, 1, 0, 0],
  [-0.00514, -0.00515, 1, 1, 1, 0, 0],
  [0.00208, 0.00209, 2, 2, 0, 0, 0],
  [-0.00111, -0.00111, 0, 0, 1, -2, 0],
  [-0.00057, -0.00057, 0, 0, 1, 2, 0],
  [0.00056, 0.00056, 1, 1, 2, 0, 0],
  [-0.00042, -0.00042, 0, 0, 3, 0, 0],
  [0.00042, 0.00042, 1, 1, 0, 2, 0],
  [0.00038, 0.00038, 1, 1, 0, -2, 0],
  [-0.00024, -0.00024, 1, -1, 2, 0, 0],
  [-0.00017, -0.00017, 0, 0, 0, 0, 1],
  [-0.00007, -0.00007, 0, 2, 1, 0, 0],
  [0.00004, 0.00004, 0, 0, 2, -2, 0],
  [0.00004, 0.00004, 0, 3, 0, 0, 0],
  [0.00003, 0.00003, 0, 1, 1, -2, 0],
  [0.00003, 0.00003, 0, 0, 2, 2, 0],
  [-0.00003, -0.00003, 0, 1, 1, 2, 0],
  [0.00003, 0.00003, 0, -1, 1, 2, 0],
  [-0.00002, -0.00002, 0, -1, 1, -2, 0],
  [-0.00002, -0.00002, 0, 1, 3, 0, 0],
  [0.00002, 0.00002, 0, 0, 4, 0, 0],
]

const QUARTER_TERMS: [number, number, number, number, number, number][] = [
  [-0.62801, 0, 0, 1, 0, 0],
  [0.17172, 1, 1, 0, 0, 0],
  [-0.01183, 1, 1, 1, 0, 0],
  [0.00862, 0, 0, 2, 0, 0],
  [0.00804, 0, 0, 0, 2, 0],
  [0.00454, 1, -1, 1, 0, 0],
  [0.00204, 2, 2, 0, 0, 0],
  [-0.0018, 0, 0, 1, -2, 0],
  [-0.0007, 0, 0, 1, 2, 0],
  [-0.0004, 0, 0, 3, 0, 0],
  [-0.00034, 1, -1, 2, 0, 0],
  [0.00032, 1, 1, 0, 2, 0],
  [0.00032, 1, 1, 0, -2, 0],
  [-0.00028, 2, 2, 1, 0, 0],
  [0.00027, 1, 1, 2, 0, 0],
  [-0.00017, 0, 0, 0, 0, 1],
  [-0.00005, 0, -1, 1, -2, 0],
  [0.00004, 0, 0, 2, 2, 0],
  [-0.00004, 0, 1, 1, 2, 0],
  [0.00004, 0, -2, 1, 0, 0],
  [0.00003, 0, 1, 1, -2, 0],
  [0.00003, 0, 3, 0, 0, 0],
  [0.00002, 0, 0, 2, -2, 0],
  [0.00002, 0, -1, 1, 2, 0],
  [-0.00002, 0, 1, 3, 0, 0],
]

const PLANETARY_COEFF = [0.000325, 0.000165, 0.000164, 0.000126, 0.00011, 0.000062, 0.00006, 0.000056, 0.000047, 0.000042, 0.00004, 0.000037, 0.000035, 0.000023]

function planetaryCorrection(k: number, T: number): number {
  const a = [
    299.77 + 0.107408 * k - 0.009173 * T ** 2,
    251.88 + 0.016321 * k,
    251.83 + 26.651886 * k,
    349.42 + 36.412478 * k,
    84.66 + 18.206239 * k,
    141.74 + 53.303771 * k,
    207.14 + 2.453732 * k,
    154.84 + 7.30686 * k,
    34.52 + 27.261239 * k,
    207.19 + 0.121824 * k,
    291.34 + 1.844379 * k,
    161.72 + 24.198154 * k,
    239.56 + 25.513099 * k,
    331.55 + 3.592518 * k,
  ]
  return a.reduce((sum, angle, i) => sum + PLANETARY_COEFF[i] * sinD(angle), 0)
}

/** JDE of the phase at lunation number k (integer = new, +.25 first quarter, +.5 full, +.75 last). */
function phaseJde(k: number): number {
  const l = lunation(k)
  const fraction = ((k % 1) + 1) % 1
  let correction = 0
  if (fraction === 0 || fraction === 0.5) {
    const col = fraction === 0 ? 0 : 1
    for (const term of NEW_FULL_TERMS) {
      const [, , e, m, mp, f, om] = term
      correction += term[col] * l.E ** e * sinD(m * l.M + mp * l.Mp + f * l.F + om * l.Om)
    }
  } else {
    for (const [c, e, m, mp, f, om] of QUARTER_TERMS) {
      correction += c * l.E ** e * sinD(m * l.M + mp * l.Mp + f * l.F + om * l.Om)
    }
    const w =
      0.00306 - 0.00038 * l.E * cosD(l.M) + 0.00026 * cosD(l.Mp) - 0.00002 * cosD(l.Mp - l.M) +
      0.00002 * cosD(l.Mp + l.M) + 0.00002 * cosD(2 * l.F)
    correction += fraction === 0.25 ? w : -w
  }
  return l.meanJde + correction + planetaryCorrection(k, l.T)
}

const KINDS: PhaseKind[] = ['new', 'first', 'full', 'last']
const kOf = (instant: number) => Math.floor(((instant / MS_PER_DAY + UNIX_JD - 2451550.09766) / 29.530588861))

const phaseCache = new Map<number, PhaseEvent[]>()

/** Every new / first-quarter / full / last-quarter moon in a calendar year (UT), in order. */
export function phaseEventsForYear(year: number): PhaseEvent[] {
  const cached = phaseCache.get(year)
  if (cached) return cached
  const start = Date.UTC(year, 0, 1)
  const end = Date.UTC(year + 1, 0, 1)
  const events: PhaseEvent[] = []
  for (let k = kOf(start) - 1; ; k++) {
    for (let q = 0; q < 4; q++) {
      const date = jdeToDate(phaseJde(k + q / 4))
      if (date.getTime() >= start && date.getTime() < end) events.push({ kind: KINDS[q], date })
    }
    if (jdeToDate(phaseJde(k)).getTime() > end) break
  }
  phaseCache.set(year, events)
  return events
}

export type PhaseName =
  | 'new' | 'waxingCrescent' | 'firstQuarter' | 'waxingGibbous'
  | 'full' | 'waningGibbous' | 'lastQuarter' | 'waningCrescent'

export interface MoonState {
  /** 0 = new, 0.25 = first quarter, 0.5 = full, 0.75 = last quarter */
  cycle: number
  illumination: number // 0..1
  ageDays: number
  name: PhaseName
  waxing: boolean
}

function nameOf(cycle: number): PhaseName {
  const bands: [number, PhaseName][] = [
    [0.0339, 'new'], [0.2161, 'waxingCrescent'], [0.2839, 'firstQuarter'], [0.4661, 'waxingGibbous'],
    [0.5339, 'full'], [0.7161, 'waningGibbous'], [0.7839, 'lastQuarter'], [0.9661, 'waningCrescent'],
  ]
  for (const [limit, name] of bands) if (cycle < limit) return name
  return 'new'
}

/** Phase of the Moon at an instant, interpolated between the exact quarter events around it. */
export function moonStateAt(date: Date): MoonState {
  const t = date.getTime()
  const year = date.getUTCFullYear()
  const all = [...phaseEventsForYear(year - 1), ...phaseEventsForYear(year), ...phaseEventsForYear(year + 1)]
  let i = all.findIndex((e) => e.date.getTime() > t) - 1
  if (i < 0) i = 0
  const prev = all[i]
  const next = all[i + 1]
  const base = KINDS.indexOf(prev.kind) / 4
  const cycle = (base + 0.25 * ((t - prev.date.getTime()) / (next.date.getTime() - prev.date.getTime()))) % 1
  // age: time since the last new moon
  let j = i
  while (j > 0 && all[j].kind !== 'new') j--
  return {
    cycle,
    illumination: (1 - Math.cos(2 * Math.PI * cycle)) / 2,
    ageDays: (t - all[j].date.getTime()) / MS_PER_DAY,
    name: nameOf(cycle),
    waxing: cycle < 0.5,
  }
}

/** The next time the Moon reaches the given phase after an instant. */
export function nextPhase(kind: PhaseKind, after: Date): PhaseEvent {
  const year = after.getUTCFullYear()
  const all = [...phaseEventsForYear(year), ...phaseEventsForYear(year + 1)]
  return all.find((e) => e.kind === kind && e.date.getTime() > after.getTime()) ?? all[all.length - 1]
}

// ── eclipses (ch. 54) ────────────────────────────────────────────────────

export type EclipseKind = 'solar' | 'lunar'
export type EclipseType = 'total' | 'annular' | 'hybrid' | 'partial' | 'penumbral'

export interface Eclipse {
  kind: EclipseKind
  type: EclipseType
  date: Date // moment of greatest eclipse (UT)
  gamma: number
  magnitude: number | null // partial solar / lunar umbral magnitude; null for central solar eclipses
}

function eclipseAt(k: number, kind: EclipseKind): Eclipse | null {
  const l = lunation(k)
  if (Math.abs(sinD(l.F)) > 0.36) return null // the Moon is too far from the ecliptic

  const { E, M, Mp, Om } = l
  const F1 = l.F - 0.02665 * sinD(Om)
  const A1 = 299.77 + 0.107408 * k - 0.009173 * l.T ** 2
  const lead = kind === 'solar' ? [-0.4075, 0.1721] : [-0.4065, 0.1727]

  const jde =
    l.meanJde +
    lead[0] * sinD(Mp) + lead[1] * E * sinD(M) + 0.0161 * sinD(2 * Mp) - 0.0097 * sinD(2 * F1) +
    0.0073 * E * sinD(Mp - M) - 0.005 * E * sinD(Mp + M) - 0.0023 * sinD(Mp - 2 * F1) +
    0.0021 * E * sinD(2 * M) + 0.0012 * sinD(Mp + 2 * F1) + 0.0006 * E * sinD(2 * Mp + M) -
    0.0004 * sinD(3 * Mp) - 0.0003 * E * sinD(M + 2 * F1) + 0.0003 * sinD(A1) -
    0.0002 * E * sinD(M - 2 * F1) - 0.0002 * E * sinD(2 * Mp - M) - 0.0002 * sinD(Om)

  const P =
    0.207 * E * sinD(M) + 0.0024 * E * sinD(2 * M) - 0.0392 * sinD(Mp) + 0.0116 * sinD(2 * Mp) -
    0.0073 * E * sinD(Mp + M) + 0.0067 * E * sinD(Mp - M) + 0.0118 * sinD(2 * F1)
  const Q =
    5.2207 - 0.0048 * E * cosD(M) + 0.002 * E * cosD(2 * M) - 0.3299 * cosD(Mp) -
    0.006 * E * cosD(Mp + M) + 0.0041 * E * cosD(Mp - M)
  const W = Math.abs(cosD(F1))
  const gamma = (P * cosD(F1) + Q * sinD(F1)) * (1 - 0.0048 * W)
  const u = 0.0059 + 0.0046 * E * cosD(M) - 0.0182 * cosD(Mp) + 0.0004 * cosD(2 * Mp) - 0.0005 * cosD(M + Mp)
  const g = Math.abs(gamma)
  const date = jdeToDate(jde)

  if (kind === 'solar') {
    if (g > 1.5433 + u) return null
    if (g < 0.9972) {
      let type: EclipseType
      if (u < 0) type = 'total'
      else if (u > 0.0047) type = 'annular'
      else type = u < 0.00464 * Math.sqrt(1 - gamma * gamma) ? 'hybrid' : 'annular'
      return { kind, type, date, gamma, magnitude: null }
    }
    if (g - 0.9972 < Math.abs(u)) return { kind, type: u < 0 ? 'total' : 'annular', date, gamma, magnitude: null }
    return { kind, type: 'partial', date, gamma, magnitude: (1.5433 + u - g) / (0.5461 + 2 * u) }
  }

  const penumbral = (1.5573 + u - g) / 0.545
  const umbral = (1.0128 - u - g) / 0.545
  if (penumbral <= 0) return null
  if (umbral >= 1) return { kind, type: 'total', date, gamma, magnitude: umbral }
  if (umbral > 0) return { kind, type: 'partial', date, gamma, magnitude: umbral }
  return { kind, type: 'penumbral', date, gamma, magnitude: penumbral }
}

const eclipseCache = new Map<number, Eclipse[]>()

/** All solar and lunar eclipses with greatest eclipse in the given calendar year (UT). */
export function eclipsesForYear(year: number): Eclipse[] {
  const cached = eclipseCache.get(year)
  if (cached) return cached
  const start = Date.UTC(year, 0, 1)
  const end = Date.UTC(year + 1, 0, 1)
  const out: Eclipse[] = []
  for (let k = kOf(start) - 1; k <= kOf(end) + 1; k++) {
    for (const [kk, kind] of [[k, 'solar'], [k + 0.5, 'lunar']] as [number, EclipseKind][]) {
      const e = eclipseAt(kk, kind)
      if (e && e.date.getTime() >= start && e.date.getTime() < end) out.push(e)
    }
  }
  out.sort((a, b) => a.date.getTime() - b.date.getTime())
  eclipseCache.set(year, out)
  return out
}

// ── equinoxes and solstices (ch. 27) ─────────────────────────────────────

export type SeasonKind = 'marchEquinox' | 'juneSolstice' | 'septemberEquinox' | 'decemberSolstice'
export interface SeasonEvent {
  kind: SeasonKind
  date: Date
}

const SEASON_BASE: Record<SeasonKind, number[]> = {
  marchEquinox: [2451623.80984, 365242.37404, 0.05169, -0.00411, -0.00057],
  juneSolstice: [2451716.56767, 365241.62603, 0.00325, 0.00888, -0.0003],
  septemberEquinox: [2451810.21715, 365242.01767, -0.11575, 0.00337, 0.00078],
  decemberSolstice: [2451900.05952, 365242.74049, -0.06223, -0.00823, 0.00032],
}

// A, B, C of the 24 periodic terms
const SEASON_TERMS: [number, number, number][] = [
  [485, 324.96, 1934.136], [203, 337.23, 32964.467], [199, 342.08, 20.186], [182, 27.85, 445267.112],
  [156, 73.14, 45036.886], [136, 171.52, 22518.443], [77, 222.54, 65928.934], [74, 296.72, 3034.906],
  [70, 243.58, 9037.513], [58, 119.81, 33718.147], [52, 297.17, 150.678], [50, 21.02, 2281.226],
  [45, 247.54, 29929.562], [44, 325.15, 31555.956], [29, 60.93, 4443.417], [18, 155.12, 67555.328],
  [17, 288.79, 4562.452], [16, 198.04, 62894.029], [14, 199.76, 31436.921], [12, 95.39, 14577.848],
  [12, 287.11, 31931.756], [12, 320.81, 34777.259], [9, 227.73, 1222.114], [8, 15.45, 16859.074],
]

export function seasonsForYear(year: number): SeasonEvent[] {
  const Y = (year - 2000) / 1000
  return (Object.keys(SEASON_BASE) as SeasonKind[]).map((kind) => {
    const [a, b, c, d, e] = SEASON_BASE[kind]
    const jde0 = a + b * Y + c * Y ** 2 + d * Y ** 3 + e * Y ** 4
    const T = (jde0 - 2451545) / 36525
    const W = 35999.373 * T - 2.47
    const dLambda = 1 + 0.0334 * cosD(W) + 0.0007 * cosD(2 * W)
    const S = SEASON_TERMS.reduce((sum, [A, B, C]) => sum + A * cosD(B + C * T), 0)
    return { kind, date: jdeToDate(jde0 + (0.00001 * S) / dLambda) }
  })
}

// ── meteor showers: fixed yearly peaks (they move by about a day) ────────

export interface MeteorShower {
  key: 'quadrantids' | 'lyrids' | 'etaAquariids' | 'perseids' | 'orionids' | 'leonids' | 'geminids' | 'ursids'
  month: number // 1-12
  day: number
  zhr: number // zenithal hourly rate at the best
}

export const METEOR_SHOWERS: MeteorShower[] = [
  { key: 'quadrantids', month: 1, day: 3, zhr: 110 },
  { key: 'lyrids', month: 4, day: 22, zhr: 18 },
  { key: 'etaAquariids', month: 5, day: 6, zhr: 50 },
  { key: 'perseids', month: 8, day: 12, zhr: 100 },
  { key: 'orionids', month: 10, day: 21, zhr: 20 },
  { key: 'leonids', month: 11, day: 17, zhr: 15 },
  { key: 'geminids', month: 12, day: 14, zhr: 150 },
  { key: 'ursids', month: 12, day: 22, zhr: 10 },
]

// ── the Sun and the Moon as seen from a place (low-precision formulas, Meeus ch. 25) ────────────

export interface Place {
  lat: number // degrees north
  lon: number // degrees east
}

const normDeg = (d: number) => ((d % 360) + 360) % 360
const unixToJd = (ms: number) => ms / MS_PER_DAY + UNIX_JD

/** The Sun's right ascension and declination (degrees) at an instant. */
export function sunCoordinates(ms: number): { ra: number; dec: number } {
  const T = (unixToJd(ms) - 2451545) / 36525
  const L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T ** 2
  const M = 357.52911 + 35999.05029 * T - 0.0001537 * T ** 2
  const C =
    (1.914602 - 0.004817 * T - 0.000014 * T ** 2) * sinD(M) +
    (0.019993 - 0.000101 * T) * sinD(2 * M) +
    0.000289 * sinD(3 * M)
  const omega = 125.04 - 1934.136 * T
  const lambda = L0 + C - 0.00569 - 0.00478 * sinD(omega)
  const eps = 23.439291 - 0.0130042 * T + 0.00256 * cosD(omega)
  const ra = normDeg((Math.atan2(cosD(eps) * sinD(lambda), cosD(lambda)) * 180) / Math.PI)
  const dec = (Math.asin(sinD(eps) * sinD(lambda)) * 180) / Math.PI
  return { ra, dec }
}

function altitude(ra: number, dec: number, ms: number, place: Place): number {
  const jd = unixToJd(ms)
  const T = (jd - 2451545) / 36525
  const gmst = 280.46061837 + 360.98564736629 * (jd - 2451545) + 0.000387933 * T ** 2
  const hourAngle = normDeg(gmst + place.lon - ra)
  const sinAlt = sinD(place.lat) * sinD(dec) + cosD(place.lat) * cosD(dec) * cosD(hourAngle)
  return (Math.asin(Math.max(-1, Math.min(1, sinAlt))) * 180) / Math.PI
}

export const sunAltitude = (ms: number, place: Place) => {
  const { ra, dec } = sunCoordinates(ms)
  return altitude(ra, dec, ms, place)
}

/**
 * The Moon's altitude at the middle of a lunar eclipse. A lunar eclipse happens at full moon,
 * when the Moon is (within a degree or two) exactly opposite the Sun, so its position is the
 * Sun's antipode: right ascension + 180°, declination negated.
 */
export function moonAltitudeAtLunarEclipse(ms: number, place: Place): number {
  const { ra, dec } = sunCoordinates(ms)
  return altitude(normDeg(ra + 180), -dec, ms, place)
}

export interface SunTimes {
  sunrise: Date | null
  sunset: Date | null
  dayLengthMinutes: number
  polar: 'day' | 'night' | null // the Sun never sets / never rises during these 24 hours
}

/** Sunrise and sunset in the 24 hours from `startMs` (use the local midnight of the day you want). */
export function sunTimes(startMs: number, place: Place): SunTimes {
  const HORIZON = -0.833 // the Sun's upper edge on the horizon, with refraction
  const STEP = 10 * 60_000
  const f = (ms: number) => sunAltitude(ms, place) - HORIZON

  let sunrise: number | null = null
  let sunset: number | null = null
  let prev = f(startMs)
  const startPositive = prev > 0
  for (let t = startMs + STEP; t <= startMs + MS_PER_DAY; t += STEP) {
    const cur = f(t)
    if ((prev < 0) !== (cur < 0)) {
      let lo = t - STEP
      let hi = t
      for (let i = 0; i < 24; i++) {
        const mid = (lo + hi) / 2
        if ((f(mid) < 0) === (f(lo) < 0)) lo = mid
        else hi = mid
      }
      if (cur > 0 && sunrise === null) sunrise = hi
      else if (cur < 0 && sunset === null) sunset = hi
    }
    prev = cur
  }
  const polar = sunrise === null && sunset === null ? (startPositive ? 'day' : 'night') : null
  let length = 0
  if (polar === 'day') length = 24 * 60
  else if (sunrise !== null && sunset !== null) length = sunset >= sunrise ? (sunset - sunrise) / 60_000 : (sunset - sunrise + MS_PER_DAY) / 60_000
  else if (sunrise !== null) length = (startMs + MS_PER_DAY - sunrise) / 60_000
  else if (sunset !== null) length = (sunset - startMs) / 60_000
  return {
    sunrise: sunrise === null ? null : new Date(sunrise),
    sunset: sunset === null ? null : new Date(sunset),
    dayLengthMinutes: Math.round(length),
    polar,
  }
}
