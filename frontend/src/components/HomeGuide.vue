<script setup lang="ts">
import { ref, onMounted } from 'vue'

// Short, plain-language explanation of what each direction of the compass contains.
export interface GuideItem {
  id: string
  letter: string
  title: string
  text: string
  accent: string // CSS variable name, e.g. --color-teal-500
  soon?: boolean
}

defineProps<{ id: string; title: string; intro: string; closeLabel: string; items: GuideItem[] }>()
defineEmits<{ close: [] }>()

const closeBtn = ref<HTMLButtonElement | null>(null)
onMounted(() => closeBtn.value?.focus())
</script>

<template>
  <div :id="id" role="dialog" :aria-label="title"
    class="absolute left-0 top-full mt-2 z-40 w-[min(92vw,36rem)] bg-surface border border-slate-200 rounded-xl shadow-lg p-4 space-y-3 text-left">
    <div class="flex items-start justify-between gap-3">
      <h2 class="text-lg font-bold text-slate-800">{{ title }}</h2>
      <button ref="closeBtn" type="button" @click="$emit('close')" :aria-label="closeLabel" :title="closeLabel"
        class="w-7 h-7 inline-flex items-center justify-center rounded text-slate-500 hover:text-slate-900 hover:bg-slate-100 shrink-0">✕</button>
    </div>
    <p class="text-sm text-slate-600">{{ intro }}</p>

    <ul class="grid gap-2 sm:grid-cols-2">
      <li v-for="item in items" :key="item.id" class="flex items-start gap-3 rounded-lg p-2 hover:bg-slate-50">
        <span class="w-9 h-9 shrink-0 rounded-full border-2 flex items-center justify-center text-sm font-bold text-slate-700"
          :style="{ borderColor: `var(${item.accent})`, borderStyle: item.soon ? 'dashed' : 'solid' }" aria-hidden="true">{{ item.letter }}</span>
        <span class="text-sm">
          <span class="block font-semibold text-slate-800">{{ item.title }}</span>
          <span class="block text-slate-600">{{ item.text }}</span>
        </span>
      </li>
    </ul>
  </div>
</template>
