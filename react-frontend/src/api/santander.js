import api from './client'

export const processSantander = async (formData) => {
  const response = await api.post('/sant-hipotecario', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  if (response.status >= 400) {
    const message = response.data?.message || 'Error procesando el archivo.'
    throw new Error(message)
  }
  return response.data
}

export const downloadSantanderCrm = async (token) => {
  const response = await api.get(`/sant-hipotecario/descargar/crm/${token}`, { responseType: 'blob' })
  return response
}

export const downloadSantanderMasiv = async (token) => {
  const response = await api.get(`/sant-hipotecario/descargar/masividad/${token}`, { responseType: 'blob' })
  return response
}
