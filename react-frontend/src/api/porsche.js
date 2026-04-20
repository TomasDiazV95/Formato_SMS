import api from './client'

export const submitPorscheProcess = async formData => {
  const response = await api.post('/cargaPorsche', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}
