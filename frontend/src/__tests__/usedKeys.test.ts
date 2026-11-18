import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import en from '../i18n/locales/en'

// Every message key written literally in a component or view (t('a.b')) must exist.
function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) return name === '__tests__' || name === 'locales' ? [] : sources(path)
    return /\.(vue|ts)$/.test(name) ? [path] : []
  })
}

describe('translation keys used in the code', () => {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en }, missingWarn: false })
  const srcDir = join(__dirname, '..')
  it('all exist in English', () => {
    const missing: string[] = []
    for (const file of sources(srcDir)) {
      const text = readFileSync(file, 'utf-8')
      for (const m of text.matchAll(/\bt\(\s*'([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)'/g)) {
        if (!i18n.global.te(m[1])) missing.push(`${m[1]}  (${file.slice(srcDir.length + 1)})`)
      }
    }
    expect(missing).toEqual([])
  })
})
