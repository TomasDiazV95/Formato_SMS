import api from './client'

export const fetchCatalogosBackoffice = async () => {
  const response = await api.get('/api/backoffice/catalogos')
  if (response.status >= 400) {
    const message = response.data?.message || 'No se pudo obtener catalogos de backoffice.'
    throw new Error(message)
  }
  return response.data
}

export const fetchCampo1Catalogo = async () => {
  const response = await api.get('/api/backoffice/campo1')
  if (response.status >= 400) {
    const message = response.data?.message || 'No se pudo obtener CAMPO1.'
    throw new Error(message)
  }
  return response.data
}

export const createCampo1Item = async payload => {
  const response = await api.post('/api/backoffice/campo1', payload)
  if (response.status >= 400) {
    const message = response.data?.message || 'No se pudo crear CAMPO1.'
    throw new Error(message)
  }
  return response.data
}

export const updateCampo1Item = async (id, payload) => {
  const response = await api.put(`/api/backoffice/campo1/${id}`, payload)
  if (response.status >= 400) {
    const message = response.data?.message || 'No se pudo actualizar CAMPO1.'
    throw new Error(message)
  }
  return response.data
}

export const deleteCampo1Item = async id => {
  const response = await api.delete(`/api/backoffice/campo1/${id}`)
  if (response.status >= 400) {
    const message = response.data?.message || 'No se pudo eliminar CAMPO1.'
    throw new Error(message)
  }
  return response.data
}
