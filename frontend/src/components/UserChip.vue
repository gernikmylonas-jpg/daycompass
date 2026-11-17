<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useStreakStore } from '../stores/streak'

// Your name with the length of your daily streak next to it; opens your profile.
const { t } = useI18n()
const auth = useAuthStore()
const streak = useStreakStore()

onMounted(() => {
  if (!streak.loaded) streak.fetch()
})
</script>

<template>
  <RouterLink to="/profile" :title="t('profile.open')"
    class="inline-flex items-center gap-2 rounded-lg px-2 py-1 text-sm text-slate-700 hover:bg-slate-100">
    <span class="font-medium">{{ auth.user?.name }}</span>
    <span :class="['inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs tabular-nums',
        streak.current > 0 ? 'border-slate-400 text-streak' : 'border-slate-300 text-slate-500']"
      :title="streak.current > 0 && !streak.activeToday ? t('streak.keep') : t('streak.title')">
      <span aria-hidden="true">🔥</span>{{ t('streak.days', streak.current) }}
    </span>
  </RouterLink>
</template>
