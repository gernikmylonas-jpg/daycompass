<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useBadgesStore } from '../stores/badges'
import BadgeIcon from './BadgeIcon.vue'

const { t, te } = useI18n()
const store = useBadgesStore()

// Badge texts come from the language files; the stored text is only a fallback.
function badgeName(code: string, fallback: string) {
  return te(`badges.${code}.name`) ? t(`badges.${code}.name`) : fallback
}
function badgeDescription(code: string, fallback: string) {
  return te(`badges.${code}.description`) ? t(`badges.${code}.description`) : fallback
}
</script>

<template>
  <div v-if="store.toasts.length" class="fixed bottom-4 right-4 space-y-2 z-50" role="status" aria-live="polite">
    <div v-for="b in store.toasts" :key="b.code"
      class="bg-primary text-on-primary rounded-xl shadow-lg px-4 py-3 flex items-center gap-3 cursor-pointer"
      @click="store.dismiss()">
      <span class="rounded-full bg-surface p-0.5 shrink-0"><BadgeIcon :code="b.code" :fallback="b.icon" :size="44" /></span>
      <div>
        <p class="text-xs opacity-75">{{ t('badges.newBadge') }}</p>
        <p class="font-bold text-sm">{{ badgeName(b.code, b.name) }}</p>
        <p class="text-xs opacity-75">{{ badgeDescription(b.code, b.description) }}</p>
      </div>
    </div>
  </div>
</template>
