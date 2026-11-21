<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Flag from './Flag.vue'
import { LOCALES, setLocale } from '../i18n'
import { radioKeydown } from '../a11y'

const { t, locale } = useI18n()

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const trigger = ref<HTMLButtonElement | null>(null)

const current = computed(() => LOCALES.find((l) => l.code === locale.value) ?? LOCALES[0])

function close(restoreFocus: boolean) {
  open.value = false
  if (restoreFocus) trigger.value?.focus()
}

// move keyboard focus into the menu, onto the current language
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
  <div ref="root" class="relative" data-tour="language">
    <button ref="trigger" type="button" @click="open = !open"
      :aria-label="t('common.language')" aria-haspopup="true" :aria-expanded="open" aria-controls="language-menu"
      class="flex items-center gap-2 bg-surface border border-slate-400 rounded-lg px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 shadow-sm">
      <Flag :code="current.code" />
      <span class="font-medium uppercase">{{ current.code }}</span>
      <span class="text-slate-500 text-xs" aria-hidden="true">▾</span>
    </button>

    <div v-if="open" id="language-menu" role="radiogroup" :aria-label="t('common.language')"
      class="absolute right-0 mt-1 w-44 bg-surface border border-slate-200 rounded-lg shadow-lg py-1 z-50">
      <button v-for="l in LOCALES" :key="l.code" type="button" role="radio"
        :aria-checked="l.code === locale" :tabindex="l.code === locale ? 0 : -1" :lang="l.code"
        @click="setLocale(l.code)" @keydown="radioKeydown"
        :class="['w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-slate-50',
          l.code === locale ? 'font-bold text-slate-900' : 'text-slate-700']">
        <Flag :code="l.code" />
        <span class="flex-1">{{ l.name }}</span>
        <span v-if="l.code === locale" class="text-ok" aria-hidden="true">✓</span>
      </button>
    </div>
  </div>
</template>
