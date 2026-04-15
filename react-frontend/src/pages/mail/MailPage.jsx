import { useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../../components/InlineAlert'
import { mandantes, mailTemplates } from '../../data/constants'
import { submitMailTemplate, submitMailCrm, downloadMailTemplateSample, downloadMailCrmSample } from '../../api/mail'
import { triggerDownload, assertExcelResponse } from '../../utils/download'

const initialTemplateState = {
  mandante_template: '',
  template_code: '',
}

const initialCrmState = {
  fecha: '',
  hora_inicio: '',
  hora_fin: '',
  usuario: '',
  observacion: '',
}

function MailPage() {
  const templateFileRef = useRef(null)
  const crmFileRef = useRef(null)

  const [templateForm, setTemplateForm] = useState(initialTemplateState)
  const [crmForm, setCrmForm] = useState(initialCrmState)
  const [intervalo, setIntervalo] = useState('')
  const [status, setStatus] = useState({ type: 'info', message: '' })
  const [loadingTemplate, setLoadingTemplate] = useState(false)
  const [loadingCrm, setLoadingCrm] = useState(false)

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
    if (templateFileRef.current) templateFileRef.current.value = ''
  }

  const resetCrmForm = () => {
    setCrmForm(initialCrmState)
    setIntervalo('')
    if (crmFileRef.current) crmFileRef.current.value = ''
  }

  const handleTemplateChange = e => {
    const { name, value } = e.target
    if (name === 'mandante_template') {
      setTemplateForm({ ...initialTemplateState, mandante_template: value })
      return
    }
    setTemplateForm(prev => ({ ...prev, [name]: value }))
  }

  const handleCrmChange = e => {
    const { name, value } = e.target
    setCrmForm(prev => ({ ...prev, [name]: value }))
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

    const formData = new FormData()
    formData.append('file', templateFileRef.current.files[0])
    formData.append('mandante_template', templateForm.mandante_template)
    formData.append('template_code', templateForm.template_code)

    try {
      setLoadingTemplate(true)
      const response = await submitMailTemplate(formData)
      await assertExcelResponse(response, 'Error generando la plantilla.')
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'plantilla_mail.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Plantilla generada correctamente.')
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

  const handleCrmSample = async () => {
    try {
      const response = await downloadMailCrmSample()
      await assertExcelResponse(response, 'No se pudo descargar el ejemplo CRM.')
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'ejemplo_MAIL_CRM.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Ejemplo CRM descargado correctamente.')
    } catch (error) {
      updateStatus('danger', error?.message || 'No se pudo descargar el ejemplo CRM.')
    }
  }

  const handleSubmitCrm = async e => {
    e.preventDefault()
    if (!crmFileRef.current?.files?.[0]) {
      updateStatus('danger', 'Debes adjuntar un Excel para la carga CRM.')
      return
    }

    const formData = new FormData()
    formData.append('file', crmFileRef.current.files[0])
    Object.entries(crmForm).forEach(([key, value]) => formData.append(key, value))
    if (intervalo) formData.append('intervalo', intervalo)

    try {
      setLoadingCrm(true)
      const response = await submitMailCrm(formData)
      await assertExcelResponse(response, 'Error generando la carga CRM.')
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'carga_MAIL_CRM.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Carga CRM generada correctamente.')
    } catch (error) {
      updateStatus('danger', error?.message || 'Error generando la carga CRM.')
    } finally {
      setLoadingCrm(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Proceso Mail</p>
            <h1 className="text-3xl font-semibold text-slate-900">Plantillas y CRM</h1>
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

        <section className="rounded-3xl bg-white/90 p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-6 space-y-2">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Carga Mail CRM</h2>
                <p className="text-sm text-slate-600">Agenda envíos masivos respetando fecha, horario e intervalo programado.</p>
              </div>
              <div className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-600">mail/crm</div>
            </div>
            <p className="text-xs text-slate-500">La lógica es la misma de services/mail_service.build_mail_crm_output.</p>
          </header>

          <form className="space-y-5" onSubmit={handleSubmitCrm}>
            <div>
              <label className="text-sm font-medium text-slate-700">Archivo Excel Base</label>
              <input ref={crmFileRef} type="file" accept=".xlsx,.xls" className="mt-1 block w-full rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm" required />
              <p className="mt-2 text-xs text-slate-500">Debe incluir al menos columnas RUT, OPERACION y MAIL del cliente (EMAIL/DEST_EMAIL). Los correos de agentes no sirven.</p>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="text-sm font-medium text-slate-700">Fecha de gestión</label>
                <input type="date" name="fecha" value={crmForm.fecha} onChange={handleCrmChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Hora inicio</label>
                <input type="time" name="hora_inicio" value={crmForm.hora_inicio} onChange={handleCrmChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Hora fin</label>
                <input type="time" name="hora_fin" value={crmForm.hora_fin} onChange={handleCrmChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="text-sm font-medium text-slate-700">Usuario CRM</label>
                <input type="text" name="usuario" value={crmForm.usuario} onChange={handleCrmChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" placeholder="Ej: jriveros" required />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Observación</label>
                <input type="text" name="observacion" value={crmForm.observacion} onChange={handleCrmChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" placeholder="Opcional" />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Intervalo (seg)</label>
                <input type="number" min="1" value={intervalo} onChange={e => setIntervalo(e.target.value)} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" placeholder="Vacío = 5s" />
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button type="submit" className="inline-flex items-center rounded-full bg-emerald-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-500" disabled={loadingCrm}>
                {loadingCrm ? 'Procesando…' : 'Generar CRM'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={resetCrmForm}>
                Limpiar campos
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={handleCrmSample}>
                Descargar ejemplo CRM
              </button>
            </div>

            <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
              <p className="font-semibold text-slate-800">Formato de salida</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li>Columnas: RUT, NRO_DOCUMENTO, FECHA_GESTION (YYYY-MM-DD HH:MM:SS), TELEFONO (vacío), OBSERVACION, USUARIO, CORREO.</li>
                <li>El intervalo funciona igual que en SMS/IVR: por defecto 5s entre registros, o el valor que definas.</li>
                <li>El archivo se descargará como carga_MAIL_CRM_dd-mm.xlsx.</li>
              </ul>
            </div>
          </form>
        </section>
      </div>
    </main>
  )
}

export default MailPage
