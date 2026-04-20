import api from './client'

export const fetchCostSummary = async ({ mandante, proceso, anio, mes, desde, hasta } = {}) => {
  const params = {}
  if (mandante) params.mandante = mandante
  if (proceso) params.proceso = proceso
  if (anio) params.anio = anio
  if (mes) params.mes = mes
  if (desde) params.desde = desde
  if (hasta) params.hasta = hasta
  const response = await api.get('/reportes/costos', {
    params,
  })
  if (response.status >= 400) {
    const message = response.data?.message || 'No se pudo obtener el resumen.'
    throw new Error(message)
  }
  return response.data
}

export const fetchCostTrend = async ({ mandante, proceso, meses = 12, anio, mes } = {}) => {
  const params = { meses }
  if (mandante) params.mandante = mandante
  if (proceso) params.proceso = proceso
  if (anio) params.anio = anio
  if (mes) params.mes = mes
  const response = await api.get('/reportes/costos/tendencia', { params })
  if (response.status >= 400) {
    const message = response.data?.message || 'No se pudo obtener la tendencia mensual.'
    throw new Error(message)
  }
  return response.data
}

export const fetchMandanteRanking = async ({ proceso, anio, mes, desde, hasta, limit = 10 } = {}) => {
  const params = { limit }
  if (proceso) params.proceso = proceso
  if (anio) params.anio = anio
  if (mes) params.mes = mes
  if (desde) params.desde = desde
  if (hasta) params.hasta = hasta
  const response = await api.get('/reportes/costos/ranking-mandantes', { params })
  if (response.status >= 400) {
    const message = response.data?.message || 'No se pudo obtener ranking de mandantes.'
    throw new Error(message)
  }
  return response.data
}

export const fetchProcesoVsMes = async ({ mandante, meses = 6, anio, mes } = {}) => {
  const params = { meses }
  if (mandante) params.mandante = mandante
  if (anio) params.anio = anio
  if (mes) params.mes = mes
  const response = await api.get('/reportes/costos/proceso-vs-mes', { params })
  if (response.status >= 400) {
    const message = response.data?.message || 'No se pudo obtener matriz proceso vs mes.'
    throw new Error(message)
  }
  return response.data
}

export const fetchProcessHistory = async ({ proceso, limit = 20 }) => {
  const response = await api.get('/reportes/historial', {
    params: { proceso, limit },
  })
  if (response.status >= 400) {
    const message = response.data?.message || 'No se pudo obtener el historial del proceso.'
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

export const downloadReporteMensual = async ({ mandante, proceso, anio, mes, desde, hasta, meses = 12 } = {}) => {
  const params = { meses }
  if (mandante) params.mandante = mandante
  if (proceso) params.proceso = proceso
  if (anio) params.anio = anio
  if (mes) params.mes = mes
  if (desde) params.desde = desde
  if (hasta) params.hasta = hasta
  return api.get('/reports/costos/mensual', {
    params,
    responseType: 'blob',
  })
}
