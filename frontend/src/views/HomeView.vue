<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-slate-100 p-8">
    <div class="max-w-2xl mx-auto bg-white rounded-xl shadow p-6 space-y-3">
      <h1 class="text-2xl font-bold text-slate-800">Γεια σου, {{ auth.user?.name }}!</h1>
      <p class="text-slate-600">Πόντοι: {{ auth.user?.total_points }}</p>
      <button @click="logout" class="bg-slate-800 text-white rounded-lg px-4 py-2 hover:bg-slate-700">
        Αποσύνδεση
      </button>
    </div>
  </div>
</template>