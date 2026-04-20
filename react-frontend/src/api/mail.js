import api from './client'

export const submitMailTemplate = async (formData) => {
  const response = await api.post('/mail/template', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}

export const downloadMailTemplateSample = async (templateCode) => {
  return api.get('/mail/sample/template', {
    params: templateCode ? { template_code: templateCode } : undefined,
    responseType: 'blob',
  })
}
