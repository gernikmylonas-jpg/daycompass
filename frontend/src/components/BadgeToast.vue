<script setup lang="ts">
import { useBadgesStore } from '../stores/badges'

const store = useBadgesStore()
</script>

<template>
  <div v-if="store.toasts.length" class="fixed bottom-4 right-4 space-y-2 z-50">
    <div v-for="b in store.toasts" :key="b.code"
      class="bg-slate-800 text-white rounded-xl shadow-lg px-4 py-3 flex items-center gap-3 cursor-pointer"
      @click="store.dismiss()">
      <span class="text-2xl">{{ b.icon }}</span>
      <div>
        <p class="text-xs text-slate-300">Νέο badge!</p>
        <p class="font-bold text-sm">{{ b.name }}</p>
        <p class="text-xs text-slate-300">{{ b.description }}</p>
      </div>
    </div>
  </div>
</template>
