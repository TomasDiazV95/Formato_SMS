import api from './client'

export const submitBitProcess = async formData => {
  const response = await api.post('/cargaBIT', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}
