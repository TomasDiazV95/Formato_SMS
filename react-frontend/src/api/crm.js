import api from './client'

export const createCrmSession = async ({ file, mode, source }) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('mode', mode)
  if (source) formData.append('source', source)

  return api.post('/crm/session', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const submitCrmCarga = async formData => {
  return api.post('/crm/carga', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
}
