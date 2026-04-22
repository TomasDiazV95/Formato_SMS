import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../../../components/InlineAlert'
import { submitBitProcess } from '../../../api/bit'
import { triggerDownload } from '../../../utils/download'

function BitPage() {
  const archivoRef = useRef(null)
  const [campanaNueva, setCampanaNueva] = useState(false)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState({ type: 'info', message: '' })

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 6000)
    }
  }

  const resetForm = () => {
    if (archivoRef.current) archivoRef.current.value = ''
    setCampanaNueva(false)
  }

  const handleSubmit = async e => {
    e.preventDefault()
    const archivo = archivoRef.current?.files?.[0]
    if (!archivo) {
      updateStatus('danger', 'Debes subir un archivo CSV de BIT.')
      return
    }

    const formData = new FormData()
    formData.append('archivo', archivo)
    if (campanaNueva) formData.append('campana_nueva', 'on')

    try {
      setLoading(true)
      const response = await submitBitProcess(formData)
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'BIT_CARGA.zip'
      triggerDownload(response.data, filename)
      updateStatus('success', 'ZIP generado correctamente con CARGA BIT e Info adicional.')
    } catch (error) {
      updateStatus('danger', error?.message || 'Error procesando la carga BIT.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-sky-50 via-white to-cyan-50 px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-8">
        <section className="relative overflow-hidden rounded-3xl border border-sky-200 bg-white p-8 shadow-sm">
          <div className="pointer-events-none absolute -right-20 -top-16 h-56 w-56 rounded-full bg-cyan-200/50 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-16 -left-20 h-60 w-60 rounded-full bg-sky-200/60 blur-3xl" />

          <div className="relative flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.32em] text-sky-600">Carga BIT</p>
              <h1 className="mt-2 text-3xl font-semibold text-slate-900">Asignacion + Datos Adicionales</h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-600">
                Sube un CSV de BIT y descarga un ZIP con dos archivos: la carga CRM y el archivo de datos adicionales.
              </p>
            </div>
            <Link to="/cargas" className="rounded-full border border-sky-200 px-4 py-2 text-sm text-sky-700 transition hover:bg-sky-50">
              ← Volver
            </Link>
          </div>
        </section>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="rounded-3xl border border-sky-100 bg-white p-6 shadow-sm">
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="text-sm font-medium text-slate-700">Archivo CSV BIT</label>
              <input
                ref={archivoRef}
                type="file"
                accept=".csv,text/csv"
                className="mt-1 block w-full rounded-2xl border border-dashed border-sky-300 px-4 py-3 text-sm"
                required
              />
              <p className="mt-2 text-xs text-slate-500">CSV separado por ';'. Se detecta encoding automaticamente.</p>
            </div>

            <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">Tipo de asignacion</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setCampanaNueva(false)}
                  className={`rounded-full px-4 py-2 text-sm font-medium ${
                    !campanaNueva ? 'bg-sky-600 text-white' : 'bg-white text-slate-700 ring-1 ring-sky-200'
                  }`}
                >
                  Normal
                </button>
                <button
                  type="button"
                  onClick={() => setCampanaNueva(true)}
                  className={`rounded-full px-4 py-2 text-sm font-medium ${
                    campanaNueva ? 'bg-sky-600 text-white' : 'bg-white text-slate-700 ring-1 ring-sky-200'
                  }`}
                >
                  Campana nueva (AD14=NEW)
                </button>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                className="inline-flex items-center rounded-full bg-sky-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-500"
                disabled={loading}
              >
                {loading ? 'Procesando...' : 'Generar ZIP BIT'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={resetForm}>
                Limpiar
              </button>
            </div>

            <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
              <p className="font-semibold text-slate-800">Salida</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li><code>CARGA BIT dd-mm-YYYY.xlsx</code></li>
                <li><code>Info_adi_dd-mm-yy.xlsx</code></li>
                <li>En campana nueva, se marca <code>AD14=NEW</code>.</li>
              </ul>
            </div>
          </form>
        </section>
      </div>
    </main>
  )
}

export default BitPage
