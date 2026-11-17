<script setup lang="ts">
import type { LocaleCode } from '../i18n'

// Inline SVGs: flag emoji are not rendered on Windows, so they would show up as "GB", "ES"…
defineProps<{ code: LocaleCode }>()
</script>

<template>
  <span class="inline-block w-6 h-4 rounded-sm overflow-hidden ring-1 ring-black/10 shrink-0 align-middle" aria-hidden="true">
    <!-- United Kingdom (English) -->
    <svg v-if="code === 'en'" viewBox="0 0 60 30" preserveAspectRatio="none" class="w-full h-full block">
      <rect width="60" height="30" fill="#012169" />
      <path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6" />
      <path d="M0,0 L60,30 M60,0 L0,30" stroke="#C8102E" stroke-width="2.5" />
      <path d="M30,0 V30 M0,15 H60" stroke="#fff" stroke-width="10" />
      <path d="M30,0 V30 M0,15 H60" stroke="#C8102E" stroke-width="6" />
    </svg>
    <!-- Spain (Spanish) -->
    <svg v-else-if="code === 'es'" viewBox="0 0 27 18" preserveAspectRatio="none" class="w-full h-full block">
      <rect width="27" height="18" fill="#AA151B" />
      <rect y="4.5" width="27" height="9" fill="#F1BF00" />
    </svg>
    <!-- France (French) -->
    <svg v-else-if="code === 'fr'" viewBox="0 0 27 18" preserveAspectRatio="none" class="w-full h-full block">
      <rect width="9" height="18" fill="#0055A4" />
      <rect x="9" width="9" height="18" fill="#fff" />
      <rect x="18" width="9" height="18" fill="#EF4135" />
    </svg>
    <!-- Greece (Greek) -->
    <svg v-else viewBox="0 0 27 18" preserveAspectRatio="none" class="w-full h-full block">
      <rect width="27" height="18" fill="#0D5EAF" />
      <path d="M0,3 H27 M0,7 H27 M0,11 H27 M0,15 H27" stroke="#fff" stroke-width="2" />
      <rect width="10" height="10" fill="#0D5EAF" />
      <path d="M5,0 V10 M0,5 H10" stroke="#fff" stroke-width="2" />
    </svg>
  </span>
</template>
