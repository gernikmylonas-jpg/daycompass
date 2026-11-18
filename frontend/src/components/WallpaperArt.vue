<script setup lang="ts">
import { computed } from 'vue'
import { wallpaperSvg } from '../wallpapers/art'

// One wallpaper picture (generated, trusted markup from wallpapers/art.ts).
const props = defineProps<{ id: string }>()
const svg = computed(() => wallpaperSvg(props.id))
</script>

<template>
  <div class="w-full h-full overflow-hidden" aria-hidden="true" v-html="svg"></div>
</template>
