import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { submitDireccionesDepurador } from '../../../api/depuradores'
import InlineAlert from '../../../components/InlineAlert'
import { assertExcelResponse, triggerDownload } from '../../../utils/download'

function DireccionesDepuradorPage() {
  const archivoRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState({ type: 'info', message: '' })

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message && type !== 'danger') {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 7000)
    }
  }

  const resetForm = () => {
    if (archivoRef.current) archivoRef.current.value = ''
  }

  const handleSubmit = async event => {
    event.preventDefault()
    const archivo = archivoRef.current?.files?.[0]
    if (!archivo) {
      updateStatus('danger', 'Debes subir un archivo Excel con direcciones.')
      return
    }

    const formData = new FormData()
    formData.append('archivo', archivo)

    try {
      setLoading(true)
      const response = await submitDireccionesDepurador(formData)
      await assertExcelResponse(response, 'No se pudo depurar el archivo de direcciones.')
      const fallback = 'DIRECCIONES_DEPURADAS.xlsx'
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || fallback
      triggerDownload(response.data, filename)
      updateStatus('success', 'Direcciones depuradas correctamente.')
    } catch (error) {
      updateStatus('danger', error?.message || 'Error depurando direcciones.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-8">
        <section className="rounded-3xl border border-cyan-100 bg-white p-8 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.32em] text-cyan-700">Depuradores</p>
              <h1 className="mt-2 text-3xl font-semibold text-slate-900">Depurador de Direcciones</h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-600">
                Sube una base con RUT y DIRECCION para generar un Excel limpio, sin duplicados claros y con campos separados.
              </p>
            </div>
            <Link to="/depuradores" className="rounded-full border border-cyan-200 px-4 py-2 text-sm text-cyan-700 transition hover:bg-cyan-50">
              Volver
            </Link>
          </div>
        </section>

        {status.message && (
          <InlineAlert variant={status.type}>
            {status.message}
          </InlineAlert>
        )}

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="text-sm font-medium text-slate-700">Archivo origen de direcciones</label>
              <input
                ref={archivoRef}
                type="file"
                accept=".xlsx,.xls"
                className="mt-1 block w-full rounded-2xl border border-dashed border-cyan-300 px-4 py-3 text-sm"
                required
              />
              <p className="mt-2 text-xs text-slate-500">Columnas minimas: RUT y DIRECCION. Usa DV, NUMERO, COMUNA y CIUDAD si vienen en el archivo.</p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                className="inline-flex items-center rounded-full bg-cyan-700 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-cyan-600"
                disabled={loading}
              >
                {loading ? 'Depurando...' : 'Depurar direcciones'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={resetForm}>
                Limpiar
              </button>
            </div>

            <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
              <p className="font-semibold text-slate-800">Salida generada</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li>Entrega solo las columnas RUT, DV, RUT+DV, NOMBRE, DIRECCION, NUMERO, COMUNA y CIUDAD.</li>
                <li>Separa numero, comuna y ciudad cuando esos datos vienen dentro de la direccion.</li>
                <li>Usa reglas internas para elegir la version mas completa cuando hay duplicados.</li>
              </ul>
            </div>
          </form>
        </section>
      </div>
    </main>
  )
}

export default DireccionesDepuradorPage
