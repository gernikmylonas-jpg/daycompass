<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useStreakStore } from '../stores/streak'
import { useNuggetsStore } from '../stores/nuggets'
import NuggetIcon from './NuggetIcon.vue'

// Your name with the length of your daily streak next to it; opens your profile.
const { t } = useI18n()
const auth = useAuthStore()
const streak = useStreakStore()
const nuggets = useNuggetsStore()

onMounted(() => {
  if (!streak.loaded) streak.fetch()
  if (!nuggets.data) nuggets.fetch()
})
</script>

<template>
  <RouterLink to="/profile" :title="t('profile.open')"
    class="inline-flex items-center gap-2 rounded-lg px-2 py-1 text-sm text-slate-700 hover:bg-slate-100">
    <span class="font-medium">{{ auth.user?.name }}</span>
    <!-- quiet placeholders until the numbers arrive, then the real chips fade in -->
    <span v-if="!streak.loaded" class="inline-block h-5 w-16 rounded-full bg-slate-200 animate-pulse" aria-hidden="true"></span>
    <span v-else :class="['chip-in inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs tabular-nums',
        streak.current > 0 ? 'border-slate-400 text-streak' : 'border-slate-300 text-slate-500']"
      :title="streak.current > 0 && !streak.activeToday ? t('streak.keep') : t('streak.title')">
      <span aria-hidden="true">🔥</span>{{ t('streak.days', streak.current) }}
    </span>
    <span v-if="!nuggets.data" class="inline-block h-5 w-10 rounded-full bg-slate-200 animate-pulse" aria-hidden="true"></span>
    <span v-else class="chip-in inline-flex items-center gap-1 rounded-full border border-slate-300 px-2 py-0.5 text-xs tabular-nums text-slate-700"
      :title="t('nuggets.title')"><NuggetIcon :size="13" />{{ nuggets.data.balance }}</span>
  </RouterLink>
</template>

<style scoped>
.chip-in { animation: chip-in 0.35s ease-out; }
@keyframes chip-in { from { opacity: 0; transform: translateY(2px); } to { opacity: 1; transform: none; } }
</style>
