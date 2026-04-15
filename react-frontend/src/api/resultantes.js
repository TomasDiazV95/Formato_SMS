import api from './client'

export const downloadResultante = async ({ mandante, fechaInicio, fechaFin }) => {
  return api.get('/resultantes/download', {
    params: { mandante, fecha_inicio: fechaInicio, fecha_fin: fechaFin },
    responseType: 'blob',
  })
}
