import axios from 'axios'
import { getJournalPin } from './journalPin'

const api = axios.create({ baseURL: 'http://localhost:8000' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  const pin = getJournalPin()
  if (pin && (config.url?.startsWith('/api/journal') || config.url?.startsWith('/api/account/export'))) config.headers['X-Journal-Pin'] = pin
  return config
})

export default api