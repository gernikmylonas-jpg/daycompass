import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import { i18n } from './i18n'
import { useSettingsStore } from './stores/settings'
import { offlineEnabled, pushEnabled, syncServiceWorker } from './offline'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia).use(router).use(i18n)
useSettingsStore(pinia) // applies the saved theme before the first render
app.mount('#app')

// the service worker (offline files and/or push) is registered only for what the user switched on in Settings
if ('serviceWorker' in navigator && (offlineEnabled() || pushEnabled())) {
  window.addEventListener('load', () => { syncServiceWorker().catch(() => { /* e.g. a private window: the app works online as usual */ }) })
}
