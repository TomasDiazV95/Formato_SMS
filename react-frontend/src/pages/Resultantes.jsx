import { useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../components/InlineAlert'
import { resultantesMandantes } from '../data/constants'
import { downloadResultante } from '../api/resultantes'
import { assertExcelResponse, triggerDownload } from '../utils/download'

const initialDates = Object.fromEntries(
  resultantesMandantes.map(item => [item.code, { inicio: '', fin: '' }]),
)

function Resultantes() {
  const [dates, setDates] = useState(initialDates)
  const [loadingCode, setLoadingCode] = useState('')
  const [status, setStatus] = useState({ type: 'info', message: '' })

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 6000)
    }
  }

  const handleDateChange = (code, key, value) => {
    setDates(prev => ({
      ...prev,
      [code]: {
        ...(prev[code] || { inicio: '', fin: '' }),
        [key]: value,
      },
    }))
  }

  const handleDownload = async item => {
    const fechaInicio = dates[item.code]?.inicio || ''
    const fechaFin = dates[item.code]?.fin || fechaInicio

    if (!fechaInicio) {
      updateStatus('danger', `Debes seleccionar fecha inicio para ${item.label}.`)
      return
    }
    if (fechaFin < fechaInicio) {
      updateStatus('danger', `La fecha termino no puede ser menor que la fecha inicio en ${item.label}.`)
      return
    }
    if (!item.enabled) {
      updateStatus('danger', `${item.label} aun no esta implementado.`)
      return
    }

    try {
      setLoadingCode(item.code)
      const response = await downloadResultante({ mandante: item.label, fechaInicio, fechaFin })
      await assertExcelResponse(response, 'No se pudo descargar la resultante.', ['text/plain'])
      const fallback = `resultantes_${item.code}_${fechaInicio}.txt`
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || fallback
      triggerDownload(response.data, filename)
      updateStatus('success', `Resultante de ${item.label} descargada.`)
    } catch (error) {
      updateStatus('danger', error?.message || 'No se pudo descargar la resultante.')
    } finally {
      setLoadingCode('')
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-6xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Resultantes</p>
            <h1 className="text-3xl font-semibold text-slate-900">Descarga por mandante</h1>
            <p className="mt-2 text-slate-600">Selecciona rango de fechas (o un solo dia) y descarga gestiones. Tanner ya esta habilitado en TXT.</p>
          </div>
          <Link to="/" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {resultantesMandantes.map(item => {
            const isLoading = loadingCode === item.code
            return (
              <article key={item.code} className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Mandante</p>
                <h2 className="mt-2 text-xl font-semibold text-slate-900">{item.label}</h2>
                <p className="mt-1 text-sm text-slate-600">{item.enabled ? 'Disponible para descarga.' : 'Cascaron creado. Proximamente.'}</p>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="text-sm font-medium text-slate-700">Fecha inicio</label>
                    <input
                      type="date"
                      value={dates[item.code]?.inicio || ''}
                      onChange={e => handleDateChange(item.code, 'inicio', e.target.value)}
                      className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-slate-700">Fecha termino</label>
                    <input
                      type="date"
                      value={dates[item.code]?.fin || ''}
                      onChange={e => handleDateChange(item.code, 'fin', e.target.value)}
                      className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                    />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleDownload(item)}
                  disabled={isLoading || !item.enabled}
                  className="mt-4 inline-flex w-full items-center justify-center rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isLoading ? 'Descargando...' : item.enabled ? 'Descargar' : 'Proximamente'}
                </button>
              </article>
            )
          })}
        </section>
      </div>
    </main>
  )
}

export default Resultantes
