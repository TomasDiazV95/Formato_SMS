import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5013',
  withCredentials: false,
  headers: {
    'X-Requested-With': 'XMLHttpRequest',
  },
  validateStatus: () => true,
})

export default api
