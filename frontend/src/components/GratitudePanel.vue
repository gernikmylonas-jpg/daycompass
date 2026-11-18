<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { formatDate } from '../i18n/dates'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'

// A few lines of gratitude each evening (up to five a day). They are yours alone and only exist once you write them.
interface Item { id: string; date: string; text: string }
const { t } = useI18n()
const badges = useBadgesStore()
const items = ref<Item[]>([])
const total = ref(0)
const text = ref('')
const error = ref('')

const groups = computed(() => {
  const map = new Map<string, Item[]>()
  for (const i of items.value) map.set(i.date, [...(map.get(i.date) ?? []), i])
  return [...map.entries()]
})

async function load() {
  try {
    const { data } = await api.get<{ total: number; items: Item[] }>('/api/gratitude')
    items.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
async function add() {
  error.value = ''
  if (!text.value.trim()) return
  try {
    const { data: saved } = await api.post<{ new_badges?: BadgeInfo[] }>('/api/gratitude', { text: text.value })
    await badges.announce(saved.new_badges)
    text.value = ''
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
async function remove(i: Item) {
  try {
    await api.delete(`/api/gratitude/${i.id}`)
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
    <section class="bg-surface rounded-xl shadow p-4 space-y-3 border-t-4 border-purple-500">
      <h3 class="font-bold text-slate-800">{{ t('gratitude.title') }}</h3>
      <p class="text-sm text-slate-600">{{ t('gratitude.prompt') }}</p>
      <form @submit.prevent="add" class="flex gap-2">
        <input v-model="text" type="text" maxlength="200" :placeholder="t('gratitude.placeholder')" :aria-label="t('gratitude.placeholder')" class="flex-1 min-w-0 border rounded-lg px-3 py-2 text-sm" />
        <button type="submit" class="bg-primary text-on-primary rounded-lg px-4 text-sm hover:bg-primary-hover">+</button>
      </form>
      <p class="text-xs text-slate-500">{{ t('gratitude.total', total) }}</p>
    </section>
    <section v-if="groups.length" class="bg-surface rounded-xl shadow p-4 space-y-3">
      <div v-for="[date, list] in groups" :key="date">
        <h4 class="text-xs font-semibold text-slate-500">{{ formatDate(date) }}</h4>
        <ul class="text-sm text-slate-700 space-y-1 mt-1">
          <li v-for="i in list" :key="i.id" class="flex items-start justify-between gap-2"><span class="break-words">🙏 {{ i.text }}</span>
            <button @click="remove(i)" :aria-label="t('home.remove')" :title="t('home.remove')" class="w-6 h-6 shrink-0 inline-flex items-center justify-center rounded text-slate-500 hover:text-danger hover:bg-slate-100">✕</button></li>
        </ul>
      </div>
    </section>
  </div>
</template>
