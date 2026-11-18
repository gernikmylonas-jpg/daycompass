<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiErrorMessage } from '../i18n/errors'
import { useJournalLockStore } from '../stores/journalLock'

// PIN lock for the journal: unlock screen, and the controls to turn the lock on, change it or remove it.
const { t } = useI18n()
const lock = useJournalLockStore()

const pin = ref('')
const newPin = ref('')
const repeat = ref('')
const mode = ref<'enable' | 'change' | null>(null)
const error = ref('')
const message = ref('')

function reset() {
  pin.value = newPin.value = repeat.value = ''
  mode.value = null
}

async function run(action: () => Promise<void>) {
  error.value = ''
  message.value = ''
  try {
    await action()
    reset()
    message.value = t('lock.done')
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

const unlock = () => run(() => lock.unlock(pin.value))
function enable() {
  if (newPin.value !== repeat.value) {
    error.value = t('lock.mismatch')
    return
  }
  return run(() => lock.enable(newPin.value))
}
function change() {
  if (newPin.value !== repeat.value) {
    error.value = t('lock.mismatch')
    return
  }
  return run(() => lock.change(pin.value, newPin.value))
}
const remove = () => {
  if (!pin.value) {
    error.value = t('lock.needCurrent')
    return
  }
  return run(() => lock.disable(pin.value))
}
</script>

<template>
  <div class="space-y-3">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
    <p v-if="message" role="status" class="text-ok text-sm">{{ message }}</p>

    <!-- locked: nothing of the journal is shown until the PIN is entered -->
    <section v-if="lock.blocked" class="bg-surface rounded-xl shadow p-5 text-center space-y-3 border-t-4 border-purple-500">
      <p class="text-3xl" aria-hidden="true">🔒</p>
      <h3 class="font-bold text-slate-800">{{ t('lock.locked') }}</h3>
      <form @submit.prevent="unlock" class="flex gap-2 justify-center">
        <input v-model="pin" type="password" autocomplete="off" required :placeholder="t('lock.pin')" :aria-label="t('lock.pin')"
          class="border rounded-lg px-3 py-2 text-sm w-40 text-center" />
        <button type="submit" class="bg-primary text-on-primary rounded-lg px-4 py-2 text-sm hover:bg-primary-hover">{{ t('lock.unlock') }}</button>
      </form>
    </section>

    <!-- unlocked and lock on -->
    <section v-else-if="lock.enabled" class="bg-surface rounded-xl shadow px-4 py-3 space-y-2">
      <div class="flex flex-wrap items-center justify-between gap-2 text-sm">
        <span class="text-slate-700">🔒 {{ t('lock.on') }}</span>
        <div class="flex gap-2">
          <button @click="lock.lockNow()" class="border border-slate-400 text-slate-700 rounded-lg px-3 py-1 hover:bg-slate-50">{{ t('lock.lockNow') }}</button>
          <button @click="mode = mode === 'change' ? null : 'change'" class="border border-slate-400 text-slate-700 rounded-lg px-3 py-1 hover:bg-slate-50">{{ t('lock.change') }}</button>
        </div>
      </div>
      <form v-if="mode === 'change'" @submit.prevent="change" class="space-y-2">
        <input v-model="pin" type="password" autocomplete="off" required :placeholder="t('lock.pin')" :aria-label="t('lock.pin')" class="w-full border rounded-lg px-3 py-2 text-sm" />
        <input v-model="newPin" type="password" autocomplete="off" required minlength="4" :placeholder="t('lock.newPin')" :aria-label="t('lock.newPin')" class="w-full border rounded-lg px-3 py-2 text-sm" />
        <input v-model="repeat" type="password" autocomplete="off" required minlength="4" :placeholder="t('lock.repeat')" :aria-label="t('lock.repeat')" class="w-full border rounded-lg px-3 py-2 text-sm" />
        <div class="flex gap-2">
          <button type="submit" class="bg-primary text-on-primary rounded-lg px-4 py-1.5 text-sm hover:bg-primary-hover">{{ t('lock.change') }}</button>
          <button type="button" @click="remove" class="border border-slate-400 text-danger rounded-lg px-4 py-1.5 text-sm hover:bg-slate-50">{{ t('lock.remove') }}</button>
        </div>
        <p class="text-xs text-slate-500">{{ t('lock.removeHint') }}</p>
      </form>
    </section>

    <!-- lock off: offer it -->
    <section v-else-if="lock.enabled === false" class="bg-surface rounded-xl shadow px-4 py-3 space-y-2">
      <button v-if="mode !== 'enable'" @click="mode = 'enable'" class="text-sm text-slate-700 underline hover:text-slate-900">🔒 {{ t('lock.enableTitle') }}</button>
      <form v-else @submit.prevent="enable" class="space-y-2">
        <p class="text-sm font-medium text-slate-800">{{ t('lock.enableTitle') }}</p>
        <p class="text-xs text-slate-500">{{ t('lock.enableHint') }}</p>
        <input v-model="newPin" type="password" autocomplete="off" required minlength="4" :placeholder="t('lock.newPin')" :aria-label="t('lock.newPin')" class="w-full border rounded-lg px-3 py-2 text-sm" />
        <input v-model="repeat" type="password" autocomplete="off" required minlength="4" :placeholder="t('lock.repeat')" :aria-label="t('lock.repeat')" class="w-full border rounded-lg px-3 py-2 text-sm" />
        <div class="flex gap-2">
          <button type="submit" class="bg-primary text-on-primary rounded-lg px-4 py-1.5 text-sm hover:bg-primary-hover">{{ t('lock.enable') }}</button>
          <button type="button" @click="reset" class="border border-slate-400 text-slate-600 rounded-lg px-4 py-1.5 text-sm hover:bg-slate-50">{{ t('common.cancel') }}</button>
        </div>
      </form>
    </section>
  </div>
</template>
