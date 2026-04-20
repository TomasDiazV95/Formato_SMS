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

export const fetchIvrCampo1Options = async () => {
  const response = await api.get('/ivr/campo1-options')
  if (response.status >= 400) {
    const message = response.data?.message || 'No se pudieron cargar opciones CAMPO1.'
    throw new Error(message)
  }
  return Array.isArray(response.data?.items) ? response.data.items : []
}
