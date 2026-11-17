<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Flag from './Flag.vue'
import { LOCALES, setLocale, type LocaleCode } from '../i18n'

const { t, locale } = useI18n()

const open = ref(false)
const root = ref<HTMLElement | null>(null)

const current = computed(() => LOCALES.find((l) => l.code === locale.value) ?? LOCALES[0])

function choose(code: LocaleCode) {
  setLocale(code)
  open.value = false
}

function onDocumentClick(ev: MouseEvent) {
  if (open.value && root.value && !root.value.contains(ev.target as Node)) open.value = false
}

function onKey(ev: KeyboardEvent) {
  if (ev.key === 'Escape') open.value = false
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
    <button type="button" @click="open = !open"
      :aria-label="t('common.language')" aria-haspopup="listbox" :aria-expanded="open"
      class="flex items-center gap-2 bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 shadow-sm">
      <Flag :code="current.code" />
      <span class="font-medium uppercase">{{ current.code }}</span>
      <span class="text-slate-400 text-xs">▾</span>
    </button>

    <ul v-if="open" role="listbox"
      class="absolute right-0 mt-1 w-44 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-50">
      <li v-for="l in LOCALES" :key="l.code" role="option" :aria-selected="l.code === locale">
        <button type="button" @click="choose(l.code)"
          :class="['w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-slate-50',
            l.code === locale ? 'font-bold text-slate-900' : 'text-slate-700']">
          <Flag :code="l.code" />
          <span class="flex-1">{{ l.name }}</span>
          <span v-if="l.code === locale" class="text-green-600">✓</span>
        </button>
      </li>
    </ul>
  </div>
</template>
