import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import InlineAlert from '../../components/InlineAlert'
import { submitSantanderConsumerTerreno } from '../../api/santanderConsumer'
import { santanderConsumerTemplates } from '../../data/santanderConsumerTemplates'
import { assertExcelResponse, triggerDownload } from '../../utils/download'

function SantanderConsumerPage() {
  const fileRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [templateKey, setTemplateKey] = useState('')
  const [status, setStatus] = useState({ type: 'info', message: '' })

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 6000)
    }
  }

  const resetForm = () => {
    if (fileRef.current) fileRef.current.value = ''
    setTemplateKey('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file) {
      updateStatus('danger', 'Debes subir un archivo Excel con operaciones.')
      return
    }
    if (!templateKey) {
      updateStatus('danger', 'Debes seleccionar una plantilla.')
      return
    }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('template_key', templateKey)

    try {
      setLoading(true)
      const response = await submitSantanderConsumerTerreno(formData)
      await assertExcelResponse(response, 'No se pudo generar el archivo Santander Consumer Terreno.')
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'Santander_Consumer_Terreno.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Archivo generado correctamente.')
    } catch (error) {
      updateStatus('danger', error?.message || 'No se pudo procesar el archivo.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 px-4 py-8">
      <div className="mx-auto max-w-4xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Proceso Santander Consumer</p>
            <h1 className="text-3xl font-semibold text-slate-900">Terreno - Excel desde BD</h1>
            <p className="mt-2 max-w-2xl text-slate-600">Sube un Excel con operaciones y genera un archivo base consultando SQL Server en dbo.tmp_bench_STC.</p>
          </div>
          <Link to="/procesos" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="text-sm font-medium text-slate-700">Plantilla</label>
              <select
                value={templateKey}
                onChange={e => setTemplateKey(e.target.value)}
                className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                required
              >
                <option value="">Selecciona una plantilla</option>
                {santanderConsumerTemplates.map(template => (
                  <option key={template.key} value={template.key}>
                    {`${template.label} (message_id ${template.messageId})`}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-slate-500">Para 3 cuotas y 2 cuotas se usa el mismo message_id (90818) y cambia NRO_CUOTAS.</p>
            </div>

            <div>
              <label className="text-sm font-medium text-slate-700">Archivo Excel de operaciones</label>
              <input
                ref={fileRef}
                type="file"
                accept=".xlsx,.xls"
                className="mt-1 block w-full rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm"
                required
              />
              <p className="mt-2 text-xs text-slate-500">Columnas aceptadas: OPERACION, NRO_OPERACION, NUM_OP, OP, ID_CREDITO.</p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                className="inline-flex items-center rounded-full bg-emerald-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-500"
                disabled={loading}
              >
                {loading ? 'Procesando…' : 'Generar archivo'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={resetForm}>
                Limpiar
              </button>
            </div>
          </form>
        </section>

        <section className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <p className="font-semibold text-slate-800">Salida base</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
            <li>Columnas iniciales: INSTITUCIÓN, SEGMENTOINSTITUCIÓN, message_id y NRO_CUOTAS.</li>
            <li>Luego: OPERACION_INPUT, ENCONTRADO_DB, RUT, dest_email, NRO_OPERACION, CLIENTE, name_from, EJECUTIVO, mail_from, CORREO, CELULAR, MARCA, PATENTE, OFERTA A PAGO, COMUNA, REGION, FECHA_FUENTE y al final MES_CURSO, ANO_CURSO, DIA_OFERTA, MES_OFERTA, ANO_OFERTA.</li>
            <li>Si una operación no existe en la tabla, se marca ENCONTRADO_DB = NO y se dejan campos vacíos.</li>
            <li>El archivo se descarga automáticamente cuando finaliza el proceso.</li>
          </ul>
        </section>
      </div>
    </main>
  )
}

export default SantanderConsumerPage
