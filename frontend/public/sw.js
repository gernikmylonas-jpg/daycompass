// DayCompass service worker. It does two independent, opt-in things:
//  - push notifications (always handled here once the user turned them on in Settings)
//  - keeping the app's own files for offline use, ONLY when registered as /sw.js?offline=1 (Settings → Work offline).
// API data is never cached, so nothing private (journal, health data) ends up on the device.
const OFFLINE = new URL(self.location.href).searchParams.get('offline') === '1'
const CACHE = 'daycompass-shell-v1'

self.addEventListener('install', (event) => {
  event.waitUntil((OFFLINE ? caches.open(CACHE).then((c) => c.add('/')) : Promise.resolve()).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => !OFFLINE || k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

if (OFFLINE) {
  self.addEventListener('fetch', (event) => {
    const req = event.request
    const url = new URL(req.url)
    if (req.method !== 'GET' || url.origin !== self.location.origin) return
    // pages: the network first, the saved shell when offline
    if (req.mode === 'navigate') {
      event.respondWith(fetch(req).catch(() => caches.match('/')))
      return
    }
    // scripts, styles, images, fonts: the saved copy first, refreshed in the background
    event.respondWith(
      caches.match(req).then((hit) => {
        const fresh = fetch(req).then((res) => {
          if (res.ok) caches.open(CACHE).then((c) => c.put(req, res.clone()))
          return res
        })
        return hit || fresh
      }),
    )
  })
}

self.addEventListener('push', (event) => {
  let data = {}
  try { data = event.data ? event.data.json() : {} } catch { data = { body: event.data ? event.data.text() : '' } }
  event.waitUntil(
    self.registration.showNotification(data.title || 'DayCompass', {
      body: data.body || '', icon: '/icon-192.png', badge: '/icon-192.png', data: { url: data.url || '/' },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = (event.notification.data && event.notification.data.url) || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((wins) => {
      const open = wins.find((w) => new URL(w.url).origin === self.location.origin)
      return open ? open.focus() : self.clients.openWindow(target)
    }),
  )
})
