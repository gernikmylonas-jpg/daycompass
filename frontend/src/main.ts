import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import { i18n } from './i18n'
import { useSettingsStore } from './stores/settings'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia).use(router).use(i18n)
useSettingsStore(pinia) // applies the saved theme before the first render
app.mount('#app')

// offline support: only in the production build, where the files are stable
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => { /* not available (e.g. private window): the app works online as usual */ })
  })
}
