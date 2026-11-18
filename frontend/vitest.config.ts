import { defineConfig } from 'vitest/config'

// Tests cover plain TypeScript (astronomy, dates, translations), so no Vue/Tailwind plugins are needed.
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
