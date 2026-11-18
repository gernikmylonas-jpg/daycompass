<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { apiErrorMessage } from '../i18n/errors'
import { formatDate, toIso } from '../i18n/dates'
import { useBadgesStore, type BadgeInfo } from '../stores/badges'
import DateField from './DateField.vue'
import JournalLock from './JournalLock.vue'
import { useJournalLockStore } from '../stores/journalLock'

// A private journal: write, and/or record your voice. Recordings are made with the browser's
// MediaRecorder, stored on the server and only ever served back to their owner.

interface Entry {
  id: string
  entry_date: string
  content: string
  mood: 'good' | 'neutral' | 'bad' | null
  created_at: string
  has_audio: boolean
  audio_seconds: number
  audio_mime: string | null
}

type Mood = 'good' | 'neutral' | 'bad'
const MOODS: { id: Mood; icon: string }[] = [
  { id: 'good', icon: '😊' },
  { id: 'neutral', icon: '😐' },
  { id: 'bad', icon: '😟' },
]
const MAX_RECORD_SECONDS = 10 * 60
const PAGE = 10

const { t } = useI18n()
const badgesStore = useBadgesStore()
const lock = useJournalLockStore()
const today = toIso(new Date())

const entries = ref<Entry[]>([])
const total = ref(0)
const error = ref('')
const message = ref('')
const busy = ref(false)

// new entry
const date = ref(today)
const content = ref('')
const mood = ref<Mood | null>(null)

// editing an existing entry
const editing = ref<{ id: string; date: string; content: string; mood: Mood | null } | null>(null)

const mmss = (seconds: number) => `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, '0')}`

// ── voice recording ──────────────────────────────────────────────────────
const supported = typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined'
const rec = ref<'idle' | 'recording' | 'ready'>('idle')
const elapsed = ref(0)
const recUrl = ref<string | null>(null)
let recBlob: Blob | null = null
let recSeconds = 0
let stream: MediaStream | null = null
let recorder: MediaRecorder | null = null
let chunks: Blob[] = []
let timer: number | undefined
let startedAt = 0

function pickMime(): string | undefined {
  return ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'].find((m) => MediaRecorder.isTypeSupported(m))
}

function releaseMic() {
  window.clearInterval(timer)
  stream?.getTracks().forEach((tr) => tr.stop())
  stream = null
}

function discardRecording() {
  if (recorder && recorder.state === 'recording') {
    recorder.onstop = null
    recorder.stop()
  }
  releaseMic()
  if (recUrl.value) URL.revokeObjectURL(recUrl.value)
  recUrl.value = null
  recBlob = null
  recSeconds = 0
  elapsed.value = 0
  rec.value = 'idle'
}

async function startRecording() {
  error.value = ''
  discardRecording()
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch {
    error.value = t('journal.micDenied')
    return
  }
  const mimeType = pickMime()
  recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
  chunks = []
  recorder.ondataavailable = (e) => {
    if (e.data.size) chunks.push(e.data)
  }
  recorder.onstop = () => {
    recBlob = new Blob(chunks, { type: recorder?.mimeType || 'audio/webm' })
    recSeconds = elapsed.value
    recUrl.value = URL.createObjectURL(recBlob)
    rec.value = 'ready'
    releaseMic()
  }
  recorder.start()
  startedAt = Date.now()
  elapsed.value = 0
  rec.value = 'recording'
  timer = window.setInterval(() => {
    elapsed.value = Math.round((Date.now() - startedAt) / 1000)
    if (elapsed.value >= MAX_RECORD_SECONDS) stopRecording()
  }, 250)
}

function stopRecording() {
  window.clearInterval(timer)
  if (recorder && recorder.state === 'recording') recorder.stop()
}

// ── saving and listing ───────────────────────────────────────────────────
const canSave = computed(() => !!date.value && (!!content.value.trim() || !!recBlob) && rec.value !== 'recording')

async function load(reset: boolean) {
  try {
    const { data } = await api.get<{ entries: Entry[]; total: number }>('/api/journal', {
      params: { limit: PAGE, offset: reset ? 0 : entries.value.length },
    })
    entries.value = reset ? data.entries : [...entries.value, ...data.entries]
    total.value = data.total
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function save() {
  if (!canSave.value) return
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const form = new FormData()
    form.append('entry_date', date.value)
    form.append('content', content.value)
    if (mood.value) form.append('mood', mood.value)
    if (recBlob) {
      const ext = recBlob.type.includes('ogg') ? 'ogg' : recBlob.type.includes('mp4') ? 'm4a' : 'webm'
      form.append('audio_seconds', String(recSeconds))
      form.append('audio', new File([recBlob], `journal.${ext}`, { type: recBlob.type }))
    }
    const { data } = await api.post<{ new_badges?: BadgeInfo[] }>('/api/journal', form)
    await badgesStore.announce(data.new_badges)
    content.value = ''
    mood.value = null
    discardRecording()
    message.value = t('journal.saved')
    await load(true)
  } catch (e) {
    error.value = apiErrorMessage(e)
  } finally {
    busy.value = false
  }
}

function startEdit(entry: Entry) {
  editing.value = { id: entry.id, date: entry.entry_date, content: entry.content, mood: entry.mood }
}

async function saveEdit() {
  const e = editing.value
  if (!e || !e.date) return
  error.value = ''
  try {
    await api.put(`/api/journal/${e.id}`, { entry_date: e.date, content: e.content, mood: e.mood })
    editing.value = null
    await load(true)
  } catch (err) {
    error.value = apiErrorMessage(err)
  }
}

async function remove(entry: Entry) {
  if (!confirm(t('journal.confirmDelete'))) return
  error.value = ''
  try {
    await api.delete(`/api/journal/${entry.id}`)
    entries.value = entries.value.filter((x) => x.id !== entry.id)
    total.value -= 1
    revoke(entry.id)
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

// ── playing saved recordings (fetched with the login token, then played from memory) ──
const audioUrls = ref<Record<string, string>>({})

async function play(entry: Entry) {
  try {
    const { data } = await api.get<Blob>(`/api/journal/${entry.id}/audio`, { responseType: 'blob' })
    audioUrls.value = { ...audioUrls.value, [entry.id]: URL.createObjectURL(data) }
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

function revoke(id: string) {
  const url = audioUrls.value[id]
  if (url) URL.revokeObjectURL(url)
  const { [id]: _removed, ...rest } = audioUrls.value
  audioUrls.value = rest
}

onMounted(async () => {
  try {
    await lock.refresh()
  } catch (e) {
    error.value = apiErrorMessage(e)
    return
  }
  if (!lock.blocked) load(true)
})
// unlocking loads the entries; locking again wipes everything decrypted from memory
watch(() => lock.blocked, (blocked) => {
  if (blocked) {
    entries.value = []
    total.value = 0
    Object.keys(audioUrls.value).forEach(revoke)
  } else {
    load(true)
  }
})
onBeforeUnmount(() => {
  discardRecording()
  Object.values(audioUrls.value).forEach((u) => URL.revokeObjectURL(u))
})
</script>

<template>
  <div class="space-y-4">
    <p v-if="error" role="alert" class="text-danger text-sm">{{ error }}</p>
    <p v-if="message" role="status" class="text-ok text-sm font-medium">{{ message }}</p>

    <JournalLock />

    <template v-if="!lock.blocked">
    <section class="bg-surface rounded-xl shadow p-4 space-y-3 border-t-4 border-purple-500">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h3 class="font-bold text-slate-800">{{ t('journal.newEntry') }}</h3>
        <DateField v-model="date" min="2000-01-01" :max="today" :label="t('wellness.date')" required />
      </div>

      <div role="radiogroup" :aria-label="t('journal.mood')" class="flex items-center gap-2">
        <span class="text-xs text-slate-500">{{ t('journal.mood') }}</span>
        <button v-for="m in MOODS" :key="m.id" type="button" role="radio" :aria-checked="mood === m.id"
          :aria-label="t(`journal.moods.${m.id}`)" :title="t(`journal.moods.${m.id}`)"
          @click="mood = mood === m.id ? null : m.id"
          :class="['w-9 h-9 rounded-full border text-lg flex items-center justify-center',
            mood === m.id ? 'border-slate-800 bg-slate-100' : 'border-slate-300 hover:bg-slate-50']">{{ m.icon }}</button>
      </div>

      <textarea v-model="content" rows="5" maxlength="10000"
        :placeholder="t('journal.placeholder')" :aria-label="t('journal.placeholder')"
        class="w-full border rounded-lg px-3 py-2 text-sm"></textarea>

      <!-- voice recorder -->
      <div v-if="supported" class="rounded-lg border border-slate-200 p-3 space-y-2">
        <div class="flex flex-wrap items-center gap-2">
          <button v-if="rec !== 'recording'" type="button" @click="startRecording"
            class="inline-flex items-center gap-2 border border-slate-400 text-slate-700 rounded-lg px-3 py-1.5 text-sm hover:bg-slate-50">
            <span aria-hidden="true">🎙</span> {{ rec === 'ready' ? t('journal.recordAgain') : t('journal.record') }}
          </button>
          <button v-else type="button" @click="stopRecording"
            class="inline-flex items-center gap-2 bg-danger text-surface rounded-lg px-3 py-1.5 text-sm">
            <span aria-hidden="true">■</span> {{ t('journal.stop') }}
          </button>
          <span v-if="rec === 'recording'" role="status" class="text-sm text-danger tabular-nums">
            <span class="inline-block w-2 h-2 rounded-full bg-danger animate-pulse mr-1" aria-hidden="true"></span>{{ t('journal.recording', { time: mmss(elapsed) }) }}
          </span>
          <button v-if="rec === 'ready'" type="button" @click="discardRecording"
            class="text-sm text-slate-600 underline hover:text-slate-900">{{ t('journal.discard') }}</button>
        </div>
        <audio v-if="rec === 'ready' && recUrl" :src="recUrl" controls class="w-full" :aria-label="t('journal.preview')"></audio>
      </div>
      <p v-else class="text-xs text-slate-500">{{ t('journal.micUnsupported') }}</p>

      <div class="flex items-center justify-between gap-2">
        <p class="text-xs text-slate-500">{{ t('journal.private') }}</p>
        <button @click="save" :disabled="!canSave || busy"
          class="bg-primary text-on-primary rounded-lg px-4 py-1.5 text-sm hover:bg-primary-hover disabled:opacity-50">
          {{ t('journal.save') }}
        </button>
      </div>
    </section>

    <section class="bg-surface rounded-xl shadow p-4">
      <h3 class="font-bold text-slate-800 mb-2">{{ t('journal.entries') }}</h3>
      <ul v-if="entries.length" class="divide-y">
        <li v-for="entry in entries" :key="entry.id" class="py-3 text-sm">
          <form v-if="editing && editing.id === entry.id" @submit.prevent="saveEdit" class="space-y-2">
            <DateField v-model="editing.date" min="2000-01-01" :max="today" :label="t('wellness.date')" required />
            <div role="radiogroup" :aria-label="t('journal.mood')" class="flex items-center gap-2">
              <button v-for="m in MOODS" :key="m.id" type="button" role="radio" :aria-checked="editing.mood === m.id"
                :aria-label="t(`journal.moods.${m.id}`)" @click="editing.mood = editing.mood === m.id ? null : m.id"
                :class="['w-8 h-8 rounded-full border flex items-center justify-center', editing.mood === m.id ? 'border-slate-800 bg-slate-100' : 'border-slate-300']">{{ m.icon }}</button>
            </div>
            <textarea v-model="editing.content" rows="4" maxlength="10000" :aria-label="t('journal.placeholder')"
              class="w-full border rounded-lg px-3 py-2 text-sm"></textarea>
            <div class="flex gap-2">
              <button type="submit" class="bg-primary text-on-primary rounded-lg px-3 py-1 text-sm hover:bg-primary-hover">{{ t('common.save') }}</button>
              <button type="button" @click="editing = null" class="border border-slate-400 text-slate-600 rounded-lg px-3 py-1 text-sm hover:bg-slate-50">{{ t('common.cancel') }}</button>
            </div>
          </form>

          <template v-else>
            <div class="flex items-center justify-between gap-2">
              <p class="font-semibold text-slate-800">
                {{ formatDate(entry.entry_date) }}
                <span v-if="entry.mood" class="ml-1" :title="t(`journal.moods.${entry.mood}`)">{{ MOODS.find((m) => m.id === entry.mood)?.icon }}</span>
              </p>
              <div class="flex items-center">
                <button @click="startEdit(entry)" :aria-label="t('home.edit')" :title="t('home.edit')"
                  class="w-7 h-7 inline-flex items-center justify-center rounded text-slate-500 hover:text-slate-900 hover:bg-slate-100">✎</button>
                <button @click="remove(entry)" :aria-label="t('home.remove')" :title="t('home.remove')"
                  class="w-7 h-7 inline-flex items-center justify-center rounded text-slate-500 hover:text-danger hover:bg-slate-100">✕</button>
              </div>
            </div>
            <p v-if="entry.content" class="text-slate-700 whitespace-pre-line break-words mt-1">{{ entry.content }}</p>
            <div v-if="entry.has_audio" class="mt-2">
              <audio v-if="audioUrls[entry.id]" :src="audioUrls[entry.id]" controls autoplay class="w-full" :aria-label="t('journal.recordingOf', { date: formatDate(entry.entry_date) })"></audio>
              <button v-else @click="play(entry)"
                class="inline-flex items-center gap-2 border border-slate-400 text-slate-700 rounded-lg px-3 py-1 text-xs hover:bg-slate-50">
                <span aria-hidden="true">▶</span> {{ t('journal.play', { time: mmss(entry.audio_seconds) }) }}
              </button>
            </div>
          </template>
        </li>
      </ul>
      <p v-else class="text-slate-500 text-sm">{{ t('journal.empty') }}</p>

      <button v-if="entries.length < total" @click="load(false)"
        class="mt-3 w-full border border-slate-400 text-slate-600 rounded-lg px-3 py-1.5 text-sm hover:bg-slate-50">
        {{ t('journal.loadMore') }}
      </button>
    </section>
    </template>
  </div>
</template>
