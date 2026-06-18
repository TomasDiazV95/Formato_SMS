import api from './client'

export const fetchScTelefoniaMailTemplates = async () => {
  const response = await api.get('/sc-telefonia-mail/templates')
  return response
}

export const fetchScTelefoniaMailExecutives = async (templateKey) => {
  const response = await api.get('/sc-telefonia-mail/executives', {
    params: { template_key: templateKey },
  })
  return response
}

export const submitScTelefoniaMail = async (formData) => {
  const response = await api.post('/sc-telefonia-mail/generar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}
