import api from './client'

export const downloadIvrSample = async () => {
  const response = await api.get('/ivr/sample', { responseType: 'blob' })
  return response.data
}

export const submitIvrAthenas = async (formData) => {
  const response = await api.post('/ivr/process', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}

export const submitIvrCrm = async (formData) => {
  const response = await api.post('/ivr_crm/process', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}
