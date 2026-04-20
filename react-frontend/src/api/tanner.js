import api from './client'

export const submitTannerProcess = async formData => {
  const response = await api.post('/cargaTanner', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}
