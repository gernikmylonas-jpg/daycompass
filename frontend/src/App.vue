<script setup lang="ts">
import LanguageSwitcher from './components/LanguageSwitcher.vue'
</script>

<template>
  <div class="bg-slate-100">
    <div class="h-12 px-4 md:px-8 flex items-center justify-end">
      <LanguageSwitcher />
    </div>
    <RouterView />
  </div>
</template>
