// The wallpapers are drawn in code (no image files): each function returns the inside of a 1600x900 SVG.
// They are seeded, so a picture looks the same every time. Add one by adding a function here, an entry to
// ART below, its id to backend/app/application/services/wallpapers.py and its texts to the four locale files.
export const W = 1600
export const H = 900

function rng(seed: number) {
  let s = seed >>> 0
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    return s / 4294967296
  }
}
const n1 = (n: number) => n.toFixed(1)

/** A filled hill/ridge: a few sine waves added together, closed along the bottom. */
function ridge(base: number, amp: number, seed: number, fill: string, opacity = 1, waves = 4): string {
  const r = rng(seed)
  const parts = Array.from({ length: waves }, (_, i) => ({ f: (0.004 + r() * 0.006) * (i + 1), p: r() * 6.28, a: amp / (i + 1) }))
  let d = `M0,${H}`
  for (let x = 0; x <= W; x += 16) {
    const y = base + parts.reduce((s, p) => s + Math.sin(x * p.f + p.p) * p.a, 0)
    d += ` L${x},${n1(y)}`
  }
  return `<path d="${d} L${W},${H} Z" fill="${fill}" opacity="${opacity}"/>`
}

function stars(count: number, seed: number, maxY: number, color = '#fff'): string {
  const r = rng(seed)
  let out = ''
  for (let i = 0; i < count; i++) out += `<circle cx="${n1(r() * W)}" cy="${n1(r() * maxY)}" r="${n1(0.5 + r() * 1.5)}" fill="${color}" opacity="${n1(0.3 + r() * 0.7)}"/>`
  return out
}

function gear(cx: number, cy: number, radius: number, teeth: number, stroke: string, fill: string, width = 3): string {
  const pts: string[] = []
  for (let i = 0; i < teeth * 4; i++) {
    const a = (i / (teeth * 4)) * Math.PI * 2
    const rr = i % 4 < 2 ? radius : radius * 1.14
    pts.push(`${n1(cx + Math.cos(a) * rr)},${n1(cy + Math.sin(a) * rr)}`)
  }
  return `<polygon points="${pts.join(' ')}" fill="${fill}" stroke="${stroke}" stroke-width="${width}" stroke-linejoin="round"/>` +
    `<circle cx="${cx}" cy="${cy}" r="${n1(radius * 0.35)}" fill="none" stroke="${stroke}" stroke-width="${width}"/>` +
    `<circle cx="${cx}" cy="${cy}" r="${n1(radius * 0.12)}" fill="${stroke}"/>`
}

function blob(cx: number, cy: number, radius: number, seed: number): string {
  const r = rng(seed)
  const k = [r() * 6, r() * 6, r() * 6]
  let d = ''
  for (let i = 0; i <= 48; i++) {
    const a = (i / 48) * Math.PI * 2
    const rr = radius * (1 + 0.22 * Math.sin(3 * a + k[0]) + 0.14 * Math.sin(5 * a + k[1]) + 0.08 * Math.sin(9 * a + k[2]))
    d += `${i ? ' L' : 'M'}${n1(cx + Math.cos(a) * rr * 1.25)},${n1(cy + Math.sin(a) * rr)}`
  }
  return d + ' Z'
}

function trees(rows: number, seed: number, horizon: number): string {
  const r = rng(seed)
  let out = ''
  for (let row = 0; row < rows; row++) {
    const y = horizon + row * ((H - horizon) / rows) + 30
    const size = 36 + row * 26
    const shade = Math.round(70 - row * (46 / rows))
    let d = ''
    for (let x = -40; x < W + 40; x += size * (0.55 + r() * 0.3)) {
      const h = size * (1.5 + r() * 0.8)
      const w = size * 0.42
      d += `M${n1(x - w)},${n1(y)} L${n1(x)},${n1(y - h)} L${n1(x + w)},${n1(y)} Z`
      d += `M${n1(x - w * 0.75)},${n1(y - h * 0.38)} L${n1(x)},${n1(y - h * 1.12)} L${n1(x + w * 0.75)},${n1(y - h * 0.38)} Z`
    }
    out += `<path d="${d}" fill="hsl(150 ${30 - row * 2}% ${shade * 0.42}%)" opacity="${n1(0.55 + row * 0.12)}"/>`
    out += `<rect x="0" y="${n1(y - 8)}" width="${W}" height="${H}" fill="hsl(150 ${30 - row * 2}% ${shade * 0.42}%)" opacity="${n1(0.55 + row * 0.12)}"/>`
  }
  return out
}

const grad = (id: string, stops: [number, string][], vertical = true) =>
  `<linearGradient id="${id}" x1="0" y1="0" x2="${vertical ? 0 : 1}" y2="${vertical ? 1 : 0}">${stops.map(([o, c]) => `<stop offset="${o}" stop-color="${c}"/>`).join('')}</linearGradient>`

const rect = (fill: string) => `<rect width="${W}" height="${H}" fill="${fill}"/>`

export const ART: Record<string, () => string> = {
  topo() {
    let out = rect('#eef1ee')
    for (const [cx, cy, seed] of [[480, 360, 3], [1180, 560, 8]] as const) {
      const r = rng(seed)
      const ph = [r() * 6, r() * 6, r() * 6]
      for (let k = 1; k <= 16; k++) {
        let d = ''
        for (let i = 0; i <= 90; i++) {
          const a = (i / 90) * Math.PI * 2
          const rr = k * 34 * (1 + 0.18 * Math.sin(2 * a + ph[0] + k * 0.2) + 0.1 * Math.sin(4 * a + ph[1]) + 0.05 * Math.sin(7 * a + ph[2]))
          d += `${i ? ' L' : 'M'}${n1(cx + Math.cos(a) * rr * 1.3)},${n1(cy + Math.sin(a) * rr)}`
        }
        out += `<path d="${d} Z" fill="none" stroke="${k % 5 === 0 ? '#7d9183' : '#a9b8ad'}" stroke-width="${k % 5 === 0 ? 2.2 : 1.1}"/>`
      }
    }
    return out
  },

  blueprint() {
    let out = rect('#0d3b66')
    for (let x = 0; x <= W; x += 40) out += `<line x1="${x}" y1="0" x2="${x}" y2="${H}" stroke="#7fb2e5" stroke-width="${x % 200 === 0 ? 1.4 : 0.5}" opacity="0.45"/>`
    for (let y = 0; y <= H; y += 40) out += `<line x1="0" y1="${y}" x2="${W}" y2="${y}" stroke="#7fb2e5" stroke-width="${y % 200 === 0 ? 1.4 : 0.5}" opacity="0.45"/>`
    for (const [cx, cy, rr] of [[420, 430, 250], [1150, 400, 170], [1330, 700, 90]] as const) {
      out += `<circle cx="${cx}" cy="${cy}" r="${rr}" fill="none" stroke="#cfe6ff" stroke-width="2" opacity="0.8"/><circle cx="${cx}" cy="${cy}" r="${rr * 0.6}" fill="none" stroke="#cfe6ff" stroke-width="1" stroke-dasharray="8 6" opacity="0.7"/>`
      out += `<path d="M${cx - rr - 30},${cy} H${cx + rr + 30} M${cx},${cy - rr - 30} V${cy + rr + 30}" stroke="#cfe6ff" stroke-width="1.2" opacity="0.8"/>`
      out += `<polygon points="${cx},${cy - rr * 0.8} ${cx + rr * 0.12},${cy} ${cx},${cy + rr * 0.8} ${cx - rr * 0.12},${cy}" fill="none" stroke="#cfe6ff" stroke-width="1.6"/>`
    }
    return out + `<path d="M120,820 H700 M120,810 V830 M700,810 V830" stroke="#cfe6ff" stroke-width="1.4" fill="none"/>`
  },

  old_map() {
    const r = rng(11)
    let out = `<defs>${grad('om', [[0, '#ecdcae'], [1, '#cfb479']])}<radialGradient id="omv" cx="50%" cy="50%" r="75%"><stop offset="60%" stop-color="#8a5a22" stop-opacity="0"/><stop offset="100%" stop-color="#5a3510" stop-opacity="0.55"/></radialGradient></defs>`
    out += rect('url(#om)')
    for (let i = 0; i < 14; i++) out += `<circle cx="${n1(r() * W)}" cy="${n1(r() * H)}" r="${n1(40 + r() * 120)}" fill="#a7792f" opacity="${n1(0.04 + r() * 0.06)}"/>`
    for (let x = 0; x <= W; x += 100) out += `<line x1="${x}" y1="0" x2="${x}" y2="${H}" stroke="#7a5320" stroke-width="0.8" opacity="0.25"/>`
    for (let y = 0; y <= H; y += 100) out += `<line x1="0" y1="${y}" x2="${W}" y2="${y}" stroke="#7a5320" stroke-width="0.8" opacity="0.25"/>`
    for (const [cx, cy, rad, seed] of [[430, 360, 210, 4], [1090, 300, 170, 9], [1180, 640, 130, 15], [640, 700, 100, 21]] as const) {
      out += `<path d="${blob(cx, cy, rad, seed)}" fill="#d9c48d" stroke="#6b4417" stroke-width="3" opacity="0.95"/>`
      out += `<path d="${blob(cx, cy, rad * 1.12, seed)}" fill="none" stroke="#6b4417" stroke-width="1" stroke-dasharray="2 5" opacity="0.6"/>`
    }
    out += `<path d="M300,420 C520,300 700,560 900,420 S1150,300 1230,610" fill="none" stroke="#9a2f1e" stroke-width="3.5" stroke-dasharray="14 9" stroke-linecap="round"/>`
    out += `<path d="M1210,590 l40,40 m0,-40 l-40,40" stroke="#9a2f1e" stroke-width="7" stroke-linecap="round"/>`
    const rose = (cx: number, cy: number, s: number) => {
      let g = `<circle cx="${cx}" cy="${cy}" r="${s}" fill="none" stroke="#5a3510" stroke-width="2.5"/>`
      for (let i = 0; i < 8; i++) {
        const a = (i * Math.PI) / 4
        const len = i % 2 === 0 ? s * 1.6 : s * 1.05
        g += `<polygon points="${n1(cx + Math.cos(a) * len)},${n1(cy + Math.sin(a) * len)} ${n1(cx + Math.cos(a + 0.28) * s * 0.28)},${n1(cy + Math.sin(a + 0.28) * s * 0.28)} ${n1(cx + Math.cos(a - 0.28) * s * 0.28)},${n1(cy + Math.sin(a - 0.28) * s * 0.28)}" fill="${i === 6 ? '#9a2f1e' : '#5a3510'}"/>`
      }
      return g
    }
    out += rose(1380, 190, 62) + rose(210, 730, 40)
    for (let i = 0; i < 3; i++) out += `<path d="M${200 + i * 160},${150 + i * 18} q20,-24 40,0 q20,-24 40,0" fill="none" stroke="#5a3510" stroke-width="2" opacity="0.7"/>`
    return out + `<rect width="${W}" height="${H}" fill="url(#omv)"/>`
  },

  ocean() {
    let out = `<defs>${grad('oc', [[0, '#a8d8ef'], [0.38, '#e8f5fa'], [0.4, '#2a7fa8'], [1, '#0a3a5e']])}</defs>` + rect('url(#oc)')
    out += `<circle cx="1180" cy="250" r="70" fill="#fff6d6" opacity="0.9"/>`
    for (let row = 0; row < 16; row++) {
      const y = 380 + row * 34
      let d = `M0,${y}`
      for (let x = 0; x <= W; x += 20) d += ` L${x},${n1(y + Math.sin(x * (0.012 + row * 0.0006) + row * 1.7) * (4 + row * 1.2))}`
      out += `<path d="${d}" fill="none" stroke="#fff" stroke-width="${n1(1 + row * 0.14)}" opacity="${n1(0.10 + row * 0.015)}"/>`
    }
    return out + ridge(405, 6, 5, '#1c6a90', 0.35, 3)
  },

  dunes() {
    let out = `<defs>${grad('du', [[0, '#f9c98a'], [0.55, '#fde7c1'], [1, '#f6c27c']])}</defs>` + rect('url(#du)')
    out += `<circle cx="1250" cy="300" r="110" fill="#fff3d6" opacity="0.9"/><circle cx="1250" cy="300" r="170" fill="#fff3d6" opacity="0.25"/>`
    return out + ridge(520, 70, 2, '#e8b377', 1, 3) + ridge(620, 80, 6, '#d99a5e', 1, 3) + ridge(730, 70, 9, '#c4804a', 1, 3) + ridge(830, 50, 14, '#a8643a', 1, 3)
  },

  mountains() {
    let out = `<defs>${grad('mt', [[0, '#7d9cc4'], [0.55, '#f2d7a8'], [1, '#f7c58b']])}</defs>` + rect('url(#mt)')
    out += `<circle cx="1050" cy="430" r="90" fill="#fff0c9" opacity="0.95"/>`
    return out + ridge(430, 120, 3, '#9fb4cf', 0.9, 5) + ridge(520, 110, 7, '#6f8aab', 0.95, 5) + ridge(630, 100, 12, '#4a6482', 1, 5) + ridge(760, 70, 17, '#2d4259', 1, 4)
  },

  forest() {
    let out = `<defs>${grad('fo', [[0, '#cfe3d4'], [0.5, '#a9c9b0'], [1, '#6f9a7c']])}</defs>` + rect('url(#fo)')
    out += `<circle cx="400" cy="230" r="95" fill="#f4f8ee" opacity="0.8"/>`
    out += trees(5, 31, 360)
    return out + `<rect y="300" width="${W}" height="220" fill="#e9f3e8" opacity="0.18"/>`
  },

  gears() {
    let out = rect('#2d1c10')
    out += `<rect width="${W}" height="${H}" fill="#000" opacity="0.15"/>`
    const spots: [number, number, number, number][] = [[260, 240, 150, 14], [560, 330, 90, 9], [820, 200, 110, 11], [1180, 330, 170, 16], [1450, 650, 110, 11], [900, 660, 140, 13], [380, 700, 100, 10]]
    spots.forEach(([x, y, rr, teeth], i) => { out += gear(x, y, rr, teeth, i % 2 ? '#c9803f' : '#e0a35c', i % 2 ? '#4a2c15' : '#563318', 3.5) })
    return out
  },

  night_sea() {
    let out = `<defs>${grad('ns', [[0, '#050d1d'], [0.55, '#122a4a'], [0.56, '#0a2236'], [1, '#04101d']])}</defs>` + rect('url(#ns)')
    out += stars(220, 5, 480)
    out += `<circle cx="1120" cy="210" r="62" fill="#f6f1d8"/><circle cx="1120" cy="210" r="120" fill="#f6f1d8" opacity="0.12"/>`
    out += `<rect x="1085" y="500" width="70" height="400" fill="#f6f1d8" opacity="0.13"/>`
    for (let row = 0; row < 14; row++) {
      const y = 500 + row * 30
      let d = `M0,${y}`
      for (let x = 0; x <= W; x += 20) d += ` L${x},${n1(y + Math.sin(x * 0.014 + row * 2.1) * (3 + row))}`
      out += `<path d="${d}" fill="none" stroke="#7fb4d6" stroke-width="${n1(1 + row * 0.1)}" opacity="${n1(0.08 + row * 0.012)}"/>`
    }
    return out
  },

  cyber_city() {
    const r = rng(77)
    let out = `<defs>${grad('cc', [[0, '#12062e'], [0.45, '#5b1a7a'], [0.62, '#ff3d9a'], [0.63, '#0a0820'], [1, '#0a0820']])}</defs>` + rect('url(#cc)')
    out += `<circle cx="800" cy="440" r="150" fill="#ffb347" opacity="0.95"/>`
    for (let i = 0; i < 9; i++) out += `<rect x="640" y="${n1(380 + i * 22 + i * i * 1.2)}" width="320" height="${n1(2 + i * 1.3)}" fill="#5b1a7a" opacity="0.95"/>`
    let x = -20
    while (x < W) {
      const w = 50 + r() * 90
      const h = 90 + r() * 240
      out += `<rect x="${n1(x)}" y="${n1(560 - h)}" width="${n1(w)}" height="${n1(h)}" fill="#0b0a1f" stroke="#00e5ff" stroke-opacity="0.35"/>`
      for (let k = 0; k < w * h / 700; k++) out += `<rect x="${n1(x + 5 + r() * (w - 12))}" y="${n1(560 - h + 8 + r() * (h - 16))}" width="4" height="4" fill="${r() > 0.5 ? '#00e5ff' : '#ff2e93'}" opacity="${n1(0.4 + r() * 0.5)}"/>`
      x += w + 6
    }
    for (let i = -14; i <= 14; i++) out += `<line x1="800" y1="560" x2="${800 + i * 220}" y2="${H}" stroke="#00e5ff" stroke-width="1.4" opacity="0.55"/>`
    for (let i = 1; i <= 8; i++) out += `<line x1="0" y1="${n1(560 + (i * i * 4.9))}" x2="${W}" y2="${n1(560 + (i * i * 4.9))}" stroke="#ff2e93" stroke-width="1.3" opacity="0.55"/>`
    return out
  },

  aurora() {
    let out = `<defs>${grad('au', [[0, '#03071a'], [1, '#0d2a3d']])}<filter id="aub" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="28"/></filter>${grad('ag', [[0, '#2dffb2'], [0.6, '#2d9bff'], [1, '#8a3dff']])}</defs>` + rect('url(#au)')
    out += stars(260, 9, 620)
    for (let b = 0; b < 3; b++) {
      let d = `M0,${200 + b * 70}`
      for (let x = 0; x <= W; x += 20) d += ` L${x},${n1(200 + b * 70 + Math.sin(x * 0.006 + b * 1.4) * 70 + Math.sin(x * 0.015 + b) * 28)}`
      d += ` L${W},${400 + b * 80} L0,${400 + b * 80} Z`
      out += `<path d="${d}" fill="url(#ag)" opacity="${n1(0.55 - b * 0.12)}" filter="url(#aub)"/>`
    }
    return out + ridge(760, 70, 4, '#06121c', 1, 4) + ridge(830, 45, 8, '#030a10', 1, 3)
  },
}

/** The finished SVG markup for a wallpaper id (empty for an unknown id). */
export function wallpaperSvg(id: string): string {
  const art = ART[id]
  if (!art) return ''
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" width="100%" height="100%">${art()}</svg>`
}
