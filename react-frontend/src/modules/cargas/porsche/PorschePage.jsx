import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../../../components/InlineAlert'
import { submitPorscheProcess } from '../../../api/porsche'
import { assertExcelResponse, triggerDownload } from '../../../utils/download'
import useStatusMessage from '../../../hooks/useStatusMessage'

function PorschePage() {
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
      updateStatus('danger', 'Debes subir el archivo base de asignacion Porsche.')
      return
    }

    const formData = new FormData()
    formData.append('archivo', archivo)

    try {
      setLoading(true)
      const response = await submitPorscheProcess(formData)
      await assertExcelResponse(response, 'No se pudo generar la asignacion Porsche.')
      const fallback = 'ASIGNACION_PORSCHE.xlsx'
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || fallback
      triggerDownload(response.data, filename)
      updateStatus('success', 'Asignacion Porsche generada correctamente.')
    } catch (error) {
      updateStatus('danger', error?.message || 'Error procesando la asignacion Porsche.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-zinc-950 via-zinc-900 to-zinc-800 px-4 py-8 text-zinc-100">
      <div className="mx-auto max-w-5xl space-y-8">
        <section className="relative overflow-hidden rounded-3xl border border-zinc-700/60 bg-zinc-900/70 p-8 shadow-2xl">
          <div className="pointer-events-none absolute -right-16 -top-16 h-52 w-52 rounded-full bg-red-600/30 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-white/5 blur-3xl" />
          <div className="relative flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.32em] text-zinc-400">Carga Porsche</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-wide text-white">Asignacion CRM</h1>
              <p className="mt-2 max-w-2xl text-sm text-zinc-300">
                Sube la base mensual y genera el archivo final de asignacion con el layout oficial.
              </p>
            </div>
            <Link to="/cargas" className="rounded-full border border-zinc-600 px-4 py-2 text-sm text-zinc-200 transition hover:bg-zinc-800">
              ← Volver
            </Link>
          </div>

          <div className="relative mt-6 rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-xs text-zinc-300">
            <span className="font-semibold text-red-400">PORSCHE</span>
            <span className="mx-2 text-zinc-500">|</span>
            Archivo esperado con encabezado real en fila de {'"N° Contrato"'}.
          </div>
        </section>

        {status.message && <InlineAlert variant={status.type} onDismiss={clearStatus}>{status.message}</InlineAlert>}

        <section className="rounded-3xl border border-zinc-700/70 bg-zinc-900/90 p-6 shadow-xl">
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="text-sm font-medium text-zinc-100">Archivo base Asignacion Porsche</label>
              <input
                ref={archivoRef}
                type="file"
                accept=".xlsx,.xls"
                className="mt-2 block w-full rounded-2xl border border-dashed border-zinc-500 bg-zinc-950 px-4 py-3 text-sm text-zinc-200"
                required
              />
              <p className="mt-2 text-xs text-zinc-400">
                El sistema detecta automaticamente la fila de encabezado y genera <code>ASIGNACION_PORSCHE_dd-mm-yy.xlsx</code>.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                className="inline-flex items-center rounded-full bg-red-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-red-500"
                disabled={loading}
              >
                {loading ? 'Procesando...' : 'Generar asignacion'}
              </button>
              <button
                type="button"
                className="rounded-full border border-zinc-600 px-4 py-2 text-sm text-zinc-200"
                onClick={resetForm}
              >
                Limpiar
              </button>
            </div>

            <div className="rounded-2xl bg-zinc-950/70 p-4 text-sm text-zinc-300">
              <p className="font-semibold text-white">Reglas aplicadas</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li>Deteccion robusta de encabezado buscando {'"N° Contrato"'}.</li>
                <li>Mapeo al formato CRM de Porsche (columnas AD y contacto).</li>
                <li>NombreProducto fijo en <code>AUTOMOTRIZ</code>.</li>
                <li>Limpieza final en modo texto para evitar celdas vacias.</li>
              </ul>
            </div>
          </form>
        </section>
      </div>
    </main>
  )
}

export default PorschePage
