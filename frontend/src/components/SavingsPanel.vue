<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { formatDate, toIso } from '../i18n/dates'
import { intlLocale } from '../i18n'
import { formatMoney, parseAmount } from '../money'
import DateField from './DateField.vue'

// Savings goals (an emergency fund, a laptop, a trip): put money in, take it out, and see when you will get there.
interface Goal {
  id: string; name: string; kind: 'general' | 'trip'; target_cents: number; saved_cents: number; percent: number; remaining_cents: number
  deadline: string | null; done: boolean; monthly_needed_cents: number | null; projected: string | null
  deposits: { id: string; date: string; amount_cents: number; note: string | null }[]
}
const { t, locale } = useI18n()
const loc = computed(() => intlLocale(locale.value))
const today = toIso(new Date())
const currency = ref('EUR')
const goals = ref<Goal[]>([])
const error = ref('')
const creating = ref(false)
const open = ref<string | null>(null)
const form = ref({ name: '', target: '', deadline: '' as string, kind: 'general' as 'general' | 'trip' })
const dep = ref({ amount: '', note: '' })
const editing = ref<{ id: string; name: string; target: string; deadline: string; kind: 'general' | 'trip' } | null>(null)
function startEdit(g: Goal) {
  editing.value = { id: g.id, name: g.name, target: String(g.target_cents / 100), deadline: g.deadline ?? '', kind: g.kind }
}
const saveEdit = () => run(async () => {
  const e = editing.value
  const target = e ? parseAmount(e.target) : null
  if (!e || target === null) return
  await api.put(`/api/money/savings/${e.id}`, { name: e.name, target, deadline: e.deadline || null, kind: e.kind })
  editing.value = null
})
const money = (c: number) => formatMoney(c, currency.value, loc.value)

async function load() {
  try {
    const { data } = await api.get<{ currency: string; goals: Goal[] }>('/api/money/savings')
    currency.value = data.currency
    goals.value = data.goals
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
async function run(fn: () => Promise<unknown>) {
  error.value = ''
  try {
    await fn()
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}
const addGoal = () => run(async () => {
  const target = parseAmount(form.value.target)
  if (target === null) return
  await api.post('/api/money/savings', { name: form.value.name, target, deadline: form.value.deadline || null, kind: form.value.kind })
  creating.value = false
  form.value = { name: '', target: '', deadline: '', kind: 'general' }
})
const deposit = (g: Goal, sign: 1 | -1) => run(async () => {
  const amount = parseAmount(dep.value.amount)
  if (amount === null || amount <= 0) return
  await api.post(`/api/money/savings/${g.id}/deposit`, { amount: sign * amount, note: dep.value.note || null })
  dep.value = { amount: '', note: '' }
})
const remove = (g: Goal) => { if (confirm(t('money.savings.confirmDelete'))) return run(() => api.delete(`/api/money/savings/${g.id}`)) }
const total = computed(() => goals.value.reduce((s, g) => s + g.saved_cents, 0))
onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
    <section class="bg-surface rounded-xl shadow p-4 space-y-3 border-t-4 border-amber-500">
      <div class="flex items-center justify-between gap-2">
        <div><h3 class="font-bold text-slate-800">🐷 {{ t('money.savings.title') }}</h3><p class="text-xs text-slate-500">{{ t('money.savings.total', { n: money(total) }) }}</p></div>
        <button type="button" @click="creating = !creating" :aria-expanded="creating" class="bg-primary text-on-primary rounded-lg px-3 py-1 text-sm hover:bg-primary-hover">+ {{ t('money.savings.new') }}</button>
      </div>
      <form v-if="creating" @submit.prevent="addGoal" class="rounded-lg border border-slate-200 p-3 space-y-2">
        <input v-model="form.name" maxlength="60" required :placeholder="t('money.savings.name')" :aria-label="t('money.savings.name')" class="w-full border rounded-lg px-3 py-1.5 text-sm" />
        <div class="flex flex-wrap gap-2 items-end">
          <input v-model="form.target" inputmode="decimal" required :placeholder="t('money.savings.target')" :aria-label="t('money.savings.target')" class="border rounded-lg px-3 py-1.5 text-sm w-32" />
          <select v-model="form.kind" :aria-label="t('money.savings.kind')" class="border rounded-lg px-2 py-1.5 text-sm"><option value="general">🐷 {{ t('money.savings.general') }}</option><option value="trip">✈️ {{ t('money.savings.trip') }}</option></select>
        </div>
        <div class="text-xs text-slate-600">
          <label class="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" class="h-4 w-4" :checked="!!form.deadline" @change="form.deadline = ($event.target as HTMLInputElement).checked ? today : ''" />{{ t('money.savings.hasDeadline') }}</label>
          <DateField v-if="form.deadline" v-model="form.deadline" :min="today" max="2100-12-31" :label="t('goals.deadline')" required class="mt-1" />
        </div>
        <div class="flex gap-2">
          <button type="submit" class="bg-primary text-on-primary rounded-lg px-4 py-1.5 text-sm hover:bg-primary-hover">{{ t('challenges.create') }}</button>
          <button type="button" @click="creating = false" class="border border-slate-400 text-slate-600 rounded-lg px-4 py-1.5 text-sm hover:bg-slate-50">{{ t('common.cancel') }}</button>
        </div>
      </form>
      <p v-if="!goals.length && !creating" class="text-sm text-slate-500">{{ t('money.savings.none') }}</p>
    </section>

    <section v-for="g in goals" :key="g.id" class="bg-surface rounded-xl shadow p-4 space-y-2">
      <div class="flex items-start justify-between gap-2">
        <div class="min-w-0"><p class="font-bold text-slate-800 break-words"><span aria-hidden="true">{{ g.kind === 'trip' ? '✈️' : '🐷' }}</span> {{ g.name }}</p>
          <p v-if="g.deadline" class="text-xs text-slate-500">{{ t('money.savings.by', { date: formatDate(g.deadline) }) }}</p></div>
        <div class="flex items-center gap-2 shrink-0"><span v-if="g.done" class="text-xs rounded-full border border-ok text-ok px-2 py-0.5">{{ t('money.savings.reached') }}</span>
          <button @click="remove(g)" :aria-label="t('home.remove')" :title="t('home.remove')" class="w-6 h-6 inline-flex items-center justify-center rounded text-slate-500 hover:text-danger hover:bg-slate-100">✕</button></div>
      </div>
      <div class="h-2.5 rounded bg-slate-100 overflow-hidden" role="progressbar" :aria-valuenow="g.percent" aria-valuemin="0" aria-valuemax="100" :aria-label="g.name"><div class="h-full" :class="g.done ? 'bg-ok' : 'bg-amber-500'" :style="{ width: g.percent + '%' }"></div></div>
      <p class="text-sm text-slate-700 tabular-nums">{{ money(g.saved_cents) }} / {{ money(g.target_cents) }} <span class="text-xs text-slate-500">· {{ g.percent }}%</span></p>
      <p v-if="!g.done" class="text-xs text-slate-500">
        <template v-if="g.monthly_needed_cents">{{ t('money.savings.monthlyNeeded', { n: money(g.monthly_needed_cents) }) }}</template>
        <template v-if="g.projected"><template v-if="g.monthly_needed_cents"> · </template>{{ t('money.savings.projected', { date: formatDate(g.projected) }) }}</template>
      </p>
      <div class="flex flex-wrap gap-4">
        <button type="button" @click="open = open === g.id ? null : g.id" :aria-expanded="open === g.id" class="text-sm underline text-slate-700">{{ open === g.id ? t('money.trips.hide') : t('money.savings.addMoney') }}</button>
        <button type="button" @click="editing?.id === g.id ? (editing = null) : startEdit(g)" :aria-expanded="editing?.id === g.id" class="text-sm underline text-slate-700">✎ {{ t('money.savings.edit') }}</button>
      </div>
      <form v-if="editing && editing.id === g.id" @submit.prevent="saveEdit" class="rounded-lg border border-slate-200 p-3 space-y-2">
        <input v-model="editing.name" maxlength="60" required :aria-label="t('money.savings.name')" class="w-full border rounded-lg px-3 py-1.5 text-sm" />
        <div class="flex flex-wrap gap-2 items-end">
          <label class="text-xs text-slate-600">{{ t('money.savings.target') }}<input v-model="editing.target" inputmode="decimal" required class="mt-1 border rounded-lg px-3 py-1.5 text-sm w-32 block" /></label>
          <select v-model="editing.kind" :aria-label="t('money.savings.kind')" class="border rounded-lg px-2 py-1.5 text-sm"><option value="general">🐷 {{ t('money.savings.general') }}</option><option value="trip">✈️ {{ t('money.savings.trip') }}</option></select>
        </div>
        <div class="text-xs text-slate-600">
          <label class="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" class="h-4 w-4" :checked="!!editing.deadline" @change="editing!.deadline = ($event.target as HTMLInputElement).checked ? today : ''" />{{ t('money.savings.hasDeadline') }}</label>
          <DateField v-if="editing.deadline" v-model="editing.deadline" min="1900-01-01" max="2100-12-31" :label="t('goals.deadline')" required class="mt-1" />
        </div>
        <div class="flex gap-2">
          <button type="submit" class="bg-primary text-on-primary rounded-lg px-4 py-1.5 text-sm hover:bg-primary-hover">{{ t('common.save') }}</button>
          <button type="button" @click="editing = null" class="border border-slate-400 text-slate-600 rounded-lg px-4 py-1.5 text-sm hover:bg-slate-50">{{ t('common.cancel') }}</button>
        </div>
      </form>
      <div v-if="open === g.id" class="space-y-2 border-t border-slate-200 pt-3">
        <form class="flex flex-wrap gap-2" @submit.prevent="deposit(g, 1)">
          <input v-model="dep.amount" inputmode="decimal" required :placeholder="t('money.amount')" :aria-label="t('money.amount')" class="border rounded-lg px-3 py-1.5 text-sm w-28" />
          <input v-model="dep.note" maxlength="120" :placeholder="t('workouts.note')" :aria-label="t('workouts.note')" class="flex-1 min-w-32 border rounded-lg px-3 py-1.5 text-sm" />
          <button type="submit" class="bg-primary text-on-primary rounded-lg px-3 text-sm hover:bg-primary-hover">+ {{ t('money.savings.put') }}</button>
          <button type="button" @click="deposit(g, -1)" class="border border-slate-400 text-slate-700 rounded-lg px-3 text-sm hover:bg-slate-50">− {{ t('money.savings.take') }}</button>
        </form>
        <ul v-if="g.deposits.length" class="divide-y text-sm">
          <li v-for="d in g.deposits.slice(0, 10)" :key="d.id" class="py-1 flex justify-between text-slate-700"><span>{{ formatDate(d.date) }}<span v-if="d.note" class="text-xs text-slate-500"> · {{ d.note }}</span></span><b class="tabular-nums" :class="d.amount_cents > 0 ? 'text-ok' : ''">{{ d.amount_cents > 0 ? '+' : '−' }}{{ money(Math.abs(d.amount_cents)) }}</b></li>
        </ul>
      </div>
    </section>
  </div>
</template>
