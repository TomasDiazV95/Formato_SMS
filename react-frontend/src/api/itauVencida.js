import api from './client'

export const submitItauVencida = async (formData) => {
  return api.post('/itau-vencida/generar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
}
