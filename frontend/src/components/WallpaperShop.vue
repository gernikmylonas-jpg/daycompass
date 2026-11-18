<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiErrorMessage } from '../i18n/errors'
import { formatDate } from '../i18n/dates'
import { useNuggetsStore } from '../stores/nuggets'
import { useSettingsStore } from '../stores/settings'
import NuggetIcon from './NuggetIcon.vue'
import WallpaperArt from './WallpaperArt.vue'

// Spend gold nuggets (1 per 10 points) on wallpapers; the list below the shop remembers every purchase.
const { t } = useI18n()
const nuggets = useNuggetsStore()
const settings = useSettingsStore()
const error = ref('')
const busy = ref('')

const info = computed(() => nuggets.data)
const history = computed(() => [...(info.value?.unlocked ?? [])].reverse())

async function buy(id: string) {
  error.value = ''
  busy.value = id
  try {
    await nuggets.unlock(id)
    settings.wallpaper = id // use it straight away
    settings.wallpapersOn = true
  } catch (e) {
    error.value = apiErrorMessage(e)
  } finally {
    busy.value = ''
  }
}

function choose(id: string) {
  settings.wallpaper = id
  settings.wallpapersOn = true
}

onMounted(() => nuggets.fetch())
</script>

<template>
  <section v-if="info" id="wallpapers" class="bg-surface rounded-xl shadow p-4 space-y-4 border-t-4 border-amber-500">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="font-bold text-slate-800">{{ t('nuggets.title') }}</h2>
        <p class="text-xs text-slate-500">{{ t('nuggets.rule', { n: info.points_per_nugget }) }}</p>
      </div>
      <div class="text-right">
        <p class="text-3xl font-bold text-slate-800 tabular-nums flex items-center justify-end gap-2" style="font-family: var(--font-display)">
          <NuggetIcon :size="30" />{{ info.balance }}
        </p>
        <p class="text-xs text-slate-500">{{ t('nuggets.nextIn', info.next_in) }}</p>
      </div>
    </div>
    <p class="text-xs text-slate-500">{{ t('nuggets.summary', { earned: info.earned, spent: info.spent }) }}</p>
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>

    <ul class="grid grid-cols-2 md:grid-cols-3 gap-3">
      <li v-for="w in info.catalog" :key="w.id" class="rounded-xl border border-slate-200 overflow-hidden flex flex-col">
        <div class="aspect-video bg-slate-100"><WallpaperArt :id="w.id" /></div>
        <div class="p-2 flex-1 flex flex-col gap-1">
          <p class="text-sm font-semibold text-slate-800">{{ t(`wallpapers.${w.id}.name`) }}</p>
          <p class="text-xs text-slate-500 flex-1">{{ t(`wallpapers.${w.id}.description`) }}</p>
          <template v-if="nuggets.isUnlocked(w.id)">
            <button type="button" @click="choose(w.id)" :aria-pressed="settings.wallpapersOn && settings.wallpaper === w.id"
              :class="['rounded-lg px-3 py-1.5 text-xs', settings.wallpapersOn && settings.wallpaper === w.id ? 'bg-primary text-on-primary' : 'border border-slate-400 text-slate-700 hover:bg-slate-50']">
              {{ settings.wallpapersOn && settings.wallpaper === w.id ? t('nuggets.inUse') : t('nuggets.use') }}
            </button>
          </template>
          <button v-else type="button" :disabled="busy === w.id || info.balance < w.cost" @click="buy(w.id)"
            class="rounded-lg px-3 py-1.5 text-xs border border-slate-400 text-slate-800 hover:bg-slate-50 disabled:opacity-50 flex items-center justify-center gap-1">
            <NuggetIcon :size="14" />{{ w.cost }} · {{ t('nuggets.unlock') }}
          </button>
          <p v-if="!nuggets.isUnlocked(w.id) && info.balance < w.cost" class="text-[0.7rem] text-slate-500">{{ t('nuggets.missing', { n: w.cost - info.balance }) }}</p>
        </div>
      </li>
    </ul>

    <div>
      <h3 class="text-sm font-bold text-slate-800 mb-1">{{ t('nuggets.history') }}</h3>
      <ul v-if="history.length" class="divide-y text-sm">
        <li v-for="h in history" :key="h.id" class="py-1.5 flex items-center justify-between text-slate-700">
          <span>{{ t(`wallpapers.${h.id}.name`) }} <span class="text-xs text-slate-500">· {{ formatDate(h.unlocked_at.slice(0, 10)) }}</span></span>
          <span class="flex items-center gap-1 tabular-nums text-slate-600">−{{ h.cost }} <NuggetIcon :size="14" /></span>
        </li>
      </ul>
      <p v-else class="text-sm text-slate-500">{{ t('nuggets.noHistory') }}</p>
    </div>
  </section>
</template>
