import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../../../components/InlineAlert'
import { processSantander, downloadSantanderCrm, downloadSantanderMasiv } from '../../../api/santander'
import { triggerDownload } from '../../../utils/download'

const initialResult = {
  token: '',
  crmName: '',
  masivName: '',
}

function SantanderPage() {
  const archivoRef = useRef(null)
  const [masividades, setMasividades] = useState(false)
  const [status, setStatus] = useState({ type: 'info', message: '' })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(initialResult)

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 6000)
    }
  }

  const resetForm = () => {
    if (archivoRef.current) archivoRef.current.value = ''
    setMasividades(false)
    setResult(initialResult)
  }

  const handleSubmit = async e => {
    e.preventDefault()
    const archivo = archivoRef.current?.files?.[0]
    if (!archivo) {
      updateStatus('danger', 'Debes subir el archivo CSV (separado por ;)')
      return
    }

    const formData = new FormData()
    formData.append('archivo', archivo)
    if (masividades) formData.append('habilitar_masividades', 'on')

    try {
      setLoading(true)
      const data = await processSantander(formData)
      setResult({ token: data.token || '', crmName: data.crm_name || '', masivName: data.masiv_name || '' })
      setMasividades(Boolean(data.masividades_activadas ?? masividades))
      updateStatus('success', data.message || 'Archivo procesado correctamente.')
    } catch (error) {
      updateStatus('danger', error.message || 'Error procesando el archivo.')
      setResult(initialResult)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async type => {
    if (!result.token) {
      updateStatus('danger', 'Procesa un archivo antes de descargar.')
      return
    }
    try {
      const response = type === 'crm' ? await downloadSantanderCrm(result.token) : await downloadSantanderMasiv(result.token)
      const fallback = type === 'crm' ? 'crm_santander.xlsx' : 'masividad_santander.xlsx'
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || fallback
      triggerDownload(response.data, filename)
      updateStatus('success', 'Descarga lista.')
    } catch (error) {
      updateStatus('danger', error.message || 'No se pudo descargar el archivo.')
    }
  }

  return (
    <main className="relative min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 px-4 py-8">
      {loading && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-white/70 backdrop-blur-sm">
          <div className="rounded-3xl bg-white px-8 py-6 shadow-lg">
            <div className="mx-auto mb-3 h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-indigo-500" />
            <p className="text-sm font-semibold text-slate-700">Procesando archivo…</p>
            <p className="text-xs text-slate-500">Esto puede tardar unos segundos.</p>
          </div>
        </div>
      )}
      <div className="mx-auto max-w-4xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Santander Hipotecario</p>
            <h1 className="text-3xl font-semibold text-slate-900">CSV → CRM / Masividad</h1>
            <p className="mt-2 max-w-2xl text-slate-600">El backend sigue generando archivos en outputs/sant_hipotecario; aquí solo refrescamos la interfaz.</p>
          </div>
          <Link to="/cargas" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="text-sm font-medium text-slate-700">Archivo CSV</label>
              <input ref={archivoRef} type="file" accept=".csv,text/csv" className="mt-1 block w-full rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm" required />
              <p className="mt-2 text-xs text-slate-500">CSV separado por punto y coma. Se normaliza igual que en Flask.</p>
            </div>

            <label className="flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3">
              <input type="checkbox" className="h-5 w-5 rounded border-slate-300" checked={masividades} onChange={e => setMasividades(e.target.checked)} />
              <div>
                <span className="font-semibold text-slate-900">Activar masividades</span>
                <p className="text-sm text-slate-500">Si está activo, se intentará generar y habilitar la descarga de masividad.</p>
              </div>
            </label>

            <div className="flex flex-wrap gap-3">
              <button type="submit" className="inline-flex items-center rounded-full bg-amber-500 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-amber-400" disabled={loading}>
                {loading ? 'Procesando…' : 'Procesar archivo'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={resetForm}>
                Limpiar
              </button>
            </div>
          </form>
        </section>

        {result.token && (
          <section className="grid gap-4 md:grid-cols-2">
            <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">CRM</p>
              <h3 className="text-xl font-semibold text-slate-900">Archivo listo</h3>
              <p className="mt-1 text-sm text-slate-600">{result.crmName || 'crm generado.xlsx'}</p>
              <button type="button" className="mt-4 inline-flex items-center rounded-full border border-indigo-200 px-4 py-2 text-sm font-semibold text-indigo-600 transition hover:bg-indigo-50" onClick={() => handleDownload('crm')}>
                Descargar CRM
              </button>
            </div>
            <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Masividad</p>
              {masividades ? (
                result.masivName ? (
                  <>
                    <h3 className="text-xl font-semibold text-slate-900">Archivo listo</h3>
                    <p className="mt-1 text-sm text-slate-600">{result.masivName}</p>
                    <button type="button" className="mt-4 inline-flex items-center rounded-full border border-emerald-200 px-4 py-2 text-sm font-semibold text-emerald-600 transition hover:bg-emerald-50" onClick={() => handleDownload('masiv')}>
                      Descargar masividad
                    </button>
                  </>
                ) : (
                  <>
                    <h3 className="text-xl font-semibold text-slate-900">Aún no disponible</h3>
                    <p className="mt-1 text-sm text-slate-600">Procesa con el switch activado para habilitar la descarga.</p>
                    <button type="button" className="mt-4 cursor-not-allowed rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-400" disabled>
                      Descargar masividad
                    </button>
                  </>
                )
              ) : (
                <>
                  <h3 className="text-xl font-semibold text-slate-900">Masividades desactivadas</h3>
                  <p className="mt-1 text-sm text-slate-600">Activa el switch y vuelve a procesar si necesitas el Excel.</p>
                </>
              )}
            </div>
          </section>
        )}

        <section className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <p className="font-semibold text-slate-800">Notas</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
            <li>CRM siempre se genera y queda disponible hasta reiniciar la app (token en memoria).</li>
            <li>Masividad solo existe si activas el switch y los correos pasan las validaciones.</li>
            <li>Las descargas usan los mismos endpoints `/sant-hipotecario/descargar/...` del backend Flask.</li>
          </ul>
        </section>
      </div>
    </main>
  )
}

export default SantanderPage
