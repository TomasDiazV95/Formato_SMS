import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import InlineAlert from '../../../components/InlineAlert'
import { fetchGmMailTemplates, submitGmMail } from '../../../api/gmMail'
import { ZIP_MIME, assertExcelResponse, triggerDownload } from '../../../utils/download'

const fallbackTemplates = [
  { key: 'gm_comercial_84995', label: 'GM_COMERCIAL_84995', filename_prefix: 'GM_COMERCIAL_84995' },
  { key: 'gm_extension_84591', label: 'GM_EXTENSION_84591', filename_prefix: 'GM_EXTENSION_84591', requires_delivery_date: true },
  { key: 'gm_descuento_98960', label: 'GM_DESCUENTO_98960', filename_prefix: 'GM_DESCUENTO_98960', requires_delivery_date: true, date_field: 'FECHA_VALIDA', date_label: 'Fecha maxima oferta' },
]

function GmMailPage() {
  const fileRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [templates, setTemplates] = useState(fallbackTemplates)
  const [templateKey, setTemplateKey] = useState('gm_comercial_84995')
  const [deliveryDate, setDeliveryDate] = useState('')
  const [includeCrm, setIncludeCrm] = useState(false)
  const [crmDate, setCrmDate] = useState('')
  const [crmStartTime, setCrmStartTime] = useState('10:00')
  const [crmEndTime, setCrmEndTime] = useState('18:00')
  const [status, setStatus] = useState({ type: 'info', message: '' })

  const selectedTemplate = templates.find(template => template.key === templateKey)
  const requiresDeliveryDate = Boolean(selectedTemplate?.requires_delivery_date)
  const dateLabel = selectedTemplate?.date_label || 'Fecha entrega'
  const dateField = selectedTemplate?.date_field || 'FECHA_ENTREGA'

  useEffect(() => {
    let ignore = false
    fetchGmMailTemplates().then(response => {
      if (ignore || response.status >= 400 || !Array.isArray(response.data?.templates)) return
      if (response.data.templates.length > 0) {
        setTemplates(response.data.templates)
        setTemplateKey(response.data.templates[0].key)
      }
    }).catch(() => {})
    return () => { ignore = true }
  }, [])

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 6000)
    }
  }

  const resetForm = () => {
    if (fileRef.current) fileRef.current.value = ''
    setTemplateKey(templates[0]?.key || 'gm_comercial_84995')
    setDeliveryDate('')
    setIncludeCrm(false)
    setCrmDate('')
    setCrmStartTime('10:00')
    setCrmEndTime('18:00')
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
    if (requiresDeliveryDate && !deliveryDate) {
      updateStatus('danger', 'Debes seleccionar la fecha de entrega.')
      return
    }
    if (includeCrm && (!crmDate || !crmStartTime || !crmEndTime)) {
      updateStatus('danger', 'Debes completar fecha, hora inicio y hora fin para CRM.')
      return
    }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('template_key', templateKey)
    if (requiresDeliveryDate) {
      formData.append('delivery_date', deliveryDate)
    }
    if (includeCrm) {
      formData.append('include_crm', 'on')
      formData.append('crm_fecha', crmDate)
      formData.append('crm_hora_inicio', crmStartTime)
      formData.append('crm_hora_fin', crmEndTime)
    }

    try {
      setLoading(true)
      const response = await submitGmMail(formData)
      await assertExcelResponse(response, 'No se pudo generar el archivo GM Mail.', includeCrm ? [ZIP_MIME] : [])
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'GM_COMERCIAL_84995.xlsx'
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
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Proceso General Motors</p>
            <h1 className="text-3xl font-semibold text-slate-900">GM Mail - Excel desde BD</h1>
            <p className="mt-2 max-w-2xl text-slate-600">Sube un Excel con operaciones y genera la masividad consultando SQL Server en dbo.tmp_asig_gm.</p>
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
                onChange={e => {
                  const value = e.target.value
                  setTemplateKey(value)
                  const template = templates.find(item => item.key === value)
                  if (!template?.requires_delivery_date) {
                    setDeliveryDate('')
                  }
                }}
                className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                required
              >
                {templates.map(template => (
                  <option key={template.key} value={template.key}>{template.label}</option>
                ))}
              </select>
            </div>

            {requiresDeliveryDate && (
              <div>
                <label className="text-sm font-medium text-slate-700">{dateLabel}</label>
                <input
                  type="date"
                  value={deliveryDate}
                  onChange={e => setDeliveryDate(e.target.value)}
                  className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                  required
                />
                <p className="mt-2 text-xs text-slate-500">Se escribira en {dateField} con formato DD-MM-YYYY.</p>
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
              <p className="mt-2 text-xs text-slate-500">Columnas aceptadas: OPERACION, operacion, operación, OPERACIÓN, OP u op.</p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-4">
              <label className="flex items-center gap-3 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={includeCrm}
                  onChange={e => setIncludeCrm(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300"
                />
                Generar archivo CRM Mail junto con la plantilla
              </label>
              <p className="mt-2 text-xs text-slate-500">Usuario CRM fijo: jriveros. Observacion fija: ENVIO MAIL.</p>

              {includeCrm && (
                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <div>
                    <label className="text-sm font-medium text-slate-700">Fecha gestion</label>
                    <input
                      type="date"
                      value={crmDate}
                      onChange={e => setCrmDate(e.target.value)}
                      className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                      required={includeCrm}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-slate-700">Hora inicio</label>
                    <input
                      type="time"
                      value={crmStartTime}
                      onChange={e => setCrmStartTime(e.target.value)}
                      className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                      required={includeCrm}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-slate-700">Hora fin</label>
                    <input
                      type="time"
                      value={crmEndTime}
                      onChange={e => setCrmEndTime(e.target.value)}
                      className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                      required={includeCrm}
                    />
                  </div>
                </div>
              )}
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
          <p className="font-semibold text-slate-800">Salida GM Mail</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
            <li>Las operaciones se cruzan por [fld_Agreement Number] en SQL Server.</li>
            <li>Si una operación no existe en la tabla, se conserva OPERACION y el resto de datos SQL queda vacío.</li>
            <li>Los campos fijos vienen desde config/gm_mail_templates.json.</li>
            <li>Las plantillas con fecha adicional solicitan datepicker y la escriben como DD-MM-YYYY.</li>
            <li>Se quitan RUT y correos duplicados conservando la primera fila encontrada.</li>
            <li>Si activas CRM, se descarga un ZIP con plantilla GM, carga CRM XLSX y carga CRM CSV.</li>
          </ul>
        </section>
      </div>
    </main>
  )
}

export default GmMailPage
