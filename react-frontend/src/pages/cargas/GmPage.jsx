import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../../components/InlineAlert'
import { submitGmProcess } from '../../api/gm'
import { triggerDownload } from '../../utils/download'

const initialSwitches = {
  comparar: false,
  masividades: false,
}

function GmPage() {
  const archivoRef = useRef(null)
  const archivoAnteriorRef = useRef(null)

  const [switches, setSwitches] = useState(initialSwitches)
  const [status, setStatus] = useState({ type: 'info', message: '' })
  const [loading, setLoading] = useState(false)

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 6000)
    }
  }

  const handleToggle = name => {
    setSwitches(prev => ({ ...prev, [name]: !prev[name] }))
    if (name === 'comparar' && archivoAnteriorRef.current) {
      archivoAnteriorRef.current.value = ''
    }
  }

  const extractErrorMessage = async (error, fallback) => {
    if (error?.response?.data instanceof Blob) {
      try {
        const text = await error.response.data.text()
        if (text) return text
      } catch (err) {
        console.error(err)
      }
    } else if (typeof error?.response?.data === 'string') {
      return error.response.data
    }
    return error?.message || fallback
  }

  const resetForm = () => {
    setSwitches(initialSwitches)
    if (archivoRef.current) archivoRef.current.value = ''
    if (archivoAnteriorRef.current) archivoAnteriorRef.current.value = ''
  }

  const handleSubmit = async e => {
    e.preventDefault()
    const archivo = archivoRef.current?.files?.[0]
    const archivoAnterior = archivoAnteriorRef.current?.files?.[0]

    if (!archivo) {
      updateStatus('danger', 'Debes subir el archivo Collection (nuevo).')
      return
    }
    if (switches.comparar && !archivoAnterior) {
      updateStatus('danger', 'Activaste comparación; sube el archivo anterior.')
      return
    }

    const formData = new FormData()
    formData.append('archivo', archivo)
    if (switches.comparar) {
      formData.append('habilitar_comparacion', 'on')
      formData.append('archivo_anterior', archivoAnterior)
    }
    if (switches.masividades) {
      formData.append('habilitar_masividades', 'on')
    }

    try {
      setLoading(true)
      const response = await submitGmProcess(formData)
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'Procesamiento_GM.zip'
      triggerDownload(response.data, filename)
      updateStatus('success', 'ZIP generado correctamente.')
    } catch (error) {
      const message = await extractErrorMessage(error, 'Error procesando el archivo.')
      updateStatus('danger', message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 px-4 py-8">
      <div className="mx-auto max-w-4xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Carga General Motors</p>
            <h1 className="text-3xl font-semibold text-slate-900">Procesar Collection</h1>
            <p className="mt-2 max-w-2xl text-slate-600">Mantuvimos la misma lógica Flask: puedes comparar archivos y anexar masividades al ZIP.</p>
          </div>
          <Link to="/cargas" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-6">
            <h2 className="text-xl font-semibold text-slate-900">Parámetros</h2>
            <p className="text-sm text-slate-600">Activa las opciones que necesites antes de subir los archivos.</p>
          </header>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3">
                <input type="checkbox" className="h-5 w-5 rounded border-slate-300" checked={switches.comparar} onChange={() => handleToggle('comparar')} />
                <div>
                  <span className="font-semibold text-slate-900">Activar comparación</span>
                  <p className="text-sm text-slate-500">Requiere archivo anterior para detectar campañas nuevas.</p>
                </div>
              </label>
              <label className="flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3">
                <input type="checkbox" className="h-5 w-5 rounded border-slate-300" checked={switches.masividades} onChange={() => handleToggle('masividades')} />
                <div>
                  <span className="font-semibold text-slate-900">Activar masividades</span>
                  <p className="text-sm text-slate-500">Agrega la plantilla de masividad dentro del ZIP.</p>
                </div>
              </label>
            </div>

            <div>
              <label className="text-sm font-medium text-slate-700">Archivo Collection (nuevo)</label>
              <input ref={archivoRef} type="file" accept=".xlsx,.xls" className="mt-1 block w-full rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm" required />
              <p className="mt-2 text-xs text-slate-500">Formato original de Collection; se corrigen columnas campana_1..5 automáticamente.</p>
            </div>

            {switches.comparar && (
              <div>
                <label className="text-sm font-medium text-slate-700">Archivo anterior (para comparación)</label>
                <input ref={archivoAnteriorRef} type="file" accept=".xlsx,.xls" className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required={switches.comparar} />
                <p className="mt-2 text-xs text-slate-500">Se usa para detectar campañas nuevas y generar Excel adicional.</p>
              </div>
            )}

            <div className="flex flex-wrap gap-3">
              <button type="submit" className="inline-flex items-center rounded-full bg-amber-500 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-amber-400" disabled={loading}>
                {loading ? 'Procesando…' : 'Procesar archivo'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={resetForm}>
                Limpiar campos
              </button>
            </div>

            <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
              <p className="font-semibold text-slate-800">Notas</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li>Las columnas campana_1 a campana_5 se crean si faltan.</li>
                <li>Números se normalizan (reemplazo de comas/puntos) igual que en Flask.</li>
                <li>Si activas comparación se genera un Excel adicional con campañas nuevas.</li>
                <li>Masividades añade la plantilla al ZIP sin alterar el procesamiento principal.</li>
              </ul>
            </div>
          </form>
        </section>
      </div>
    </main>
  )
}

export default GmPage
