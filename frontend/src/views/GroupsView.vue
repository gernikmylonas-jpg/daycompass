<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import axios from 'axios'
import api from '../api'

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

const groups = ref<GroupSummary[]>([])
const selected = ref<GroupDetail | null>(null)
const period = ref<'all' | 'week'>('all')
const newName = ref('')
const newDescription = ref('')
const joinCode = ref('')
const error = ref('')
const copied = ref(false)

const medals = ['🥇', '🥈', '🥉']
const selectedId = computed(() => selected.value?.id ?? null)

function showError(e: unknown) {
  error.value = axios.isAxiosError(e)
    ? (e.response?.data?.detail ?? 'Κάτι πήγε στραβά')
    : 'Κάτι πήγε στραβά'
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
    selected.value = data
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
    const { data } = await api.post<GroupSummary>('/api/groups', {
      name: newName.value,
      description: newDescription.value || null,
    })
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
    const { data } = await api.post<GroupSummary>('/api/groups/join', { invite_code: joinCode.value })
    joinCode.value = ''
    await loadGroups()
    await openGroup(data.id)
  } catch (e) {
    showError(e)
  }
}

async function leaveGroup() {
  if (!selected.value || !confirm('Να αποχωρήσεις από το group;')) return
  try {
    await api.delete(`/api/groups/${selected.value.id}/members/me`)
    selected.value = null
    await loadGroups()
  } catch (e) {
    showError(e)
  }
}

async function deleteGroup() {
  if (!selected.value || !confirm('Διαγραφή του group για όλα τα μέλη;')) return
  try {
    await api.delete(`/api/groups/${selected.value.id}`)
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
</script>

<template>
  <div class="min-h-screen bg-slate-100 p-4 md:p-8">
    <div class="max-w-3xl mx-auto space-y-4">
      <header class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-slate-800">Groups</h1>
        <RouterLink to="/"
          class="bg-slate-800 text-white rounded-lg px-4 py-2 text-sm hover:bg-slate-700">
          ← Πυξίδα
        </RouterLink>
      </header>

      <p v-if="error" class="text-red-600 text-sm">{{ error }}</p>

      <section class="grid md:grid-cols-2 gap-4">
        <form @submit.prevent="createGroup" class="bg-white rounded-xl shadow p-4 space-y-2">
          <h2 class="font-bold text-slate-800">Νέο group</h2>
          <input v-model="newName" maxlength="60" placeholder="Όνομα"
            class="border rounded-lg px-3 py-2 text-sm w-full" />
          <input v-model="newDescription" maxlength="200" placeholder="Περιγραφή (προαιρετικό)"
            class="border rounded-lg px-3 py-2 text-sm w-full" />
          <button class="bg-slate-800 text-white rounded-lg px-4 py-2 text-sm hover:bg-slate-700">Δημιουργία</button>
        </form>

        <form @submit.prevent="joinGroup" class="bg-white rounded-xl shadow p-4 space-y-2">
          <h2 class="font-bold text-slate-800">Συμμετοχή με κωδικό</h2>
          <input v-model="joinCode" maxlength="8" placeholder="π.χ. AB12CD34"
            class="border rounded-lg px-3 py-2 text-sm w-full uppercase tracking-widest" />
          <button class="bg-slate-800 text-white rounded-lg px-4 py-2 text-sm hover:bg-slate-700">Συμμετοχή</button>
        </form>
      </section>

      <section class="bg-white rounded-xl shadow p-4">
        <h2 class="font-bold text-slate-800 mb-2">Τα groups μου</h2>
        <ul v-if="groups.length" class="divide-y">
          <li v-for="g in groups" :key="g.id">
            <button @click="openGroup(g.id)"
              :class="['w-full flex justify-between items-center py-2 px-2 text-sm text-left rounded hover:bg-slate-50',
                g.id === selectedId ? 'bg-slate-100' : '']">
              <span>
                <span class="font-medium text-slate-800">{{ g.name }}</span>
                <span class="text-slate-400"> · {{ g.member_count }} μέλη</span>
              </span>
              <span class="text-slate-500">#{{ g.my_rank }}</span>
            </button>
          </li>
        </ul>
        <p v-else class="text-slate-400 text-sm">Δεν ανήκεις σε κανένα group ακόμα.</p>
      </section>

      <section v-if="selected" class="bg-white rounded-xl shadow p-4 border-t-4 border-amber-500 space-y-3">
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2 class="text-lg font-bold text-slate-800">{{ selected.name }}</h2>
            <p v-if="selected.description" class="text-sm text-slate-500">{{ selected.description }}</p>
          </div>
          <button @click="copyCode" title="Αντιγραφή κωδικού πρόσκλησης"
            class="border border-slate-300 rounded-lg px-3 py-1 text-sm font-mono tracking-widest text-slate-700 hover:bg-slate-50">
            {{ copied ? 'Αντιγράφηκε ✓' : selected.invite_code }}
          </button>
        </div>

        <div class="flex gap-2 text-sm">
          <button @click="setPeriod('all')"
            :class="['rounded-lg px-3 py-1', period === 'all' ? 'bg-slate-800 text-white' : 'border border-slate-300 text-slate-600']">
            Συνολικά
          </button>
          <button @click="setPeriod('week')"
            :class="['rounded-lg px-3 py-1', period === 'week' ? 'bg-slate-800 text-white' : 'border border-slate-300 text-slate-600']">
            Τελευταίες 7 μέρες
          </button>
        </div>

        <ol class="divide-y">
          <li v-for="e in selected.leaderboard" :key="e.user_id"
            :class="['flex items-center justify-between py-2 px-2 text-sm', e.is_me ? 'bg-amber-50 rounded' : '']">
            <span class="flex items-center gap-3">
              <span class="w-8 text-center text-lg">{{ medals[e.rank - 1] ?? e.rank }}</span>
              <span :class="e.is_me ? 'font-bold text-slate-800' : 'text-slate-700'">
                {{ e.name }}<span v-if="e.is_me" class="text-slate-400 font-normal"> (εσύ)</span>
              </span>
            </span>
            <span class="font-medium text-slate-800">{{ e.points }} πόντοι</span>
          </li>
        </ol>

        <div class="flex justify-end gap-2 pt-2">
          <button @click="leaveGroup" class="text-sm border border-slate-300 text-slate-600 rounded-lg px-3 py-1 hover:bg-slate-50">
            Αποχώρηση
          </button>
          <button v-if="selected.is_owner" @click="deleteGroup"
            class="text-sm border border-red-300 text-red-600 rounded-lg px-3 py-1 hover:bg-red-50">
            Διαγραφή group
          </button>
        </div>
      </section>
    </div>
  </div>
</template>
