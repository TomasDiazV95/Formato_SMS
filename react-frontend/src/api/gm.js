import api from './client'

export const submitGmProcess = async (formData) => {
  const response = await api.post('/cargaGM', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}
