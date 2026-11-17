<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '../i18n'
import { daysInMonth } from '../i18n/dates'

// Day / month / year date input. (The browser's own date input follows the operating system's
// order, which for many people is month first.) v-model is an ISO "YYYY-MM-DD" string, or ""
// while the date is incomplete, invalid or outside min/max.
const props = withDefaults(defineProps<{
  modelValue: string
  min?: string
  max?: string
  label: string
  required?: boolean
}>(), { min: '1900-01-01', max: '2100-12-31' })

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const { t, locale } = useI18n()

const minYear = computed(() => Number(props.min.slice(0, 4)))
const maxYear = computed(() => Number(props.max.slice(0, 4)))

const day = ref<number | null>(null)
const month = ref<number | null>(null)
const year = ref<number | null>(null)

function load(value: string) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!m) return
  year.value = Number(m[1])
  month.value = Number(m[2])
  day.value = Number(m[3])
}
load(props.modelValue)

const monthNames = computed(() => {
  const f = new Intl.DateTimeFormat(intlLocale(locale.value), { month: 'long' })
  return Array.from({ length: 12 }, (_, i) => {
    const name = f.format(new Date(2024, i, 1))
    return name.charAt(0).toUpperCase() + name.slice(1)
  })
})

function compose(): string {
  const d = day.value
  const m = month.value
  const y = year.value
  if (!d || !m || !y || y < 1000 || y > 9999) return ''
  if (m < 1 || m > 12 || d < 1 || d > daysInMonth(y, m)) return ''
  const iso = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
  return iso < props.min || iso > props.max ? '' : iso
}

watch([day, month, year], () => {
  const next = compose()
  if (next !== props.modelValue) emit('update:modelValue', next)
})

// follow changes made by the parent (e.g. opening the form for another day)
watch(() => props.modelValue, (value) => {
  if (value && value !== compose()) load(value)
})

const invalid = computed(() => !!(day.value && month.value && year.value && !compose()))
</script>

<template>
  <div role="group" :aria-label="label" class="flex items-center gap-1.5">
    <input v-model.number="day" type="number" inputmode="numeric" min="1" max="31" :required="required"
      :placeholder="t('date.dayHint')" :aria-label="`${label}: ${t('date.day')}`" :aria-invalid="invalid"
      class="border rounded-lg px-2 py-1.5 text-sm w-14 text-center" />
    <span class="text-slate-500" aria-hidden="true">/</span>
    <select v-model.number="month" :required="required" :aria-label="`${label}: ${t('date.month')}`" :aria-invalid="invalid"
      class="border rounded-lg px-1.5 py-1.5 text-sm min-w-0 flex-1">
      <option :value="null" disabled>{{ t('date.month') }}</option>
      <option v-for="(name, i) in monthNames" :key="i" :value="i + 1">{{ name }}</option>
    </select>
    <span class="text-slate-500" aria-hidden="true">/</span>
    <input v-model.number="year" type="number" inputmode="numeric" :min="minYear" :max="maxYear" :required="required"
      :placeholder="t('date.yearHint')" :aria-label="`${label}: ${t('date.year')}`" :aria-invalid="invalid"
      class="border rounded-lg px-2 py-1.5 text-sm w-20 text-center" />
  </div>
</template>
