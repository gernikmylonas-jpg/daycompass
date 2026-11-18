// Planets and other sky events, computed on the device from the "Keplerian elements for approximate positions
// of the major planets" (E. M. Standish, JPL, valid 1800–2050). Accuracy is about a day for dates up to 2050 and
// degrades slowly after that (the outer planets first), so dates are shown as dates, not times.

export type PlanetId = 'mercury' | 'venus' | 'mars' | 'jupiter' | 'saturn' | 'uranus' | 'neptune'

// a, e, I, L, long.peri, long.node  (value at J2000 and change per Julian century)
type Elements = [number, number, number, number, number, number, number, number, number, number, number, number]
const ELEMENTS: Record<PlanetId | 'earth', Elements> = {
  mercury: [0.38709927, 0.00000037, 0.20563593, 0.00001906, 7.00497902, -0.00594749, 252.2503235, 149472.67411175, 77.45779628, 0.16047689, 48.33076593, -0.12534081],
  venus: [0.72333566, 0.0000039, 0.00677672, -0.00004107, 3.39467605, -0.0007889, 181.9790995, 58517.81538729, 131.60246718, 0.00268329, 76.67984255, -0.27769418],
  earth: [1.00000261, 0.00000562, 0.01671123, -0.00004392, -0.00001531, -0.01294668, 100.46457166, 35999.37244981, 102.93768193, 0.32327364, 0, 0],
  mars: [1.52371034, 0.00001847, 0.0933941, 0.00007882, 1.84969142, -0.00813131, -4.55343205, 19140.30268499, -23.94362959, 0.44441088, 49.55953891, -0.29257343],
  jupiter: [5.202887, -0.00011607, 0.04838624, -0.00013253, 1.30439695, -0.00183714, 34.39644051, 3034.74612775, 14.72847983, 0.21252668, 100.47390909, 0.20469106],
  saturn: [9.53667594, -0.0012506, 0.05386179, -0.00050991, 2.48599187, 0.00193609, 49.95424423, 1222.49362201, 92.59887831, -0.41897216, 113.66242448, -0.28867794],
  uranus: [19.18916464, -0.00196176, 0.04725744, -0.00004397, 0.77263783, -0.00242939, 313.23810451, 428.48202785, 170.9542763, 0.40805281, 74.01692503, 0.04240589],
  neptune: [30.06992276, 0.00026291, 0.00859048, 0.00005105, 1.77004347, 0.00035372, -55.12002969, 218.45945325, 44.96476227, -0.32241464, 131.78422574, -0.00508664],
}

export const PLANETS: PlanetId[] = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune']
const INNER: PlanetId[] = ['mercury', 'venus']
const RAD = Math.PI / 180
const wrap180 = (d: number) => ((((d + 180) % 360) + 360) % 360) - 180
const JD_UNIX = 2440587.5
const MS_DAY = 86_400_000

const jdToDate = (jd: number) => new Date(Math.round((jd - JD_UNIX) * MS_DAY))
const dateToJd = (d: Date) => d.getTime() / MS_DAY + JD_UNIX

type Vec = [number, number, number]

function helio(body: PlanetId | 'earth', jd: number): Vec {
  const T = (jd - 2451545) / 36525
  const el = ELEMENTS[body]
  const v = (i: number) => el[i] + el[i + 1] * T
  const a = v(0), e = v(2), I = v(4) * RAD, L = v(6), peri = v(8), node = v(10) * RAD
  const M = wrap180(L - peri) * RAD
  let E = M + e * Math.sin(M)
  for (let i = 0; i < 12; i++) E -= (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E))
  const xp = a * (Math.cos(E) - e)
  const yp = a * Math.sqrt(1 - e * e) * Math.sin(E)
  const w = (peri - (node / RAD)) * RAD // argument of perihelion
  const cw = Math.cos(w), sw = Math.sin(w), cO = Math.cos(node), sO = Math.sin(node), cI = Math.cos(I), sI = Math.sin(I)
  return [
    (cw * cO - sw * sO * cI) * xp + (-sw * cO - cw * sO * cI) * yp,
    (cw * sO + sw * cO * cI) * xp + (-sw * sO + cw * cO * cI) * yp,
    sw * sI * xp + cw * sI * yp,
  ]
}

export interface Geo { lon: number; lat: number; dist: number; sunLon: number; elongation: number } // degrees; elongation signed: + east of the Sun (evening sky)
export function geocentric(planet: PlanetId, jd: number): Geo {
  const p = helio(planet, jd)
  const e = helio('earth', jd)
  const g: Vec = [p[0] - e[0], p[1] - e[1], p[2] - e[2]]
  const lon = Math.atan2(g[1], g[0]) / RAD
  const lat = Math.atan2(g[2], Math.hypot(g[0], g[1])) / RAD
  const sunLon = Math.atan2(-e[1], -e[0]) / RAD
  const dLon = wrap180(lon - sunLon)
  // true angular distance from the Sun
  const cosEl = Math.cos(lat * RAD) * Math.cos(dLon * RAD)
  const el = Math.acos(Math.max(-1, Math.min(1, cosEl))) / RAD
  return { lon, lat, dist: Math.hypot(...g), sunLon, elongation: dLon >= 0 ? el : -el }
}

export type SkyEventKind = 'opposition' | 'greatestElongation' | 'conjunctionSun' | 'conjunction' | 'perihelion' | 'aphelion'
export interface SkyEvent {
  kind: SkyEventKind
  planets: PlanetId[] // empty for the Earth's perihelion/aphelion
  date: Date
  degrees?: number // elongation or separation
  side?: 'east' | 'west' // greatest elongation: evening (east) or morning (west) sky
  inferior?: boolean // conjunction with the Sun
}

/** Finds where f crosses zero between two Julian days (bisection). */
function root(f: (jd: number) => number, a: number, b: number): number {
  let fa = f(a)
  for (let i = 0; i < 40; i++) {
    const m = (a + b) / 2
    const fm = f(m)
    if ((fm < 0) === (fa < 0)) { a = m; fa = fm } else b = m
  }
  return (a + b) / 2
}

/** Finds the maximum of f in [a, b] (ternary search; f is smooth and single-peaked on a day-scale window). */
function peak(f: (jd: number) => number, a: number, b: number): number {
  for (let i = 0; i < 50; i++) {
    const m1 = a + (b - a) / 3
    const m2 = b - (b - a) / 3
    if (f(m1) < f(m2)) a = m1
    else b = m2
  }
  return (a + b) / 2
}

const cache = new Map<number, SkyEvent[]>()

/** Oppositions, greatest elongations, conjunctions with the Sun, planet–planet conjunctions and the Earth's perihelion/aphelion. */
export function skyEventsForYear(year: number): SkyEvent[] {
  const hit = cache.get(year)
  if (hit) return hit
  const start = dateToJd(new Date(Date.UTC(year, 0, 1)))
  const days = Math.round(dateToJd(new Date(Date.UTC(year + 1, 0, 1))) - start)
  const out: SkyEvent[] = []
  const inYear = (jd: number) => jdToDate(jd).getUTCFullYear() === year

  for (const planet of PLANETS) {
    const inner = INNER.includes(planet)
    const d = (jd: number) => geocentric(planet, jd).elongation
    const lonDiff = (jd: number) => { const g = geocentric(planet, jd); return wrap180(g.lon - g.sunLon) }
    for (let i = -1; i < days; i++) {
      const jd = start + i
      const a = lonDiff(jd), b = lonDiff(jd + 1)
      if (inner) {
        // conjunction with the Sun: the longitude difference crosses 0
        if ((a < 0) !== (b < 0) && Math.abs(a) < 90 && Math.abs(b) < 90) {
          const t = root(lonDiff, jd, jd + 1)
          if (inYear(t)) out.push({ kind: 'conjunctionSun', planets: [planet], date: jdToDate(t), inferior: geocentric(planet, t).dist < 1 })
        }
        // greatest elongation: |elongation| has a local maximum
        const m = Math.abs(d(jd - 1)), c = Math.abs(d(jd)), n = Math.abs(d(jd + 1))
        if (c > m && c >= n && c > 10) {
          const t = peak((x) => Math.abs(d(x)), jd - 1, jd + 1)
          if (inYear(t)) out.push({ kind: 'greatestElongation', planets: [planet], date: jdToDate(t), degrees: Math.abs(d(t)), side: d(t) > 0 ? 'east' : 'west' })
        }
      } else {
        const og = (x: number) => wrap180(lonDiff(x) + 180) // 0 at opposition
        const oa = og(jd), ob = og(jd + 1)
        if ((oa < 0) !== (ob < 0) && Math.abs(oa) < 90 && Math.abs(ob) < 90) {
          const t = root(og, jd, jd + 1)
          if (inYear(t)) out.push({ kind: 'opposition', planets: [planet], date: jdToDate(t) })
        }
      }
    }
  }

  // planets close together in the sky (and not lost in the Sun's glare)
  for (let x = 0; x < PLANETS.length; x++) {
    for (let y = x + 1; y < PLANETS.length; y++) {
      const A = PLANETS[x], B = PLANETS[y]
      const f = (jd: number) => wrap180(geocentric(A, jd).lon - geocentric(B, jd).lon)
      for (let i = -1; i < days; i++) {
        const jd = start + i
        const a = f(jd), b = f(jd + 1)
        if ((a < 0) !== (b < 0) && Math.abs(a) < 20 && Math.abs(b) < 20) {
          const t = root(f, jd, jd + 1)
          if (!inYear(t)) continue
          const ga = geocentric(A, t), gb = geocentric(B, t)
          const sep = Math.hypot(ga.lat - gb.lat, wrap180(ga.lon - gb.lon) * Math.cos(ga.lat * RAD))
          if (sep <= 2 && Math.min(Math.abs(ga.elongation), Math.abs(gb.elongation)) >= 15) out.push({ kind: 'conjunction', planets: [A, B], date: jdToDate(t), degrees: sep })
        }
      }
    }
  }

  // the Earth's closest and farthest points from the Sun
  const dist = (jd: number) => Math.hypot(...helio('earth', jd))
  for (let i = 0; i < days; i++) {
    const jd = start + i
    const m = dist(jd - 1), c = dist(jd), n = dist(jd + 1)
    if (c < m && c <= n) {
      const t = peak((x) => -dist(x), jd - 1, jd + 1)
      if (inYear(t)) out.push({ kind: 'perihelion', planets: [], date: jdToDate(t) })
    }
    if (c > m && c >= n) {
      const t = peak(dist, jd - 1, jd + 1)
      if (inYear(t)) out.push({ kind: 'aphelion', planets: [], date: jdToDate(t) })
    }
  }

  out.sort((p, q) => p.date.getTime() - q.date.getTime())
  cache.set(year, out)
  return out
}

export type SkyPosition = 'evening' | 'morning' | 'allNight' | 'nearSun'
export interface PlanetNow { planet: PlanetId; elongation: number; position: SkyPosition }

/** Where each planet is relative to the Sun today: evening sky, morning sky, up all night, or lost near the Sun. */
export function planetsNow(date: Date): PlanetNow[] {
  const jd = dateToJd(date)
  return PLANETS.map((planet) => {
    const e = geocentric(planet, jd).elongation
    const abs = Math.abs(e)
    const position: SkyPosition = abs < 15 ? 'nearSun' : abs > 150 ? 'allNight' : e > 0 ? 'evening' : 'morning'
    return { planet, elongation: Math.round(e), position }
  })
}
