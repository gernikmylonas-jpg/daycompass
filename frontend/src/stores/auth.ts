import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export interface User {
  id: string
  name: string
  email: string
  total_points: number
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(JSON.parse(localStorage.getItem('user') || 'null'))
  const isLoggedIn = computed(() => !!token.value)

  function setSession(newToken: string, newUser: User) {
    token.value = newToken
    user.value = newUser
    localStorage.setItem('token', newToken)
    localStorage.setItem('user', JSON.stringify(newUser))
  }

  async function login(email: string, password: string) {
    const { data } = await api.post('/api/auth/login', { email, password })
    setSession(data.token, data.user)
  }

  async function register(name: string, email: string, password: string) {
    const { data } = await api.post('/api/auth/register', { name, email, password })
    setSession(data.token, data.user)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { token, user, isLoggedIn, login, register, logout }
})