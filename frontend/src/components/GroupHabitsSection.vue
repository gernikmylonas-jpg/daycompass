<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'

// Habits the whole group does together (the group streak counts days when everyone did it) and small daily cheers.
interface Member { user_id: string; name: string; done: boolean }
interface Habit { id: string; name: string; group_streak: number; all_done_today: boolean; done_today: number; members_total: number; me_done: boolean; members: Member[] }
interface Cheers { received: { from: string; emoji: string }[]; sent_to: string[]; options: string[] }

const props = defineProps<{ groupId: string; members: { user_id: string; name: string; is_me: boolean }[] }>()
const { t } = useI18n()
const badges = useBadgesStore()
const habits = ref<Habit[]>([])
const cheers = ref<Cheers>({ received: [], sent_to: [], options: [] })
const name = ref('')
const error = ref('')

async function reload() {
  try {
    const [h, c] = await Promise.all([
      api.get<Habit[]>(`/api/groups/${props.groupId}/habits`),
      api.get<Cheers>(`/api/groups/${props.groupId}/cheers`),
    ])
    habits.value = h.data
    cheers.value = c.data
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
async function act(fn: () => Promise<unknown>) {
  error.value = ''
  try {
    const res = (await fn()) as { data?: { new_badges?: BadgeInfo[] } } | undefined
    await badges.announce(res?.data?.new_badges)
    await reload()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
const add = () => act(async () => { if (name.value.trim()) { await api.post(`/api/groups/${props.groupId}/habits`, { name: name.value }); name.value = '' } })
const check = (h: Habit) => act(() => api.post(`/api/groups/${props.groupId}/habits/${h.id}/check`))
const remove = (h: Habit) => { if (confirm(t('groupHabits.confirmDelete'))) return act(() => api.delete(`/api/groups/${props.groupId}/habits/${h.id}`)) }
const cheer = (to: string, emoji: string) => act(() => api.post(`/api/groups/${props.groupId}/cheers`, { to_user_id: to, emoji }))

watch(() => props.groupId, reload, { immediate: true })
defineExpose({ reload })
</script>

<template>
  <section class="space-y-3 border-t border-slate-200 pt-3">
    <h3 class="font-bold text-slate-800">{{ t('groupHabits.title') }}</h3>
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>

    <ul v-if="habits.length" class="space-y-2">
      <li v-for="h in habits" :key="h.id" class="rounded-lg border border-slate-200 p-3">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="font-medium text-slate-800 break-words">{{ h.name }}</p>
            <p class="text-xs text-slate-500">{{ t('groupHabits.today', { done: h.done_today, total: h.members_total }) }}<span v-if="h.group_streak > 0" class="text-streak"> · 🔥 {{ t('steps.streak', h.group_streak) }}</span></p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span v-if="h.me_done" class="text-xs text-ok">{{ t('groupHabits.done') }}</span>
            <button v-else type="button" @click="check(h)" class="bg-primary text-on-primary rounded-lg px-3 py-1 text-sm hover:bg-primary-hover">{{ t('groupHabits.check') }}</button>
            <button type="button" @click="remove(h)" :aria-label="t('home.remove')" :title="t('home.remove')" class="w-6 h-6 inline-flex items-center justify-center rounded text-slate-500 hover:text-danger hover:bg-slate-100">✕</button>
          </div>
        </div>
        <p class="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
          <span v-for="m in h.members" :key="m.user_id" :class="m.done ? 'text-ok' : 'text-slate-500'">{{ m.done ? '✓' : '·' }} {{ m.name }}</span>
        </p>
        <p v-if="h.all_done_today" class="text-xs text-ok mt-1">🎉 {{ t('groupHabits.everyone') }}</p>
      </li>
    </ul>
    <p v-else class="text-sm text-slate-500">{{ t('groupHabits.none') }}</p>

    <form @submit.prevent="add" class="flex gap-2">
      <input v-model="name" type="text" maxlength="60" :placeholder="t('groupHabits.placeholder')" :aria-label="t('groupHabits.placeholder')" class="flex-1 min-w-0 border rounded-lg px-3 py-1.5 text-sm" />
      <button type="submit" class="bg-primary text-on-primary rounded-lg px-3 text-sm hover:bg-primary-hover">+</button>
    </form>

    <div class="space-y-1">
      <h4 class="text-sm font-semibold text-slate-800">{{ t('groupHabits.cheers') }}</h4>
      <p v-if="cheers.received.length" class="text-sm text-slate-700">{{ t('groupHabits.received') }}: <span v-for="(c, i) in cheers.received" :key="i" class="mr-2">{{ c.emoji }} <span class="text-xs text-slate-500">{{ c.from }}</span></span></p>
      <ul class="text-sm space-y-1">
        <li v-for="m in members.filter((x) => !x.is_me)" :key="m.user_id" class="flex flex-wrap items-center gap-2">
          <span class="text-slate-700 w-28 truncate">{{ m.name }}</span>
          <template v-if="cheers.sent_to.includes(m.user_id)"><span class="text-xs text-slate-500">{{ t('groupHabits.cheered') }}</span></template>
          <template v-else>
            <button v-for="e in cheers.options" :key="e" type="button" @click="cheer(m.user_id, e)" :aria-label="`${e} → ${m.name}`"
              class="w-8 h-8 rounded-full border border-slate-300 hover:bg-slate-50 active:scale-95 transition">{{ e }}</button>
          </template>
        </li>
      </ul>
      <p class="text-xs text-slate-500">{{ t('groupHabits.cheerHint') }}</p>
    </div>
  </section>
</template>
