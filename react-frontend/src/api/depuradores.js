import api from './client'

export const submitDireccionesDepurador = async (formData) => {
  const response = await api.post('/depuradores/direcciones', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  return response
}
