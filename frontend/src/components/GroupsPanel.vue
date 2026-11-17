<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'

interface GroupSummary {
  id: string
  name: string
  description: string | null
  invite_code: string
  is_owner: boolean
  member_count: number
  my_rank: number
}

interface LeaderboardEntry {
  rank: number
  user_id: string
  name: string
  points: number
  is_me: boolean
}

interface GroupDetail {
  id: string
  name: string
  description: string | null
  invite_code: string
  is_owner: boolean
  period: 'all' | 'week'
  leaderboard: LeaderboardEntry[]
}

const { t } = useI18n()
const badgesStore = useBadgesStore()
const groups = ref<GroupSummary[]>([])
const selected = ref<GroupDetail | null>(null)
const period = ref<'all' | 'week'>('all')
const newName = ref('')
const newDescription = ref('')
const joinCode = ref('')
const error = ref('')
const copied = ref(false)
const live = ref<'connecting' | 'live' | 'offline'>('offline')

const medals = ['🥇', '🥈', '🥉']
const selectedId = computed(() => selected.value?.id ?? null)

function showError(e: unknown) {
  error.value = apiErrorMessage(e)
}

const WS_BASE = String(api.defaults.baseURL).replace(/^http/, 'ws')
const MAX_BACKOFF_MS = 15000
const PING_MS = 25000

let socket: WebSocket | null = null
let socketGroupId: string | null = null
let retryTimer: number | undefined
let pingTimer: number | undefined
let refreshTimer: number | undefined
let attempt = 0

function clearTimers() {
  window.clearTimeout(retryTimer)
  window.clearInterval(pingTimer)
  window.clearTimeout(refreshTimer)
}

function disconnectSocket() {
  clearTimers()
  socketGroupId = null
  if (socket) {
    socket.onclose = null
    socket.close()
    socket = null
  }
  live.value = 'offline'
}

function connectSocket(groupId: string) {
  disconnectSocket()
  socketGroupId = groupId
  attempt = 0
  openSocket()
}

function openSocket() {
  const groupId = socketGroupId
  const token = localStorage.getItem('token')
  if (!groupId || !token) return
  live.value = 'connecting'
  const ws = new WebSocket(`${WS_BASE}/api/groups/${groupId}/ws?token=${encodeURIComponent(token)}`)
  socket = ws

  ws.onopen = () => {
    attempt = 0
    live.value = 'live'
    // A change may have happened while we were disconnected.
    refreshSelected()
    window.clearInterval(pingTimer)
    pingTimer = window.setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping')
    }, PING_MS)
  }

  ws.onmessage = (ev) => {
    let msg: { type?: string; group_id?: string }
    try {
      msg = JSON.parse(ev.data)
    } catch {
      return
    }
    if (msg.group_id !== socketGroupId) return
    if (msg.type === 'group_deleted') {
      disconnectSocket()
      selected.value = null
      loadGroups()
    } else {
      // Debounce bursts of events into a single refetch.
      window.clearTimeout(refreshTimer)
      refreshTimer = window.setTimeout(refreshSelected, 150)
    }
  }

  ws.onclose = (ev) => {
    window.clearInterval(pingTimer)
    live.value = 'offline'
    if (socket !== ws) return
    socket = null
    if (ev.code === 4401 || ev.code === 4404) return // auth/membership problem: retrying won't help
    const delay = Math.min(MAX_BACKOFF_MS, 1000 * 2 ** attempt)
    attempt += 1
    retryTimer = window.setTimeout(openSocket, delay)
  }
}

async function refreshSelected() {
  const id = socketGroupId
  if (!id) return
  try {
    const { data } = await api.get<GroupDetail>(`/api/groups/${id}`, { params: { period: period.value } })
    if (socketGroupId === id) selected.value = data
    loadGroups()
  } catch {
    // transient failure; the next event or reconnect will refresh again
  }
}

async function loadGroups() {
  try {
    const { data } = await api.get<GroupSummary[]>('/api/groups')
    groups.value = data
    if (selected.value && !data.some((g) => g.id === selected.value!.id)) selected.value = null
  } catch (e) {
    showError(e)
  }
}

async function openGroup(id: string) {
  error.value = ''
  try {
    const { data } = await api.get<GroupDetail>(`/api/groups/${id}`, { params: { period: period.value } })
    const changed = selected.value?.id !== data.id
    selected.value = data
    if (changed) connectSocket(data.id)
  } catch (e) {
    showError(e)
  }
}

async function setPeriod(p: 'all' | 'week') {
  period.value = p
  if (selectedId.value) await openGroup(selectedId.value)
}

async function createGroup() {
  error.value = ''
  if (!newName.value.trim()) return
  try {
    const { data } = await api.post<GroupSummary & { new_badges?: BadgeInfo[] }>('/api/groups', {
      name: newName.value,
      description: newDescription.value || null,
    })
    await badgesStore.announce(data.new_badges)
    newName.value = ''
    newDescription.value = ''
    await loadGroups()
    await openGroup(data.id)
  } catch (e) {
    showError(e)
  }
}

async function joinGroup() {
  error.value = ''
  if (!joinCode.value.trim()) return
  try {
    const { data } = await api.post<GroupSummary & { new_badges?: BadgeInfo[] }>('/api/groups/join', { invite_code: joinCode.value })
    await badgesStore.announce(data.new_badges)
    joinCode.value = ''
    await loadGroups()
    await openGroup(data.id)
  } catch (e) {
    showError(e)
  }
}

async function leaveGroup() {
  if (!selected.value || !confirm(t('groups.confirmLeave'))) return
  try {
    await api.delete(`/api/groups/${selected.value.id}/members/me`)
    disconnectSocket()
    selected.value = null
    await loadGroups()
  } catch (e) {
    showError(e)
  }
}

async function deleteGroup() {
  if (!selected.value || !confirm(t('groups.confirmDelete'))) return
  try {
    await api.delete(`/api/groups/${selected.value.id}`)
    disconnectSocket()
    selected.value = null
    await loadGroups()
  } catch (e) {
    showError(e)
  }
}

async function copyCode() {
  if (!selected.value) return
  try {
    await navigator.clipboard.writeText(selected.value.invite_code)
    copied.value = true
    window.setTimeout(() => (copied.value = false), 1500)
  } catch {
    // clipboard unavailable
  }
}

onMounted(loadGroups)
onUnmounted(disconnectSocket)
</script>

<template>
  <div class="@container space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>

    <section class="grid @md:grid-cols-2 gap-4">
      <form @submit.prevent="createGroup" class="bg-surface rounded-xl shadow p-4 space-y-2">
        <h2 class="font-bold text-slate-800">{{ t('groups.newGroup') }}</h2>
        <input v-model="newName" maxlength="60" :placeholder="t('groups.namePlaceholder')" :aria-label="t('groups.namePlaceholder')"
          class="border rounded-lg px-3 py-2 text-sm w-full" />
        <input v-model="newDescription" maxlength="200" :placeholder="t('groups.descriptionPlaceholder')" :aria-label="t('groups.descriptionPlaceholder')"
          class="border rounded-lg px-3 py-2 text-sm w-full" />
        <button class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover">{{ t('groups.create') }}</button>
      </form>

      <form @submit.prevent="joinGroup" class="bg-surface rounded-xl shadow p-4 space-y-2">
        <h2 class="font-bold text-slate-800">{{ t('groups.joinTitle') }}</h2>
        <input v-model="joinCode" maxlength="8" :placeholder="t('groups.codePlaceholder')" :aria-label="t('groups.codePlaceholder')"
          class="border rounded-lg px-3 py-2 text-sm w-full uppercase tracking-widest" />
        <button class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover">{{ t('groups.join') }}</button>
      </form>
    </section>

    <section class="bg-surface rounded-xl shadow p-4">
      <h2 class="font-bold text-slate-800 mb-2">{{ t('groups.mine') }}</h2>
      <ul v-if="groups.length" class="divide-y">
        <li v-for="g in groups" :key="g.id">
          <button @click="openGroup(g.id)"
            :class="['w-full flex justify-between items-center py-2 px-2 text-sm text-left rounded hover:bg-slate-50',
              g.id === selectedId ? 'bg-slate-100' : '']">
            <span>
              <span class="font-medium text-slate-800">{{ g.name }}</span>
              <span class="text-slate-500"> · {{ t('groups.members', g.member_count) }}</span>
            </span>
            <span class="text-slate-500">#{{ g.my_rank }}</span>
          </button>
        </li>
      </ul>
      <p v-else class="text-slate-500 text-sm">{{ t('groups.none') }}</p>
    </section>

    <section v-if="selected" class="bg-surface rounded-xl shadow p-4 border-t-4 border-amber-500 space-y-3">
      <div class="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 class="text-lg font-bold text-slate-800 flex items-center gap-2">
            {{ selected.name }}
            <span :class="['text-xs font-normal flex items-center gap-1',
              live === 'live' ? 'text-ok' : 'text-slate-500']">
              <span :class="['inline-block w-2 h-2 rounded-full',
                live === 'live' ? 'bg-green-500' : live === 'connecting' ? 'bg-amber-400' : 'bg-slate-300']"></span>
              {{ live === 'live' ? t('groups.live') : live === 'connecting' ? t('groups.connecting') : t('groups.offline') }}
            </span>
          </h2>
          <p v-if="selected.description" class="text-sm text-slate-500">{{ selected.description }}</p>
        </div>
        <button @click="copyCode" :title="t('groups.copyCode')"
          class="border border-slate-400 rounded-lg px-3 py-1 text-sm font-mono tracking-widest text-slate-700 hover:bg-slate-50">
          {{ copied ? t('groups.copied') : selected.invite_code }}
        </button>
      </div>

      <div class="flex gap-2 text-sm">
        <button @click="setPeriod('all')"
          :class="['rounded-lg px-3 py-1', period === 'all' ? 'bg-primary text-on-primary' : 'border border-slate-400 text-slate-600']">
          {{ t('groups.periodAll') }}
        </button>
        <button @click="setPeriod('week')"
          :class="['rounded-lg px-3 py-1', period === 'week' ? 'bg-primary text-on-primary' : 'border border-slate-400 text-slate-600']">
          {{ t('groups.periodWeek') }}
        </button>
      </div>

      <ol class="divide-y">
        <li v-for="e in selected.leaderboard" :key="e.user_id"
          :class="['flex items-center justify-between py-2 px-2 text-sm', e.is_me ? 'bg-amber-50 rounded' : '']">
          <span class="flex items-center gap-3">
            <span class="w-8 text-center text-lg">{{ medals[e.rank - 1] ?? e.rank }}</span>
            <span :class="e.is_me ? 'font-bold text-slate-800' : 'text-slate-700'">
              {{ e.name }}<span v-if="e.is_me" class="text-slate-500 font-normal"> ({{ t('groups.you') }})</span>
            </span>
          </span>
          <span class="font-medium text-slate-800">{{ t('groups.points', { n: e.points }) }}</span>
        </li>
      </ol>

      <div class="flex justify-end gap-2 pt-2">
        <button @click="leaveGroup" class="text-sm border border-slate-400 text-slate-600 rounded-lg px-3 py-1 hover:bg-slate-50">
          {{ t('groups.leave') }}
        </button>
        <button v-if="selected.is_owner" @click="deleteGroup"
          class="text-sm border border-red-300 text-danger rounded-lg px-3 py-1 hover:bg-red-50">
          {{ t('groups.deleteGroup') }}
        </button>
      </div>
    </section>
  </div>
</template>
