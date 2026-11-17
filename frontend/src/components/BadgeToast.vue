<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useBadgesStore } from '../stores/badges'

const { t, te } = useI18n()
const store = useBadgesStore()

// Badge texts come from the backend (Greek); prefer the translation for known codes.
function badgeName(code: string, fallback: string) {
  return te(`badges.${code}.name`) ? t(`badges.${code}.name`) : fallback
}
function badgeDescription(code: string, fallback: string) {
  return te(`badges.${code}.description`) ? t(`badges.${code}.description`) : fallback
}
</script>

<template>
  <div v-if="store.toasts.length" class="fixed bottom-4 right-4 space-y-2 z-50">
    <div v-for="b in store.toasts" :key="b.code"
      class="bg-slate-800 text-white rounded-xl shadow-lg px-4 py-3 flex items-center gap-3 cursor-pointer"
      @click="store.dismiss()">
      <span class="text-2xl">{{ b.icon }}</span>
      <div>
        <p class="text-xs text-slate-300">{{ t('badges.newBadge') }}</p>
        <p class="font-bold text-sm">{{ badgeName(b.code, b.name) }}</p>
        <p class="text-xs text-slate-300">{{ badgeDescription(b.code, b.description) }}</p>
      </div>
    </div>
  </div>
</template>
