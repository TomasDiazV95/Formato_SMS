import api from './client'

export const fetchCostSummary = async (mandante) => {
  const response = await api.get('/reportes/costos', {
    params: mandante ? { mandante } : undefined,
  })
  if (response.status >= 400) {
    const message = response.data?.message || 'No se pudo obtener el resumen.'
    throw new Error(message)
  }
  return response.data
}

export const downloadCostosTotales = async () => {
  return api.get('/reports/costos/totales', { responseType: 'blob' })
}

export const downloadCostosMandante = async (mandante) => {
  return api.get('/reports/costos/mandante', {
    params: { mandante },
    responseType: 'blob',
  })
}

export const downloadDetalleMasividades = async ({ mandante, proceso, desde, hasta }) => {
  const params = {}
  if (mandante) params.mandante = mandante
  if (proceso) params.proceso = proceso
  if (desde) params.desde = desde
  if (hasta) params.hasta = hasta
  return api.get('/reports/detalle', {
    params,
    responseType: 'blob',
  })
}
