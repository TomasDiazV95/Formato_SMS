import api from './client'

export const downloadResultante = async ({ mandante, fechaInicio, fechaFin, modo }) => {
  return api.get('/resultantes/download', {
    params: { mandante, fecha_inicio: fechaInicio, fecha_fin: fechaFin, modo },
    responseType: 'blob',
  })
}
