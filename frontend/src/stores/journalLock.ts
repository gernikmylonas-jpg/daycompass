import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api from '../api'
import { setJournalPin } from '../journalPin'

// State of the journal lock. `enabled` is stored on the server (entries are encrypted with the
// PIN there); `unlocked` only means this tab currently holds the right PIN in memory.
export const useJournalLockStore = defineStore('journalLock', () => {
  const enabled = ref<boolean | null>(null) // null = not known yet
  const unlocked = ref(false)

  const blocked = computed(() => enabled.value === true && !unlocked.value)

  async function refresh() {
    const { data } = await api.get<{ enabled: boolean }>('/api/journal/lock')
    enabled.value = data.enabled
    if (!data.enabled) {
      unlocked.value = true
      setJournalPin('')
    }
  }

  async function unlock(pin: string) {
    setJournalPin(pin)
    try {
      await api.get('/api/journal', { params: { limit: 1 } }) // the server checks the PIN
      unlocked.value = true
    } catch (e) {
      setJournalPin('')
      unlocked.value = false
      throw e
    }
  }

  function lockNow() {
    setJournalPin('')
    unlocked.value = false
  }

  async function enable(pin: string) {
    await api.post('/api/journal/lock', { pin })
    setJournalPin(pin)
    enabled.value = true
    unlocked.value = true
  }

  async function change(pin: string, newPin: string) {
    await api.put('/api/journal/lock', { pin, new_pin: newPin })
    setJournalPin(newPin)
  }

  async function disable(pin: string) {
    await api.post('/api/journal/lock/disable', { pin })
    setJournalPin('')
    enabled.value = false
    unlocked.value = true
  }

  return { enabled, unlocked, blocked, refresh, unlock, lockNow, enable, change, disable }
})
