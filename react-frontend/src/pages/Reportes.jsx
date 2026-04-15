import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../components/InlineAlert'
import { mandantes, procesosMasividad } from '../data/constants'
import { fetchCostSummary, downloadCostosMandante, downloadCostosTotales, downloadDetalleMasividades } from '../api/reports'
import { triggerDownload, assertExcelResponse } from '../utils/download'

const currencyFormat = new Intl.NumberFormat('es-CL', {
  style: 'currency',
  currency: 'CLP',
  maximumFractionDigits: 0,
})

function Reportes() {
  const [selectedMandante, setSelectedMandante] = useState('')
  const [summary, setSummary] = useState(null)
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [downloadingDetalle, setDownloadingDetalle] = useState(false)
  const [status, setStatus] = useState({ type: 'info', message: '' })
  const [detalleFilters, setDetalleFilters] = useState({ mandante: '', proceso: '', desde: '', hasta: '' })

  const resumen = summary?.resumen_por_proceso || []
  const totales = summary?.totales || { total_registros: 0, costo_total: 0 }

  useEffect(() => {
    const load = async () => {
      setLoadingSummary(true)
      try {
        const data = await fetchCostSummary(selectedMandante || undefined)
        setSummary(data)
      } catch (err) {
        setStatus({ type: 'danger', message: err.message || 'No se pudo obtener el resumen.' })
      } finally {
        setLoadingSummary(false)
      }
    }
    load()
  }, [selectedMandante])

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 6000)
    }
  }

  const downloadFile = async type => {
    try {
      setDownloading(true)
      const response = type === 'totales'
        ? await downloadCostosTotales()
        : await downloadCostosMandante(selectedMandante)
      await assertExcelResponse(response, 'No se pudo descargar el reporte.')
      const fallback = type === 'totales' ? 'reporte_costos_totales.xlsx' : `reporte_costos_${selectedMandante || 'mandante'}.xlsx`
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || fallback
      triggerDownload(response.data, filename)
      updateStatus('success', 'Descarga iniciada correctamente.')
    } catch (err) {
      updateStatus('danger', err.message || 'No se pudo descargar el reporte.')
    } finally {
      setDownloading(false)
    }
  }

  const handleMandanteChange = e => {
    setSelectedMandante(e.target.value)
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
      const fallback = 'detalle_masividades.xlsx'
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || fallback
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
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Reportes</p>
            <h1 className="text-3xl font-semibold text-slate-900">Costos de masividades</h1>
            <p className="mt-2 max-w-2xl text-slate-600">Los datos provienen de los mismos endpoints Flask (/reportes/costos y /reports/costos/*).</p>
          </div>
          <Link to="/" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <div className="flex flex-col gap-4 md:flex-row md:items-end">
            <div className="flex-1">
              <label className="text-sm font-medium text-slate-700">Mandante</label>
              <select value={selectedMandante} onChange={handleMandanteChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm">
                <option value="">Consolidado general</option>
                {mandantes.map(nombre => (
                  <option key={nombre} value={nombre}>{nombre}</option>
                ))}
              </select>
              <p className="mt-2 text-xs text-slate-500">El resumen y el Excel filtrado se actualizarán usando este mandante.</p>
            </div>
            <div className="flex gap-3">
              <button type="button" className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500" onClick={() => downloadFile('totales')} disabled={downloading}>
                {downloading ? 'Generando…' : 'Descargar totales'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 disabled:opacity-50" onClick={() => downloadFile('mandante')} disabled={!selectedMandante || downloading}>
                {downloading ? 'Generando…' : 'Descargar por mandante'}
              </button>
            </div>
          </div>
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-6">
            <h2 className="text-xl font-semibold text-slate-900">Resumen {selectedMandante ? `de ${selectedMandante}` : 'general'}</h2>
            <p className="text-sm text-slate-600">Los totales salen directo de masividades_log (utilizando services/db_repos.get_cost_summary).</p>
          </header>
          {loadingSummary ? (
            <div className="py-10 text-center text-slate-500">Cargando datos…</div>
          ) : (
            <div className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Total registros</p>
                  <p className="mt-2 text-2xl font-semibold text-slate-900">{totales.total_registros?.toLocaleString('es-CL')}</p>
                </div>
                <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Costo total</p>
                  <p className="mt-2 text-2xl font-semibold text-slate-900">{currencyFormat.format(totales.costo_total || 0)}</p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[480px] text-sm">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="px-3 py-2 font-medium">Proceso</th>
                      <th className="px-3 py-2 font-medium">Descripción</th>
                      <th className="px-3 py-2 font-medium">Registros</th>
                      <th className="px-3 py-2 font-medium">Costo total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resumen.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-3 py-6 text-center text-slate-500">Sin datos para este filtro.</td>
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
            </div>
          )}
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-6">
            <h2 className="text-xl font-semibold text-slate-900">Detalle por contacto</h2>
            <p className="text-sm text-slate-600">Descarga el desglose desde `masividades_detalle` con RUT, teléfono y archivo generado.</p>
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
                {downloadingDetalle ? 'Generando…' : 'Descargar detalle'}
              </button>
              <p className="text-xs text-slate-500">El rango recomendado es de hasta 30 días para evitar archivos muy pesados.</p>
            </div>
          </form>
        </section>
      </div>
    </main>
  )
}

export default Reportes
