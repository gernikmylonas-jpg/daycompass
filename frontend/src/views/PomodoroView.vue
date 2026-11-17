<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import BadgeToast from '../components/BadgeToast.vue'
import PomodoroPanel from '../components/PomodoroPanel.vue'

const { t } = useI18n()
</script>

<template>
  <div class="min-h-[calc(100vh-3rem)] bg-page p-4 md:p-8">
    <div class="max-w-2xl mx-auto space-y-4">
      <header class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-slate-800">{{ t('pomodoro.title') }}</h1>
        <RouterLink to="/"
          class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover">
          {{ t('common.backToCompass') }}
        </RouterLink>
      </header>

      <PomodoroPanel />
    </div>
    <BadgeToast />
  </div>
</template>
