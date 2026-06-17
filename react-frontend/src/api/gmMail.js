import api from './client'

export const fetchGmMailTemplates = async () => {
  const response = await api.get('/gm-mail/templates')
  return response
}

export const submitGmMail = async (formData) => {
  const response = await api.post('/gm-mail/generar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}
