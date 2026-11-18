<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from './stores/auth'
import { useSettingsStore } from './stores/settings'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import SettingsMenu from './components/SettingsMenu.vue'
import NeedleCursor from './components/NeedleCursor.vue'
import WallpaperLayer from './components/WallpaperLayer.vue'

const { t } = useI18n()
const auth = useAuthStore()
const settings = useSettingsStore()

// Once signed in, the account's saved preferences (style, mode, cursor, language) replace this
// device's; from then on every change is saved back to the account.
const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
const setOnline = () => { online.value = navigator.onLine }
onMounted(() => { window.addEventListener('online', setOnline); window.addEventListener('offline', setOnline) })
onBeforeUnmount(() => { window.removeEventListener('online', setOnline); window.removeEventListener('offline', setOnline) })

watch(() => auth.token, (token) => { if (token) settings.loadFromServer() }, { immediate: true })
</script>

<template>
  <div class="bg-page min-h-screen">
    <WallpaperLayer />
    <a href="#main" class="skip-link">{{ t('a11y.skip') }}</a>
    <p v-if="!online" role="status" class="bg-surface border-b border-slate-400 text-slate-700 text-sm text-center px-4 py-1">📡 {{ t('common.offline') }}</p>
    <div class="h-12 px-4 md:px-8 flex items-center justify-between">
      <!-- small compass emblem: the needle cursor points here on pages without the big dial -->
      <RouterLink to="/" aria-label="DayCompass" data-compass-target="logo"
        class="w-8 h-8 rounded-full bg-surface border border-slate-400 shadow-sm flex items-center justify-center">
        <svg viewBox="-12 -12 24 24" width="22" height="22" aria-hidden="true">
          <circle r="10" fill="none" stroke="var(--color-slate-400)" stroke-width="1" />
          <polygon points="0,-8 -2.6,0 2.6,0" fill="var(--color-compass-north)" transform="rotate(35)" />
          <polygon points="0,8 -2.6,0 2.6,0" fill="var(--color-slate-600)" transform="rotate(35)" />
          <circle r="1.2" fill="var(--color-surface)" stroke="var(--color-slate-600)" stroke-width="0.6" />
        </svg>
      </RouterLink>
      <div class="flex items-center gap-2">
        <SettingsMenu />
        <LanguageSwitcher />
      </div>
    </div>
    <main id="main" tabindex="-1" class="outline-none">
      <RouterView />
    </main>
    <NeedleCursor />
  </div>
</template>
