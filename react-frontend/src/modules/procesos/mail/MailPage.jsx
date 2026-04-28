import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import InlineAlert from '../../../components/InlineAlert'
import { mandantes, mailTemplates } from '../../../data/constants'
import { submitMailTemplate, downloadMailTemplateSample } from '../../../api/mail'
import { createCrmSession } from '../../../api/crm'
import { fetchProcessHistory } from '../../../api/reports'
import { triggerDownload, assertExcelResponse } from '../../../utils/download'
import useStatusMessage from '../../../hooks/useStatusMessage'

const initialTemplateState = {
  mandante_template: '',
  template_code: '',
}

function MailPage() {
  const navigate = useNavigate()
  const templateFileRef = useRef(null)

  const [templateForm, setTemplateForm] = useState(initialTemplateState)
  const { status, updateStatus, clearStatus } = useStatusMessage()
  const [crmSeedFile, setCrmSeedFile] = useState(null)
  const [historyRows, setHistoryRows] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [loadingTemplate, setLoadingTemplate] = useState(false)

  const filteredTemplates = useMemo(() => {
    if (!templateForm.mandante_template) return []
    return mailTemplates.filter(tpl => tpl.mandante === templateForm.mandante_template)
  }, [templateForm.mandante_template])

  const resetTemplateForm = () => {
    setTemplateForm(initialTemplateState)
    setCrmSeedFile(null)
    if (templateFileRef.current) templateFileRef.current.value = ''
  }

  const handleTemplateChange = e => {
    const { name, value } = e.target
    if (name === 'mandante_template') {
      setTemplateForm({ ...initialTemplateState, mandante_template: value })
      return
    }
    setTemplateForm(prev => ({ ...prev, [name]: value }))
  }

  const loadHistory = async () => {
    try {
      setHistoryLoading(true)
      const data = await fetchProcessHistory({ proceso: 'mail', limit: 20 })
      setHistoryRows(Array.isArray(data?.items) ? data.items : [])
    } catch {
      setHistoryRows([])
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

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
    const selectedFile = templateFileRef.current.files[0]
    formData.append('file', selectedFile)
    formData.append('mandante_template', templateForm.mandante_template)
    formData.append('template_code', templateForm.template_code)

    try {
      setLoadingTemplate(true)
      const response = await submitMailTemplate(formData)
      await assertExcelResponse(response, 'Error generando la plantilla.')
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'plantilla_mail.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Plantilla generada correctamente.')
      setCrmSeedFile(selectedFile)
      loadHistory()
    } catch (error) {
      updateStatus('danger', error?.message || 'Error generando la plantilla.')
    } finally {
      setLoadingTemplate(false)
    }
  }

  const formatHistoryDate = value => {
    if (!value) return '-'
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return String(value)
    return parsed.toLocaleString('es-CL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const handleContinueCrm = async () => {
    if (!crmSeedFile) {
      updateStatus('danger', 'Primero genera una plantilla para continuar en CRM.')
      return
    }
    try {
      setLoadingTemplate(true)
      const response = await createCrmSession({ file: crmSeedFile, mode: 'mail', source: 'mail_template' })
      if (response.status >= 400 || !response.data?.token) {
        throw new Error(response.data?.message || 'No se pudo crear la sesión de CRM.')
      }
      navigate(`/procesos/crm?token=${encodeURIComponent(response.data.token)}&mode=mail`)
    } catch (error) {
      updateStatus('danger', error?.message || 'No se pudo abrir CRM unificado.')
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

        {status.message && <InlineAlert variant={status.type} onDismiss={clearStatus}>{status.message}</InlineAlert>}

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
              <button
                type="button"
                className="rounded-full border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                onClick={handleContinueCrm}
                disabled={loadingTemplate || !crmSeedFile}
              >
                Continuar en CRM
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
          <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Historial de este proceso</h2>
              <p className="text-sm text-slate-600">Registros recientes generados desde Mail.</p>
            </div>
            <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={loadHistory} disabled={historyLoading}>
              {historyLoading ? 'Actualizando…' : 'Actualizar'}
            </button>
          </header>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="px-3 py-2 font-medium">Proceso</th>
                  <th className="px-3 py-2 font-medium">Mandante</th>
                  <th className="px-3 py-2 font-medium">Registros</th>
                  <th className="px-3 py-2 font-medium">Fecha creación</th>
                  <th className="px-3 py-2 font-medium">Archivo generado</th>
                </tr>
              </thead>
              <tbody>
                {historyRows.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-6 text-center text-slate-500">Aún no hay cargas registradas para Mail.</td>
                  </tr>
                ) : (
                  historyRows.map(item => (
                    <tr key={item.id} className="border-t border-slate-100">
                      <td className="px-3 py-2 font-semibold text-slate-900">{item.proceso || '-'}</td>
                      <td className="px-3 py-2 text-slate-600">{item.mandante || '-'}</td>
                      <td className="px-3 py-2 text-slate-600">{Number(item.registros || 0).toLocaleString('es-CL')}</td>
                      <td className="px-3 py-2 text-slate-600">{formatHistoryDate(item.fecha_creacion)}</td>
                      <td className="px-3 py-2 text-slate-600">{item.archivo || '-'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  )
}

export default MailPage
