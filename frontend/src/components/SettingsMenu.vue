<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { THEMES, MODES, useSettingsStore } from '../stores/settings'
import { radioKeydown } from '../a11y'

const { t } = useI18n()
const settings = useSettingsStore()

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const trigger = ref<HTMLButtonElement | null>(null)

function close(restoreFocus: boolean) {
  open.value = false
  if (restoreFocus) trigger.value?.focus()
}

// move keyboard focus into the panel, onto the current style
watch(open, async (isOpen) => {
  if (!isOpen) return
  await nextTick()
  root.value?.querySelector<HTMLElement>('[role="radio"][aria-checked="true"]')?.focus()
})

function onDocumentClick(ev: MouseEvent) {
  if (open.value && root.value && !root.value.contains(ev.target as Node)) open.value = false
}

function onKey(ev: KeyboardEvent) {
  if (ev.key === 'Escape' && open.value) close(true)
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
  document.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div ref="root" class="relative">
    <button ref="trigger" type="button" @click="open = !open"
      :aria-label="t('settings.title')" aria-haspopup="dialog" :aria-expanded="open" aria-controls="settings-panel"
      class="flex items-center gap-2 bg-surface border border-slate-400 rounded-lg px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 shadow-sm">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
      <span class="hidden sm:inline">{{ t('settings.title') }}</span>
    </button>

    <div v-if="open" id="settings-panel" role="dialog" :aria-label="t('settings.title')"
      class="absolute right-0 mt-1 w-72 bg-surface border border-slate-200 rounded-lg shadow-lg p-3 z-50 space-y-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{{ t('settings.mode') }}</p>
        <div class="grid grid-cols-3 gap-1" role="radiogroup" :aria-label="t('settings.mode')">
          <button v-for="m in MODES" :key="m" type="button" role="radio"
            :aria-checked="settings.mode === m" :tabindex="settings.mode === m ? 0 : -1"
            @click="settings.setMode(m)" @keydown="radioKeydown"
            :class="['rounded-lg border px-2 py-1.5 text-sm flex flex-col items-center gap-0.5',
              settings.mode === m ? 'border-slate-400 bg-slate-50 font-semibold text-slate-900' : 'border-slate-200 text-slate-700 hover:bg-slate-50']">
            <span aria-hidden="true">{{ m === 'light' ? '☀' : m === 'dark' ? '☾' : '◐' }}</span>
            <span class="text-xs">{{ t(`settings.modes.${m}`) }}</span>
          </button>
        </div>
      </div>

      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{{ t('settings.theme') }}</p>
        <div class="space-y-1" role="radiogroup" :aria-label="t('settings.theme')">
          <button v-for="th in THEMES" :key="th.id" type="button" role="radio"
            :aria-checked="settings.theme === th.id" :tabindex="settings.theme === th.id ? 0 : -1"
            @click="settings.setTheme(th.id)" @keydown="radioKeydown"
            :class="['w-full flex items-center gap-3 rounded-lg px-2 py-1.5 text-sm text-left border',
              settings.theme === th.id ? 'border-slate-400 bg-slate-50 font-semibold text-slate-900' : 'border-transparent text-slate-700 hover:bg-slate-50']">
            <svg viewBox="0 0 40 40" width="36" height="36" class="shrink-0 rounded-md" aria-hidden="true">
              <rect width="40" height="40" :fill="th.swatch.page" />
              <circle cx="20" cy="20" r="14" :fill="th.swatch.surface" :stroke="th.swatch.primary" stroke-width="1.5" />
              <polygon points="20,8 17,20 23,20" :fill="th.swatch.north" />
              <polygon points="20,32 17,20 23,20" :fill="th.swatch.primary" opacity="0.55" />
              <circle cx="20" cy="20" r="1.8" :fill="th.swatch.surface" :stroke="th.swatch.primary" stroke-width="1" />
            </svg>
            <span class="flex-1">{{ t(`settings.themes.${th.id}`) }}</span>
            <span v-if="settings.theme === th.id" class="text-ok" aria-hidden="true">✓</span>
          </button>
        </div>
      </div>

      <label class="flex items-start gap-3 border-t border-slate-200 pt-3 cursor-pointer">
        <input v-model="settings.needleCursor" type="checkbox" class="mt-1 h-4 w-4" />
        <span>
          <span class="block text-sm font-medium text-slate-800">{{ t('settings.cursor') }}</span>
          <span class="block text-xs text-slate-500">{{ t('settings.cursorHint') }}</span>
        </span>
      </label>

      <p v-if="settings.syncError" role="status" class="text-xs text-danger">{{ t('settings.syncError') }}</p>
    </div>
  </div>
</template>
