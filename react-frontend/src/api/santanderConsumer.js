import api from './client'

export const submitSantanderConsumerTerreno = async (formData) => {
  const response = await api.post('/santander-consumer/terreno', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}
