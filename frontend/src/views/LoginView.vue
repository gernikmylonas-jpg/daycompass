<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const email = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = axios.isAxiosError(e)
      ? (e.response?.data?.detail ?? 'Κάτι πήγε στραβά')
      : 'Κάτι πήγε στραβά'
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-100">
    <form @submit.prevent="submit" class="bg-white p-8 rounded-xl shadow w-full max-w-sm space-y-4">
      <h1 class="text-2xl font-bold text-slate-800">DayCompass</h1>
      <p class="text-slate-500 text-sm">Σύνδεση στον λογαριασμό σου</p>

      <input v-model="email" type="email" placeholder="Email" required
        class="w-full border rounded-lg px-3 py-2" />
      <input v-model="password" type="password" placeholder="Κωδικός" required
        class="w-full border rounded-lg px-3 py-2" />

      <p v-if="error" class="text-red-600 text-sm">{{ error }}</p>

      <button type="submit"
        class="w-full bg-slate-800 text-white rounded-lg py-2 hover:bg-slate-700">
        Σύνδεση
      </button>

      <p class="text-sm text-slate-500">
        Δεν έχεις λογαριασμό;
        <RouterLink to="/register" class="text-slate-800 underline">Εγγραφή</RouterLink>
      </p>
    </form>
  </div>
</template>
