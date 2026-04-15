import api from './client'

export const downloadSmsSample = async (type) => {
  const response = await api.get(`/sms/sample/${type}`, { responseType: 'blob' })
  return response.data
}

export const submitSmsMasivo = async (formData) => {
  const response = await api.post('/sms/athenas', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}

export const submitSmsCrm = async (formData) => {
  const response = await api.post('/sms/crm', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}
