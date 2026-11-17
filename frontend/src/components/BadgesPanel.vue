<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBadgesStore, type BadgeStatus } from '../stores/badges'
import { BADGE_ART, BADGE_GROUPS, artFor } from '../badgeArt'
import BadgeIcon from './BadgeIcon.vue'

const { t, te } = useI18n()
const store = useBadgesStore()

// the order of the table in badgeArt.ts is the order of progress (easiest first), not alphabetical
const ORDER = Object.keys(BADGE_ART)
const orderOf = (code: string) => {
  const i = ORDER.indexOf(code)
  return i < 0 ? ORDER.length : i
}

const earnedCount = computed(() => store.badges.filter((b) => b.earned).length)

// badges grouped by the compass direction they belong to
const sections = computed(() =>
  BADGE_GROUPS.map((g) => {
    const items = store.badges
      .filter((b) => (artFor(b.code)?.group ?? 'general') === g.key)
      .sort((x, y) => orderOf(x.code) - orderOf(y.code))
    return { ...g, items, earned: items.filter((b) => b.earned).length }
  }).filter((g) => g.items.length > 0),
)

// Texts come from the language files; the stored text is only a fallback for unknown codes.
const badgeName = (b: BadgeStatus) => (te(`badges.${b.code}.name`) ? t(`badges.${b.code}.name`) : b.name)
const badgeDescription = (b: BadgeStatus) =>
  te(`badges.${b.code}.description`) ? t(`badges.${b.code}.description`) : b.description

onMounted(() => {
  store.fetchBadges().catch(() => {})
})
</script>

<template>
  <section class="bg-surface rounded-xl shadow p-4 space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-bold text-slate-800">{{ t('badges.title') }}</h2>
      <span class="text-sm text-slate-500 tabular-nums">{{ earnedCount }} / {{ store.badges.length }}</span>
    </div>

    <div v-for="g in sections" :key="g.key">
      <h3 class="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-2">
        <span v-if="g.direction" class="w-6 h-6 rounded-full border-2 text-[0.65rem] font-bold inline-flex items-center justify-center"
          :style="{ borderColor: `var(${g.accent})` }" aria-hidden="true">{{ t(`compass.${g.direction}`) }}</span>
        <span>{{ t(`badges.groups.${g.key}`) }}</span>
        <span class="text-xs font-normal text-slate-500 tabular-nums">{{ g.earned }}/{{ g.items.length }}</span>
      </h3>
      <ul class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <li v-for="b in g.items" :key="b.code"
          :class="['rounded-lg border p-3 flex flex-col items-center text-center gap-1',
            b.earned ? 'border-amber-300 bg-amber-50' : 'border-slate-200 bg-slate-50']"
          :title="badgeDescription(b)">
          <BadgeIcon :code="b.code" :fallback="b.icon" :earned="b.earned" :size="56" />
          <p :class="['text-sm font-medium', b.earned ? 'text-slate-800' : 'text-slate-600']">{{ badgeName(b) }}</p>
          <p class="text-xs text-slate-500">{{ badgeDescription(b) }}</p>
          <span class="sr-only">{{ b.earned ? t('badges.earned') : t('badges.locked') }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
