import axios from 'axios'
import { getJournalPin } from './journalPin'

// Where the API lives. Development talks to localhost:8000. In a production build the site and the API share one
// address (a reverse proxy sends /api to the backend), so the default is "same origin". Set VITE_API_URL to override.
const configured = import.meta.env.VITE_API_URL as string | undefined
export const API_BASE: string = configured ?? (import.meta.env.PROD ? '' : 'http://localhost:8000')

/** The WebSocket address of the API (ws:// or wss://, following the page when the API is on the same origin). */
export const wsBase = (): string =>
  API_BASE ? API_BASE.replace(/^http/, 'ws') : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`

const api = axios.create({ baseURL: API_BASE })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  const pin = getJournalPin()
  if (pin && (config.url?.startsWith('/api/journal') || config.url?.startsWith('/api/account/export'))) config.headers['X-Journal-Pin'] = pin
  return config
})

export default api
