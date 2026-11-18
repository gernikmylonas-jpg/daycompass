<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import api from '../api'

// A round picture: the member's photo if they chose to share one with their groups, otherwise their initial.
const props = withDefaults(defineProps<{ userId: string; name: string; has: boolean; size?: number }>(), { size: 32 })
const cache = (globalThis as { __avatarCache?: Map<string, string> }).__avatarCache ??= new Map<string, string>()
const url = ref<string | null>(null)
const initial = computed(() => (props.name.trim()[0] ?? '?').toUpperCase())

async function load() {
  if (!props.has) { url.value = null; return }
  const hit = cache.get(props.userId)
  if (hit) { url.value = hit; return }
  try {
    const { data } = await api.get<Blob>(`/api/profile-photo/user/${props.userId}`, { responseType: 'blob' })
    const made = URL.createObjectURL(data)
    cache.set(props.userId, made)
    url.value = made
  } catch {
    url.value = null
  }
}
watch(() => [props.userId, props.has], load)
onMounted(load)
</script>

<template>
  <span class="inline-flex items-center justify-center rounded-full overflow-hidden bg-slate-200 text-slate-600 font-semibold shrink-0 border border-slate-300"
    :style="{ width: size + 'px', height: size + 'px', fontSize: size * 0.45 + 'px' }" aria-hidden="true">
    <img v-if="url" :src="url" alt="" class="w-full h-full object-cover" />
    <template v-else>{{ initial }}</template>
  </span>
</template>
