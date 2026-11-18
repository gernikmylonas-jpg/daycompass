<script setup lang="ts">
// A gold nugget: lumpy, lit from the top left.
withDefaults(defineProps<{ size?: number }>(), { size: 18 })
</script>

<template>
  <svg viewBox="0 0 32 32" :width="size" :height="size" aria-hidden="true" class="shrink-0">
    <defs>
      <linearGradient id="nug-g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#fff2a8" /><stop offset="0.45" stop-color="#f4c430" /><stop offset="1" stop-color="#a8761a" />
      </linearGradient>
    </defs>
    <path d="M5 19c-2-4 0-8 4-9 1-4 6-6 10-4 4-1 8 2 8 6 3 2 3 7 0 10-2 4-8 5-12 4-5 2-9-1-10-7z"
      fill="url(#nug-g)" stroke="#8a5a0a" stroke-width="1.2" stroke-linejoin="round" />
    <path d="M10 12c2-2 5-2 7-1M9 19c1 2 3 3 5 3" fill="none" stroke="#fff8cc" stroke-width="1.4" stroke-linecap="round" opacity="0.8" />
  </svg>
</template>
