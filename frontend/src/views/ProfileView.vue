<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { useAuthStore } from '../stores/auth'
import { useBadgesStore } from '../stores/badges'
import { useStreakStore } from '../stores/streak'

// Your details: name, email, password (it is stored hashed, so it can only be changed, never shown).
const { t } = useI18n()
const auth = useAuthStore()
const badges = useBadgesStore()
const streak = useStreakStore()
const router = useRouter()

const name = ref(auth.user?.name ?? '')
const newEmail = ref('')
const emailPassword = ref('')
const currentPassword = ref('')
const newPassword = ref('')
const repeatPassword = ref('')

const message = ref('')
const error = ref('')
const section = ref<'name' | 'email' | 'password' | null>(null)

const earned = computed(() => badges.badges.filter((b) => b.earned).length)
const passwordsMatch = computed(() => newPassword.value === repeatPassword.value)

function reset(next: 'name' | 'email' | 'password') {
  message.value = ''
  error.value = ''
  section.value = next
}

async function saveName() {
  reset('name')
  try {
    const { data } = await api.put('/api/auth/profile', { name: name.value })
    auth.updateUser(data)
    message.value = t('profile.saved')
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function saveEmail() {
  reset('email')
  try {
    const { data } = await api.put('/api/auth/profile', { email: newEmail.value, current_password: emailPassword.value })
    auth.updateUser(data)
    newEmail.value = ''
    emailPassword.value = ''
    message.value = t('profile.saved')
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function savePassword() {
  reset('password')
  if (!passwordsMatch.value) {
    error.value = t('profile.passwordMismatch')
    return
  }
  try {
    await api.put('/api/auth/password', { current_password: currentPassword.value, new_password: newPassword.value })
    currentPassword.value = newPassword.value = repeatPassword.value = ''
    message.value = t('profile.passwordChanged')
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

// ── your data: download everything, or delete the account for good ──
const deletePassword = ref('')
const confirmDelete = ref(false)

async function exportData() {
  reset('password')
  try {
    const { data } = await api.get<Blob>('/api/account/export', { responseType: 'blob' })
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'daycompass-export.json'
    a.click()
    URL.revokeObjectURL(url)
    message.value = t('profile.exported')
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function deleteAccount() {
  reset('password')
  try {
    await api.delete('/api/account', { data: { password: deletePassword.value } })
    auth.logout()
    router.push('/login')
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(async () => {
  await Promise.all([auth.refreshUser().catch(() => {}), badges.fetchBadges().catch(() => {}), streak.fetch()])
  name.value = auth.user?.name ?? ''
})
</script>

<template>
  <div class="min-h-[calc(100vh-3rem)] bg-page p-4 md:p-8">
    <div class="max-w-2xl mx-auto space-y-4">
      <header class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-slate-800">{{ t('profile.title') }}</h1>
        <RouterLink to="/"
          class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover">
          {{ t('common.backToCompass') }}
        </RouterLink>
      </header>

      <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
      <p v-if="message" role="status" class="text-ok text-sm font-medium">{{ message }}</p>

      <!-- at a glance -->
      <section class="grid grid-cols-3 gap-3 text-center">
        <RouterLink to="/progress" class="bg-surface rounded-xl shadow p-3 hover:bg-slate-50">
          <p class="text-2xl font-bold text-slate-800 tabular-nums">{{ auth.user?.total_points ?? 0 }}</p>
          <p class="text-xs text-slate-500">{{ t('profile.points') }}</p>
        </RouterLink>
        <div class="bg-surface rounded-xl shadow p-3">
          <p class="text-2xl font-bold text-streak tabular-nums">🔥 {{ streak.current }}</p>
          <p class="text-xs text-slate-500">{{ t('streak.title') }} · {{ t('streak.best', { n: streak.best }) }}</p>
        </div>
        <RouterLink to="/progress" class="bg-surface rounded-xl shadow p-3 hover:bg-slate-50">
          <p class="text-2xl font-bold text-slate-800 tabular-nums">{{ earned }}/{{ badges.badges.length }}</p>
          <p class="text-xs text-slate-500">{{ t('profile.badges') }}</p>
        </RouterLink>
      </section>

      <section class="bg-surface rounded-xl shadow p-4 space-y-4">
        <h2 class="font-bold text-slate-800">{{ t('profile.details') }}</h2>

        <form @submit.prevent="saveName" class="space-y-2">
          <label class="block text-sm text-slate-600" for="profile-name">{{ t('auth.name') }}</label>
          <div class="flex gap-2">
            <input id="profile-name" v-model="name" type="text" maxlength="60" required class="flex-1 min-w-0 border rounded-lg px-3 py-2 text-sm" />
            <button type="submit" class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover">{{ t('common.save') }}</button>
          </div>
        </form>

        <div class="border-t border-slate-200 pt-3">
          <p class="text-sm text-slate-600">{{ t('auth.email') }}</p>
          <p class="text-sm font-medium text-slate-800 break-all">{{ auth.user?.email }}</p>
          <form @submit.prevent="saveEmail" class="mt-2 space-y-2">
            <input v-model="newEmail" type="email" required :placeholder="t('profile.newEmail')" :aria-label="t('profile.newEmail')"
              autocomplete="email" class="w-full border rounded-lg px-3 py-2 text-sm" />
            <input v-model="emailPassword" type="password" required :placeholder="t('profile.currentPassword')" :aria-label="t('profile.currentPassword')"
              autocomplete="current-password" class="w-full border rounded-lg px-3 py-2 text-sm" />
            <button type="submit" class="border border-slate-400 text-slate-700 rounded-lg px-4 py-2 text-sm hover:bg-slate-50">{{ t('profile.changeEmail') }}</button>
          </form>
        </div>

        <div class="border-t border-slate-200 pt-3">
          <p class="text-sm text-slate-600">{{ t('auth.password') }}</p>
          <p class="text-sm font-medium text-slate-800 tracking-widest" aria-hidden="true">••••••••</p>
          <p class="text-xs text-slate-500">{{ t('profile.passwordHidden') }}</p>
          <form @submit.prevent="savePassword" class="mt-2 space-y-2">
            <input v-model="currentPassword" type="password" required :placeholder="t('profile.currentPassword')" :aria-label="t('profile.currentPassword')"
              autocomplete="current-password" class="w-full border rounded-lg px-3 py-2 text-sm" />
            <input v-model="newPassword" type="password" required minlength="8" :placeholder="t('profile.newPassword')" :aria-label="t('profile.newPassword')"
              autocomplete="new-password" class="w-full border rounded-lg px-3 py-2 text-sm" />
            <input v-model="repeatPassword" type="password" required minlength="8" :placeholder="t('profile.repeatPassword')" :aria-label="t('profile.repeatPassword')"
              autocomplete="new-password" class="w-full border rounded-lg px-3 py-2 text-sm" />
            <p v-if="section === 'password' && error" class="sr-only">{{ error }}</p>
            <button type="submit" class="border border-slate-400 text-slate-700 rounded-lg px-4 py-2 text-sm hover:bg-slate-50">{{ t('profile.changePassword') }}</button>
          </form>
        </div>
      </section>

      <section class="bg-surface rounded-xl shadow p-4 space-y-3">
        <h2 class="font-bold text-slate-800">{{ t('profile.yourData') }}</h2>
        <p class="text-sm text-slate-600">{{ t('profile.exportHint') }}</p>
        <button @click="exportData" class="border border-slate-400 text-slate-700 rounded-lg px-4 py-2 text-sm hover:bg-slate-50">⬇ {{ t('profile.export') }}</button>
        <div class="border-t border-slate-200 pt-3 space-y-2">
          <button v-if="!confirmDelete" @click="confirmDelete = true" class="text-sm text-danger underline">{{ t('profile.deleteAccount') }}</button>
          <form v-else @submit.prevent="deleteAccount" class="space-y-2">
            <p class="text-sm text-danger font-medium">{{ t('profile.deleteWarning') }}</p>
            <input v-model="deletePassword" type="password" required autocomplete="current-password" :placeholder="t('profile.currentPassword')" :aria-label="t('profile.currentPassword')"
              class="w-full border rounded-lg px-3 py-2 text-sm" />
            <div class="flex gap-2">
              <button type="submit" class="border-2 border-danger text-danger font-medium rounded-lg px-4 py-2 text-sm hover:bg-slate-50">{{ t('profile.deleteConfirm') }}</button>
              <button type="button" @click="confirmDelete = false; deletePassword = ''" class="border border-slate-400 text-slate-600 rounded-lg px-4 py-2 text-sm hover:bg-slate-50">{{ t('common.cancel') }}</button>
            </div>
          </form>
        </div>
      </section>

      <button @click="logout" class="w-full border border-slate-400 text-slate-700 rounded-lg px-4 py-2 text-sm hover:bg-slate-50">
        {{ t('nav.logout') }}
      </button>
    </div>
  </div>
</template>
