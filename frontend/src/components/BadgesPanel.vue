<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBadgesStore } from '../stores/badges'

const { t, te } = useI18n()
const store = useBadgesStore()

const earnedCount = computed(() => store.badges.filter((b) => b.earned).length)

// Badge texts come from the backend (Greek); prefer the translation for known codes.
function badgeName(code: string, fallback: string) {
  return te(`badges.${code}.name`) ? t(`badges.${code}.name`) : fallback
}
function badgeDescription(code: string, fallback: string) {
  return te(`badges.${code}.description`) ? t(`badges.${code}.description`) : fallback
}

onMounted(() => {
  store.fetchBadges().catch(() => {})
})
</script>

<template>
  <section class="bg-white rounded-xl shadow p-4">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-lg font-bold text-slate-800">{{ t('badges.title') }}</h2>
      <span class="text-sm text-slate-500">{{ earnedCount }} / {{ store.badges.length }}</span>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div v-for="b in store.badges" :key="b.code"
        :title="badgeDescription(b.code, b.description)"
        :class="['rounded-lg border p-3 text-center', b.earned ? 'border-amber-300 bg-amber-50' : 'border-slate-200 bg-slate-50 opacity-50']">
        <p :class="['text-2xl', b.earned ? '' : 'grayscale']">{{ b.icon }}</p>
        <p class="text-sm font-medium text-slate-800 mt-1">{{ badgeName(b.code, b.name) }}</p>
        <p class="text-xs text-slate-500">{{ badgeDescription(b.code, b.description) }}</p>
      </div>
    </div>
  </section>
</template>
