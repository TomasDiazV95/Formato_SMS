import { useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../../../components/InlineAlert'
import { mandantes, mailTemplates } from '../../../data/constants'
import { submitMailTemplate, downloadMailTemplateSample } from '../../../api/mail'
import { triggerDownload, assertExcelResponse, ZIP_MIME } from '../../../utils/download'

const initialTemplateState = {
  mandante_template: '',
  template_code: '',
}

const mailCrmRules = {
  'Itau Vencida': { usuario: 'VDAD', observacion: 'ENVIO SIN RESPUESTA' },
  'Itau Castigo': { usuario: 'VDAD', observacion: 'ENVIO SIN RESPUESTA' },
  'Banco Internacional': { usuario: 'VDAD', observacion: '' },
  'La Araucana': { usuario: 'VDAD', observacion: '' },
  Tanner: { usuario: 'VDAD', observacion: '' },
  'Santander Consumer Judicial': { usuario: 'jriveros', observacion: '' },
  'General Motors': { usuario: 'jriveros', observacion: 'ENVIO MAIL' },
}

function MailPage() {
  const templateFileRef = useRef(null)

  const [templateForm, setTemplateForm] = useState(initialTemplateState)
  const [status, setStatus] = useState({ type: 'info', message: '' })
  const [includeCrm, setIncludeCrm] = useState(false)
  const [templateDate, setTemplateDate] = useState('')
  const [crmDate, setCrmDate] = useState('')
  const [crmStartTime, setCrmStartTime] = useState('10:00')
  const [crmEndTime, setCrmEndTime] = useState('18:00')
  const [loadingTemplate, setLoadingTemplate] = useState(false)

  const crmRule = mailCrmRules[templateForm.mandante_template]
  const crmDisabled = !crmRule
  const requiresTemplateDate = templateForm.template_code === 'ARAUCANA_ALTERNATIVAS_PAGO_86256'

  const filteredTemplates = useMemo(() => {
    if (!templateForm.mandante_template) return []
    return mailTemplates.filter(tpl => tpl.mandante === templateForm.mandante_template)
  }, [templateForm.mandante_template])

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 6000)
    }
  }

  const resetTemplateForm = () => {
    setTemplateForm(initialTemplateState)
    setIncludeCrm(false)
    setTemplateDate('')
    setCrmDate('')
    setCrmStartTime('10:00')
    setCrmEndTime('18:00')
    if (templateFileRef.current) templateFileRef.current.value = ''
  }

  const handleTemplateChange = e => {
    const { name, value } = e.target
    if (name === 'mandante_template') {
      setTemplateForm({ ...initialTemplateState, mandante_template: value })
      setIncludeCrm(false)
      setTemplateDate('')
      return
    }
    if (name === 'template_code' && value !== 'ARAUCANA_ALTERNATIVAS_PAGO_86256') {
      setTemplateDate('')
    }
    setTemplateForm(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmitTemplate = async e => {
    e.preventDefault()
    if (!templateFileRef.current?.files?.[0]) {
      updateStatus('danger', 'Debes adjuntar un Excel para generar la plantilla.')
      return
    }
    if (!templateForm.mandante_template) {
      updateStatus('danger', 'Selecciona un mandante.')
      return
    }
    if (!templateForm.template_code) {
      updateStatus('danger', 'Selecciona la plantilla a generar.')
      return
    }
    if (requiresTemplateDate && !templateDate) {
      updateStatus('danger', 'Debes indicar FECHA_VCTO para La Araucana Alternativas de Pago.')
      return
    }
    if (includeCrm && crmDisabled) {
      updateStatus('danger', 'Este mandante no sube CRM desde el modulo Mail.')
      return
    }
    if (includeCrm && (!crmDate || !crmStartTime || !crmEndTime)) {
      updateStatus('danger', 'Debes indicar fecha, hora inicio y hora fin para generar CRM.')
      return
    }

    const formData = new FormData()
    formData.append('file', templateFileRef.current.files[0])
    formData.append('mandante_template', templateForm.mandante_template)
    formData.append('template_code', templateForm.template_code)
    if (requiresTemplateDate) {
      formData.append('template_fecha', templateDate)
    }
    if (includeCrm) {
      formData.append('include_crm', 'on')
      formData.append('crm_fecha', crmDate)
      formData.append('crm_hora_inicio', crmStartTime)
      formData.append('crm_hora_fin', crmEndTime)
    }

    try {
      setLoadingTemplate(true)
      const response = await submitMailTemplate(formData)
      await assertExcelResponse(response, 'Error generando la plantilla.', [ZIP_MIME])
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'plantilla_mail.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', includeCrm ? 'Plantilla y CRM generados correctamente.' : 'Plantilla generada correctamente.')
      resetTemplateForm()
    } catch (error) {
      updateStatus('danger', error?.message || 'Error generando la plantilla.')
    } finally {
      setLoadingTemplate(false)
    }
  }

  const handleTemplateSample = async () => {
    if (!templateForm.mandante_template || !templateForm.template_code) {
      updateStatus('danger', 'Selecciona mandante y plantilla para descargar el ejemplo.')
      return
    }
    try {
      const response = await downloadMailTemplateSample(templateForm.template_code)
      await assertExcelResponse(response, 'No se pudo descargar el ejemplo de plantilla.')
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'ejemplo_mail_template.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Ejemplo de plantilla descargado correctamente.')
    } catch (error) {
      updateStatus('danger', error?.message || 'No se pudo descargar el ejemplo de plantilla.')
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Proceso Mail</p>
            <h1 className="text-3xl font-semibold text-slate-900">Plantillas Mail</h1>
            <p className="mt-2 max-w-2xl text-slate-600">La lógica del backend se mantiene intacta; solo modernizamos la interfaz para generar las mismas salidas XLSX.</p>
          </div>
          <Link to="/procesos" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="rounded-3xl bg-white/90 p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-6 space-y-2">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Generador de Plantillas</h2>
                <p className="text-sm text-slate-600">Sube la base y selecciona mandante + plantilla. El archivo conserva columnas completas gracias al backend.</p>
              </div>
              <div className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600">mail/template</div>
            </div>
            <p className="text-xs text-slate-500">Se usan los mismos mapeos flexibles definidos en services/mail_templates.py.</p>
          </header>

          <form className="space-y-5" onSubmit={handleSubmitTemplate}>
            <div>
              <label className="text-sm font-medium text-slate-700">Archivo Excel Base</label>
              <input ref={templateFileRef} type="file" accept=".xlsx,.xls" className="mt-1 block w-full rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm" required />
              <p className="mt-2 text-xs text-slate-500">Incluye columnas RUT/DV, operación, correo destino y datos del agente.</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-slate-700">Mandante</label>
                <select
                  name="mandante_template"
                  value={templateForm.mandante_template}
                  onChange={handleTemplateChange}
                  className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                  required
                >
                  <option value="">Selecciona mandante</option>
                  {mandantes.map(item => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Plantilla</label>
                <select
                  name="template_code"
                  value={templateForm.template_code}
                  onChange={handleTemplateChange}
                  className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                  disabled={!templateForm.mandante_template}
                  required
                >
                  <option value="">Selecciona plantilla</option>
                  {filteredTemplates.map(tpl => (
                    <option key={tpl.code} value={tpl.code}>{`${tpl.label} (ID ${tpl.messageId})`}</option>
                  ))}
                </select>
                {!filteredTemplates.length && templateForm.mandante_template && (
                  <p className="mt-2 text-xs text-amber-600">No hay plantillas registradas para este mandante.</p>
                )}
              </div>
            </div>

            {requiresTemplateDate && (
              <div>
                <label className="text-sm font-medium text-slate-700">FECHA_VCTO</label>
                <input
                  type="date"
                  value={templateDate}
                  onChange={e => setTemplateDate(e.target.value)}
                  className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                  required={requiresTemplateDate}
                />
                <p className="mt-2 text-xs text-slate-500">Se escribira en la columna FECHA_VCTO con formato DD-MM-YYYY.</p>
              </div>
            )}

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <label className="inline-flex items-center gap-2 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={includeCrm}
                  onChange={e => setIncludeCrm(e.target.checked)}
                  disabled={crmDisabled}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                Generar archivo CRM junto con Mail
              </label>
              {crmRule && <p className="mt-2 text-xs text-slate-500">Usuario CRM fijo: {crmRule.usuario}. Observacion fija: {crmRule.observacion || 'vacia'}.</p>}
              {!crmRule && templateForm.mandante_template && <p className="mt-2 text-xs text-amber-600">Este mandante no sube CRM desde el modulo Mail.</p>}
              {includeCrm && (
                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <div>
                    <label className="text-xs font-medium text-slate-600">Fecha gestion</label>
                    <input type="date" value={crmDate} onChange={e => setCrmDate(e.target.value)} className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required={includeCrm} />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-600">Hora inicio</label>
                    <input type="time" value={crmStartTime} onChange={e => setCrmStartTime(e.target.value)} className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required={includeCrm} />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-600">Hora fin</label>
                    <input type="time" value={crmEndTime} onChange={e => setCrmEndTime(e.target.value)} className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required={includeCrm} />
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-wrap gap-3">
              <button type="submit" className="inline-flex items-center rounded-full bg-indigo-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500" disabled={loadingTemplate}>
                {loadingTemplate ? 'Procesando…' : 'Generar plantilla'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={resetTemplateForm}>
                Limpiar campos
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600 disabled:opacity-60" onClick={handleTemplateSample} disabled={!templateForm.template_code}>
                Descargar ejemplo
              </button>
            </div>

            <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
              <p className="font-semibold text-slate-800">Notas rápidas</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li>El campo mail_from para Tanner se obtiene de REENVIADORES AGENTES.xlsx.</li>
                <li>La columna TELEFONO del agente se normaliza automáticamente.</li>
                <li>El layout final sigue el orden INSTITUCIÓN, message_id, RUT+DV, operación, destino, agente.</li>
              </ul>
            </div>
          </form>
        </section>

      </div>
    </main>
  )
}

export default MailPage
