<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { apiErrorMessage } from '../i18n/errors'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()

const name = ref('')
const email = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.register(name.value, email.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-3rem)] flex items-center justify-center bg-page">
    <form @submit.prevent="submit" class="bg-surface p-8 rounded-xl shadow w-full max-w-sm space-y-4">
      <h1 class="text-2xl font-bold text-slate-800">DayCompass</h1>
      <p class="text-slate-500 text-sm">{{ t('auth.registerSubtitle') }}</p>

      <input v-model="name" type="text" :placeholder="t('auth.name')" :aria-label="t('auth.name')" required
        class="w-full border rounded-lg px-3 py-2" />
      <input v-model="email" type="email" :placeholder="t('auth.email')" :aria-label="t('auth.email')" required
        class="w-full border rounded-lg px-3 py-2" />
      <input v-model="password" type="password" minlength="8" autocomplete="new-password" :placeholder="t('auth.password')" :aria-label="t('auth.password')" required
        class="w-full border rounded-lg px-3 py-2" />
      <p class="text-xs text-slate-500 -mt-2">{{ t('auth.passwordHint') }}</p>

      <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>

      <button type="submit"
        class="w-full bg-primary text-on-primary rounded-lg py-2 hover:bg-primary-hover">
        {{ t('auth.register') }}
      </button>

      <p class="text-sm text-slate-500">
        {{ t('auth.haveAccount') }}
        <RouterLink to="/login" class="text-slate-800 underline">{{ t('auth.login') }}</RouterLink>
      </p>
    </form>
  </div>
</template>
