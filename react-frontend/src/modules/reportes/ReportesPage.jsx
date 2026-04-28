import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../../components/InlineAlert'
import { mandantes, procesosMasividad } from '../../data/constants'
import {
  downloadDetalleMasividades,
  downloadReporteMensual,
  fetchCostSummary,
  fetchCostTrend,
  fetchMandanteRanking,
  fetchProcesoVsMes,
} from '../../api/reports'
import { triggerDownload, assertExcelResponse } from '../../utils/download'

const currencyFormat = new Intl.NumberFormat('es-CL', {
  style: 'currency',
  currency: 'CLP',
  maximumFractionDigits: 0,
})

const monthLabels = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
]

const now = new Date()
const initialFilters = {
  mandante: '',
  proceso: '',
  anio: String(now.getFullYear()),
  mes: String(now.getMonth() + 1),
}

const initialDetalle = {
  mandante: '',
  proceso: '',
  desde: '',
  hasta: '',
}

function Reportes() {
  const [filters, setFilters] = useState(initialFilters)
  const [summary, setSummary] = useState(null)
  const [trend, setTrend] = useState([])
  const [ranking, setRanking] = useState([])
  const [matrix, setMatrix] = useState({ periodos: [], items: [] })
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState({ type: 'info', message: '' })
  const [downloading, setDownloading] = useState(false)
  const [downloadingDetalle, setDownloadingDetalle] = useState(false)
  const [detalleFilters, setDetalleFilters] = useState(initialDetalle)

  const years = useMemo(() => {
    const current = now.getFullYear()
    return [current - 2, current - 1, current, current + 1]
  }, [])

  const resumen = summary?.resumen_por_proceso || []
  const kpis = summary?.kpis || { total_registros: 0, costo_total: 0, ticket_promedio: 0 }
  const variacion = summary?.comparativo?.variacion || {}
  const mandantesConMovimiento = ranking.length
  const procesoMayorCosto = useMemo(() => {
    if (!resumen.length) return null
    return [...resumen].sort((a, b) => Number(b.costo_total || 0) - Number(a.costo_total || 0))[0]
  }, [resumen])

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 7000)
    }
  }

  const normalizedQuery = useMemo(
    () => ({
      mandante: filters.mandante || undefined,
      proceso: filters.proceso || undefined,
      anio: Number(filters.anio),
      mes: Number(filters.mes),
    }),
    [filters]
  )

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true)
        const [summaryResp, trendResp, rankingResp, matrixResp] = await Promise.all([
          fetchCostSummary(normalizedQuery),
          fetchCostTrend({ ...normalizedQuery, meses: 12 }),
          fetchMandanteRanking({ ...normalizedQuery, limit: 8 }),
          fetchProcesoVsMes({ mandante: normalizedQuery.mandante, anio: normalizedQuery.anio, mes: normalizedQuery.mes, meses: 6 }),
        ])
        setSummary(summaryResp)
        setTrend(Array.isArray(trendResp?.items) ? trendResp.items : [])
        setRanking(Array.isArray(rankingResp?.items) ? rankingResp.items : [])
        setMatrix({
          periodos: Array.isArray(matrixResp?.periodos) ? matrixResp.periodos : [],
          items: Array.isArray(matrixResp?.items) ? matrixResp.items : [],
        })
      } catch (err) {
        updateStatus('danger', err.message || 'No se pudieron cargar los reportes.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [normalizedQuery])

  const handleFilterChange = event => {
    const { name, value } = event.target
    setFilters(prev => ({ ...prev, [name]: value }))
  }

  const trendMaxCost = useMemo(() => Math.max(1, ...trend.map(item => Number(item.costo_total || 0))), [trend])
  const rankingMaxCost = useMemo(() => Math.max(1, ...ranking.map(item => Number(item.costo_total || 0))), [ranking])

  const formatPct = value => {
    if (value === null || value === undefined) return 'N/A'
    const num = Number(value)
    if (Number.isNaN(num)) return 'N/A'
    const sign = num > 0 ? '+' : ''
    return `${sign}${num.toFixed(2)}%`
  }

  const downloadMensual = async () => {
    try {
      setDownloading(true)
      const response = await downloadReporteMensual({ ...normalizedQuery, meses: 12 })
      await assertExcelResponse(response, 'No se pudo descargar el reporte mensual.')
      const fallback = `reporte_costos_mensual_${filters.anio}_${String(filters.mes).padStart(2, '0')}.xlsx`
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || fallback
      triggerDownload(response.data, filename)
      updateStatus('success', 'Reporte mensual descargado correctamente.')
    } catch (err) {
      updateStatus('danger', err.message || 'No se pudo descargar el reporte mensual.')
    } finally {
      setDownloading(false)
    }
  }

  const handleDetalleChange = e => {
    const { name, value } = e.target
    setDetalleFilters(prev => ({ ...prev, [name]: value }))
  }

  const handleDetalleDownload = async e => {
    e.preventDefault()
    if (!detalleFilters.desde || !detalleFilters.hasta) {
      updateStatus('danger', 'Debes seleccionar fecha desde y hasta para el detalle.')
      return
    }
    try {
      setDownloadingDetalle(true)
      const response = await downloadDetalleMasividades(detalleFilters)
      await assertExcelResponse(response, 'No se pudo descargar el detalle.')
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'detalle_masividades.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Detalle descargado correctamente.')
    } catch (err) {
      updateStatus('danger', err.message || 'No se pudo descargar el detalle.')
    } finally {
      setDownloadingDetalle(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-6xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Reportes</p>
            <h1 className="text-3xl font-semibold text-slate-900">Centro de control mensual</h1>
            <p className="mt-2 max-w-3xl text-slate-600">Vista ejecutiva con filtros por periodo, métricas comparativas y desglose por mandante/proceso.</p>
          </div>
          <div className="flex items-center gap-3">
            <button type="button" className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white" onClick={downloadMensual} disabled={downloading || loading}>
              {downloading ? 'Generando...' : 'Exportar reporte mensual'}
            </button>
            <Link to="/" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
          </div>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <div className="grid gap-4 md:grid-cols-4">
            <div>
              <label className="text-sm font-medium text-slate-700">Año</label>
              <select name="anio" value={filters.anio} onChange={handleFilterChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm">
                {years.map(item => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Mes</label>
              <select name="mes" value={filters.mes} onChange={handleFilterChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm">
                {monthLabels.map((label, index) => (
                  <option key={label} value={index + 1}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Mandante</label>
              <select name="mandante" value={filters.mandante} onChange={handleFilterChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm">
                <option value="">Todos</option>
                {mandantes.map(item => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Proceso</label>
              <select name="proceso" value={filters.proceso} onChange={handleFilterChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm">
                <option value="">Todos</option>
                {procesosMasividad.map(item => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <article className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Cantidad de registros</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{Number(kpis.total_registros || 0).toLocaleString('es-CL')}</p>
            <p className="mt-1 text-sm text-slate-500">Vs mes anterior: {formatPct(variacion.total_registros_pct)}</p>
          </article>
          <article className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Costo total</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{currencyFormat.format(kpis.costo_total || 0)}</p>
            <p className="mt-1 text-sm text-slate-500">Vs mes anterior: {formatPct(variacion.costo_total_pct)}</p>
          </article>
          <article className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Mandantes con movimiento</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{mandantesConMovimiento}</p>
            <p className="mt-1 text-sm text-slate-500">Con costo mayor a 0 en el período</p>
          </article>
          <article className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Proceso con mayor costo</p>
            <p className="mt-2 text-xl font-semibold text-slate-900">{procesoMayorCosto?.proceso || '-'}</p>
            <p className="mt-1 text-sm text-slate-500">{currencyFormat.format(procesoMayorCosto?.costo_total || 0)}</p>
          </article>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <article className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
            <header className="mb-4">
              <h2 className="text-xl font-semibold text-slate-900">Tendencia ultimos 12 meses</h2>
              <p className="text-sm text-slate-600">Costo total por mes segun filtros aplicados.</p>
            </header>
            <div className="space-y-3">
              {loading ? (
                <p className="text-sm text-slate-500">Cargando tendencia...</p>
              ) : trend.length === 0 ? (
                <p className="text-sm text-slate-500">Sin datos para mostrar.</p>
              ) : (
                trend.map(item => {
                  const cost = Number(item.costo_total || 0)
                  const width = `${Math.max(4, (cost / trendMaxCost) * 100)}%`
                  return (
                    <div key={item.periodo} className="space-y-1">
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>{item.periodo}</span>
                        <span>{currencyFormat.format(cost)}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                        <div className="h-full rounded-full bg-indigo-500" style={{ width }} />
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </article>

          <article className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
            <header className="mb-4">
              <h2 className="text-xl font-semibold text-slate-900">Ranking de mandantes</h2>
              <p className="text-sm text-slate-600">Top por costo en el periodo seleccionado.</p>
            </header>
            <div className="space-y-3">
              {loading ? (
                <p className="text-sm text-slate-500">Cargando ranking...</p>
              ) : ranking.length === 0 ? (
                <p className="text-sm text-slate-500">Sin datos para este periodo.</p>
              ) : (
                ranking.map(item => {
                  const cost = Number(item.costo_total || 0)
                  const width = `${Math.max(6, (cost / rankingMaxCost) * 100)}%`
                  return (
                    <div key={item.mandante} className="space-y-1">
                      <div className="flex items-center justify-between gap-3 text-xs">
                        <span className="truncate text-slate-700">{item.mandante}</span>
                        <span className="text-slate-500">{currencyFormat.format(cost)}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                        <div className="h-full rounded-full bg-emerald-500" style={{ width }} />
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </article>
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-4">
            <h2 className="text-xl font-semibold text-slate-900">Matriz proceso vs mes (6 meses)</h2>
            <p className="text-sm text-slate-600">Comparativo de costos por proceso en ventana reciente.</p>
          </header>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="px-3 py-2 font-medium">Proceso</th>
                  {matrix.periodos.map(periodo => (
                    <th key={periodo} className="px-3 py-2 font-medium">{periodo}</th>
                  ))}
                  <th className="px-3 py-2 font-medium">Total costo</th>
                </tr>
              </thead>
              <tbody>
                {matrix.items.length === 0 ? (
                  <tr>
                    <td colSpan={Math.max(3, matrix.periodos.length + 2)} className="px-3 py-6 text-center text-slate-500">Sin informacion de matriz para este filtro.</td>
                  </tr>
                ) : (
                  matrix.items.map(item => (
                    <tr key={item.proceso} className="border-t border-slate-100">
                      <td className="px-3 py-2 font-semibold text-slate-900">{item.proceso}</td>
                      {matrix.periodos.map(periodo => (
                        <td key={`${item.proceso}-${periodo}`} className="px-3 py-2 text-slate-600">{currencyFormat.format(item.periodos?.[periodo]?.costo_total || 0)}</td>
                      ))}
                      <td className="px-3 py-2 text-slate-700">{currencyFormat.format(item.total_costo || 0)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-4">
            <h2 className="text-xl font-semibold text-slate-900">Resumen por proceso del mes</h2>
          </header>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="px-3 py-2 font-medium">Proceso</th>
                  <th className="px-3 py-2 font-medium">Descripcion</th>
                  <th className="px-3 py-2 font-medium">Registros</th>
                  <th className="px-3 py-2 font-medium">Costo total</th>
                </tr>
              </thead>
              <tbody>
                {resumen.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-3 py-6 text-center text-slate-500">Sin datos para este mes/filtro.</td>
                  </tr>
                ) : (
                  resumen.map(row => (
                    <tr key={row.proceso} className="border-t border-slate-100">
                      <td className="px-3 py-2 font-semibold text-slate-900">{row.proceso}</td>
                      <td className="px-3 py-2 text-slate-600">{row.descripcion || '-'}</td>
                      <td className="px-3 py-2 text-slate-600">{Number(row.total_registros || 0).toLocaleString('es-CL')}</td>
                      <td className="px-3 py-2 text-slate-600">{currencyFormat.format(row.costo_total || 0)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-6">
            <h2 className="text-xl font-semibold text-slate-900">Detalle por contacto</h2>
            <p className="text-sm text-slate-600">Descarga desde masividades_detalle para auditoria operativa.</p>
          </header>
          <form className="space-y-5" onSubmit={handleDetalleDownload}>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-slate-700">Mandante</label>
                <select name="mandante" value={detalleFilters.mandante} onChange={handleDetalleChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm">
                  <option value="">Todos</option>
                  {mandantes.map(nombre => (
                    <option key={nombre} value={nombre}>{nombre}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Proceso</label>
                <select name="proceso" value={detalleFilters.proceso} onChange={handleDetalleChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm">
                  <option value="">Todos</option>
                  {procesosMasividad.map(code => (
                    <option key={code} value={code}>{code}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-slate-700">Fecha desde</label>
                <input type="date" name="desde" value={detalleFilters.desde} onChange={handleDetalleChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Fecha hasta</label>
                <input type="date" name="hasta" value={detalleFilters.hasta} onChange={handleDetalleChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button type="submit" className="inline-flex items-center rounded-full bg-emerald-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-500 disabled:opacity-60" disabled={downloadingDetalle}>
                {downloadingDetalle ? 'Generando...' : 'Descargar detalle'}
              </button>
              <p className="text-xs text-slate-500">Recomendacion: descargar por tramos de 30 dias.</p>
            </div>
          </form>
        </section>
      </div>
    </main>
  )
}

export default Reportes
