import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../../../components/InlineAlert'
import { submitTannerProcess } from '../../../api/tanner'
import { assertExcelResponse, triggerDownload } from '../../../utils/download'
import useStatusMessage from '../../../hooks/useStatusMessage'

function TannerPage() {
  const archivoRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const { status, updateStatus, clearStatus } = useStatusMessage()

  const resetForm = () => {
    if (archivoRef.current) archivoRef.current.value = ''
  }

  const handleSubmit = async e => {
    e.preventDefault()
    const archivo = archivoRef.current?.files?.[0]
    if (!archivo) {
      updateStatus('danger', 'Debes subir el archivo base de asignacion Tanner.')
      return
    }

    const formData = new FormData()
    formData.append('archivo', archivo)

    try {
      setLoading(true)
      const response = await submitTannerProcess(formData)
      await assertExcelResponse(response, 'No se pudo generar la asignacion Tanner.')
      const fallback = 'ASIGNACION_TANNER.xlsx'
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || fallback
      triggerDownload(response.data, filename)
      updateStatus('success', 'Asignacion Tanner generada correctamente.')
    } catch (error) {
      updateStatus('danger', error?.message || 'Error procesando la asignacion Tanner.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-amber-50 via-stone-50 to-zinc-100 px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-8">
        <section className="relative overflow-hidden rounded-3xl border border-amber-200 bg-white p-8 shadow-sm">
          <div className="pointer-events-none absolute -right-16 -top-14 h-52 w-52 rounded-full bg-amber-200/60 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-16 -left-20 h-56 w-56 rounded-full bg-stone-200/70 blur-3xl" />
          <div className="relative flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.32em] text-amber-700">Carga Tanner</p>
              <h1 className="mt-2 text-3xl font-semibold text-slate-900">Asignacion CRM</h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-600">
                Sube la base y genera el layout de asignacion Tanner siguiendo la automatizacion validada.
              </p>
            </div>
            <Link to="/cargas" className="rounded-full border border-amber-200 px-4 py-2 text-sm text-amber-700 transition hover:bg-amber-50">
              ← Volver
            </Link>
          </div>
        </section>

        {status.message && <InlineAlert variant={status.type} onDismiss={clearStatus}>{status.message}</InlineAlert>}

        <section className="rounded-3xl border border-amber-100 bg-white p-6 shadow-sm">
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="text-sm font-medium text-slate-700">Archivo base Tanner</label>
              <input
                ref={archivoRef}
                type="file"
                accept=".xlsx,.xls"
                className="mt-1 block w-full rounded-2xl border border-dashed border-amber-300 px-4 py-3 text-sm"
                required
              />
              <p className="mt-2 text-xs text-slate-500">Se genera un único archivo: <code>ASIGNACION_TANNER_dd-mm-yy.xlsx</code>.</p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                className="inline-flex items-center rounded-full bg-amber-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-amber-500"
                disabled={loading}
              >
                {loading ? 'Procesando...' : 'Generar asignacion'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={resetForm}>
                Limpiar
              </button>
            </div>

            <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
              <p className="font-semibold text-slate-800">Reglas aplicadas</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li><code>Nro_Documento</code> desde <code>ID_CREDITO</code>.</li>
                <li><code>NombreProducto</code> desde <code>TRAMO_INI</code> con fallback <code>SIN MARCA</code>.</li>
                <li><code>AD3</code> conserva el valor textual original de <code>TRAMO_INI</code>.</li>
                <li>Mapeo de contacto y judicial según archivo de automatización Tanner.</li>
              </ul>
            </div>
          </form>
        </section>
      </div>
    </main>
  )
}

export default TannerPage
