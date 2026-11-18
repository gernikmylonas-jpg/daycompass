<script setup lang="ts">
import { useSettingsStore } from '../stores/settings'
import WallpaperArt from './WallpaperArt.vue'

// The page background picture, when the user has switched wallpapers on and chosen one they unlocked.
// A soft veil in the page colour keeps text readable on top of it.
const settings = useSettingsStore()
</script>

<template>
  <div v-if="settings.wallpapersOn && settings.wallpaper" class="wallpaper" aria-hidden="true">
    <WallpaperArt :id="settings.wallpaper" />
  </div>
</template>
