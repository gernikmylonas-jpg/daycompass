<script setup lang="ts">
import { ref, onBeforeUnmount, watch } from 'vue'
import { useI18n } from 'vue-i18n'

// Background sounds for focusing, generated in the browser (no audio files). Silent until you press one;
// it stops when you leave the page.
type Kind = 'white' | 'pink' | 'brown' | 'rain'
const KINDS: Kind[] = ['white', 'pink', 'brown', 'rain']
const { t } = useI18n()
const playing = ref<Kind | null>(null)
const volume = ref(0.3)

let ctx: AudioContext | null = null
let gain: GainNode | null = null
let source: AudioBufferSourceNode | null = null

function noiseBuffer(c: AudioContext, kind: Kind): AudioBuffer {
  const length = c.sampleRate * 4
  const buffer = c.createBuffer(1, length, c.sampleRate)
  const data = buffer.getChannelData(0)
  let b0 = 0, b1 = 0, b2 = 0, last = 0
  for (let i = 0; i < length; i++) {
    const white = Math.random() * 2 - 1
    if (kind === 'pink') { // Paul Kellet's filter
      b0 = 0.99765 * b0 + white * 0.099046
      b1 = 0.963 * b1 + white * 0.2965164
      b2 = 0.57 * b2 + white * 1.0526913
      data[i] = (b0 + b1 + b2 + white * 0.1848) * 0.11
    } else if (kind === 'brown') {
      last = (last + 0.02 * white) / 1.02
      data[i] = last * 3.5
    } else {
      data[i] = white * 0.6
    }
  }
  return buffer
}

function stop() {
  source?.stop()
  source?.disconnect()
  source = null
  playing.value = null
}

async function play(kind: Kind) {
  if (playing.value === kind) return stop()
  stop()
  ctx ??= new AudioContext()
  await ctx.resume()
  gain ??= ctx.createGain()
  gain.gain.value = volume.value
  gain.connect(ctx.destination)
  source = ctx.createBufferSource()
  source.buffer = noiseBuffer(ctx, kind === 'rain' ? 'white' : kind)
  source.loop = true
  if (kind === 'rain') { // white noise, softened and thinned to sound like steady rain
    const high = ctx.createBiquadFilter(); high.type = 'highpass'; high.frequency.value = 900
    const low = ctx.createBiquadFilter(); low.type = 'lowpass'; low.frequency.value = 7000
    source.connect(high); high.connect(low); low.connect(gain)
  } else {
    source.connect(gain)
  }
  source.start()
  playing.value = kind
}

watch(volume, (v) => { if (gain) gain.gain.value = v })
onBeforeUnmount(() => { stop(); ctx?.close() })
</script>

<template>
  <section class="bg-surface rounded-xl shadow p-4 space-y-2">
    <h3 class="font-bold text-slate-800">🎧 {{ t('sounds.title') }}</h3>
    <div class="flex flex-wrap gap-2" role="group" :aria-label="t('sounds.title')">
      <button v-for="k in KINDS" :key="k" type="button" :aria-pressed="playing === k" @click="play(k)"
        :class="['rounded-lg px-3 py-1.5 text-sm', playing === k ? 'bg-primary text-on-primary' : 'border border-slate-400 text-slate-700 hover:bg-slate-50']">
        {{ t(`sounds.${k}`) }}
      </button>
    </div>
    <label class="flex items-center gap-3 text-xs text-slate-600">{{ t('sounds.volume') }}
      <input v-model.number="volume" type="range" min="0" max="1" step="0.05" class="flex-1" /></label>
    <p class="text-xs text-slate-500">{{ t('sounds.hint') }}</p>
  </section>
</template>
