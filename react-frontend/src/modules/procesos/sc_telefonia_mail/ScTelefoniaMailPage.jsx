import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import InlineAlert from '../../../components/InlineAlert'
import { fetchScTelefoniaMailExecutives, fetchScTelefoniaMailTemplates, submitScTelefoniaMail } from '../../../api/scTelefoniaMail'
import { assertExcelResponse, triggerDownload } from '../../../utils/download'

const fallbackTemplates = [
  { key: 'sc_telefonia_descuento_95008', label: 'SC_TELEFONIA_DESCUENTO_95008', requires_date: true },
  { key: 'sc_telefonia_medios_pago_96706', label: 'SC_TELEFONIA_MEDIOS_PAGO_96706' },
  { key: 'sc_telefonia_novacion_93500', label: 'SC_TELEFONIA_NOVACION_93500', requires_date: true, requires_executive: true },
]

function ScTelefoniaMailPage() {
  const fileRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [templates, setTemplates] = useState(fallbackTemplates)
  const [templateKey, setTemplateKey] = useState('sc_telefonia_descuento_95008')
  const [selectedDate, setSelectedDate] = useState('')
  const [executives, setExecutives] = useState([])
  const [executiveKey, setExecutiveKey] = useState('')
  const [status, setStatus] = useState({ type: 'info', message: '' })

  const selectedTemplate = templates.find(template => template.key === templateKey)
  const requiresDate = Boolean(selectedTemplate?.requires_date)
  const requiresExecutive = Boolean(selectedTemplate?.requires_executive)

  useEffect(() => {
    let ignore = false
    fetchScTelefoniaMailTemplates().then(response => {
      if (ignore || response.status >= 400 || !Array.isArray(response.data?.templates)) return
      if (response.data.templates.length > 0) {
        setTemplates(response.data.templates)
        setTemplateKey(response.data.templates[0].key)
      }
    }).catch(() => {})
    return () => { ignore = true }
  }, [])

  useEffect(() => {
    let ignore = false
    setExecutiveKey('')
    setExecutives([])
    if (!requiresExecutive) return () => { ignore = true }
    fetchScTelefoniaMailExecutives(templateKey).then(response => {
      if (ignore || response.status >= 400 || !Array.isArray(response.data?.executives)) return
      setExecutives(response.data.executives)
      if (response.data.executives.length > 0) {
        setExecutiveKey(response.data.executives[0].key)
      }
    }).catch(() => {})
    return () => { ignore = true }
  }, [templateKey, requiresExecutive])

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 6000)
    }
  }

  const resetForm = () => {
    if (fileRef.current) fileRef.current.value = ''
    setTemplateKey(templates[0]?.key || 'sc_telefonia_descuento_95008')
    setSelectedDate('')
    setExecutiveKey('')
  }

  const handleTemplateChange = (value) => {
    setTemplateKey(value)
    const template = templates.find(item => item.key === value)
    if (!template?.requires_date) setSelectedDate('')
    if (!template?.requires_executive) setExecutiveKey('')
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
    if (requiresDate && !selectedDate) {
      updateStatus('danger', 'Debes seleccionar la fecha.')
      return
    }
    if (requiresExecutive && !executiveKey) {
      updateStatus('danger', 'Debes seleccionar una ejecutiva.')
      return
    }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('template_key', templateKey)
    if (requiresDate) formData.append('selected_date', selectedDate)
    if (requiresExecutive) formData.append('executive_key', executiveKey)

    try {
      setLoading(true)
      const response = await submitScTelefoniaMail(formData)
      await assertExcelResponse(response, 'No se pudo generar el archivo Santander Consumer Telefonia.')
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'SC_TELEFONIA_MAIL.xlsx'
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
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Proceso Santander Consumer Telefonia</p>
            <h1 className="text-3xl font-semibold text-slate-900">Telefonia Mail - Excel desde BD</h1>
            <p className="mt-2 max-w-2xl text-slate-600">Sube operaciones y genera masividades consultando SQL Server en dbo.tmp_bench_temp_STC.</p>
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
                onChange={e => handleTemplateChange(e.target.value)}
                className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                required
              >
                {templates.map(template => (
                  <option key={template.key} value={template.key}>{template.label}</option>
                ))}
              </select>
            </div>

            {requiresDate && (
              <div>
                <label className="text-sm font-medium text-slate-700">Fecha</label>
                <input
                  type="date"
                  value={selectedDate}
                  onChange={e => setSelectedDate(e.target.value)}
                  className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                  required
                />
                <p className="mt-2 text-xs text-slate-500">Se escribira en DIA, MES y ANO.</p>
              </div>
            )}

            {requiresExecutive && (
              <div>
                <label className="text-sm font-medium text-slate-700">Ejecutiva</label>
                <select
                  value={executiveKey}
                  onChange={e => setExecutiveKey(e.target.value)}
                  className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                  required
                >
                  <option value="">Selecciona ejecutiva</option>
                  {executives.map(executive => (
                    <option key={executive.key} value={executive.key}>{executive.label}</option>
                  ))}
                </select>
                <p className="mt-2 text-xs text-slate-500">Se usa para mail_from, CORREO, EJECU y CORREO_EJE en Novacion.</p>
              </div>
            )}

            <div>
              <label className="text-sm font-medium text-slate-700">Archivo Excel de operaciones</label>
              <input
                ref={fileRef}
                type="file"
                accept=".xlsx,.xls"
                className="mt-1 block w-full rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm"
                required
              />
              <p className="mt-2 text-xs text-slate-500">Columnas aceptadas: OPERACION, operacion, operación, OP, NRO_OPERACION o N_OPERACION.</p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                className="inline-flex items-center rounded-full bg-emerald-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-500"
                disabled={loading}
              >
                {loading ? 'Procesando...' : 'Generar archivo'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={resetForm}>
                Limpiar
              </button>
            </div>
          </form>
        </section>

        <section className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <p className="font-semibold text-slate-800">Salida Santander Consumer Telefonia</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
            <li>Las operaciones se cruzan por fld_OPERACION en dbo.tmp_bench_temp_STC.</li>
            <li>Si una operación no existe, queda solo la operación y los datos SQL vacíos.</li>
            <li>Los campos fijos y semillas vienen desde config/sc_telefonia_mail_templates.json.</li>
            <li>Solo SC_TELEFONIA_MEDIOS_PAGO_96706 deduplica por RUT y dest_email.</li>
          </ul>
        </section>
      </div>
    </main>
  )
}

export default ScTelefoniaMailPage
