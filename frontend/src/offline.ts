// Two separate, opt-in switches in Settings share one service worker (public/sw.js):
//  - "Work offline": keeps the app's own files on this device (never API data)
//  - "Push notifications": a reminder when you still have habits open today
// Nothing is registered until the user switches one of them on.
import api from './api'

const OFFLINE_KEY = 'offlineMode'
const PUSH_KEY = 'pushOn'

const flag = (key: string): boolean => {
  try { return localStorage.getItem(key) === 'on' } catch { return false }
}
const store = (key: string, on: boolean) => {
  try { localStorage.setItem(key, on ? 'on' : 'off') } catch { /* not remembered, still applied now */ }
}

export const offlineSupported = () => 'serviceWorker' in navigator && import.meta.env.PROD
export const offlineEnabled = () => flag(OFFLINE_KEY)
export const pushSupported = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
export const pushEnabled = () => flag(PUSH_KEY)

/** Registers (or removes) the service worker so that it matches exactly what the user switched on. */
export async function syncServiceWorker(): Promise<void> {
  if (!('serviceWorker' in navigator)) return
  const offline = offlineSupported() && offlineEnabled()
  const push = pushSupported() && pushEnabled()
  if (!offline && !push) {
    for (const r of await navigator.serviceWorker.getRegistrations()) await r.unregister()
    for (const key of await caches.keys()) await caches.delete(key)
    return
  }
  await navigator.serviceWorker.register(offline ? '/sw.js?offline=1' : '/sw.js')
}

export async function setOffline(on: boolean): Promise<void> {
  store(OFFLINE_KEY, on)
  await syncServiceWorker()
}

const keyBytes = (b64: string) => {
  const raw = atob((b64 + '='.repeat((4 - (b64.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(raw, (c) => c.charCodeAt(0))
}

export type PushResult = 'on' | 'denied' | 'unavailable'

/** Asks the browser for permission, subscribes this device and tells the server. */
export async function enablePush(): Promise<PushResult> {
  if (!pushSupported()) return 'unavailable'
  const { data } = await api.get<{ enabled: boolean; public_key: string | null }>('/api/push/key')
  if (!data.enabled || !data.public_key) return 'unavailable'
  if ((await Notification.requestPermission()) !== 'granted') return 'denied'
  store(PUSH_KEY, true)
  await syncServiceWorker()
  const reg = await navigator.serviceWorker.ready
  const sub = (await reg.pushManager.getSubscription()) ?? (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(data.public_key) }))
  await api.post('/api/push/subscribe', sub.toJSON())
  await api.post('/api/push/test') // so you can see right away that it works
  return 'on'
}

export async function disablePush(): Promise<void> {
  store(PUSH_KEY, false)
  try {
    const reg = await navigator.serviceWorker.getRegistration()
    const sub = await reg?.pushManager.getSubscription()
    if (sub) {
      await api.post('/api/push/unsubscribe', { endpoint: sub.endpoint }).catch(() => {})
      await sub.unsubscribe()
    }
  } finally {
    await syncServiceWorker()
  }
}
