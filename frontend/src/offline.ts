// Offline mode is opt-in: nothing is cached on the device until the user switches it on (Settings).
// Only the app's own files are kept; API data never is (see public/sw.js).
const KEY = 'offlineMode'

export const offlineSupported = () => 'serviceWorker' in navigator && import.meta.env.PROD
export const offlineEnabled = (): boolean => {
  try { return localStorage.getItem(KEY) === 'on' } catch { return false }
}

export async function setOffline(on: boolean): Promise<void> {
  try { localStorage.setItem(KEY, on ? 'on' : 'off') } catch { /* not remembered, still applied now */ }
  if (!offlineSupported()) return
  if (on) {
    await navigator.serviceWorker.register('/sw.js')
  } else {
    const regs = await navigator.serviceWorker.getRegistrations()
    await Promise.all(regs.map((r) => r.unregister()))
    for (const key of await caches.keys()) await caches.delete(key)
  }
}
