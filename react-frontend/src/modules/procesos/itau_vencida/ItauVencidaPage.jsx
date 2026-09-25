import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import InlineAlert from '../../../components/InlineAlert'
import { submitItauVencida } from '../../../api/itauVencida'
import { ZIP_MIME, assertExcelResponse, triggerDownload } from '../../../utils/download'

const initialTimes = {
  start: '10:00',
  end: '18:00',
}

function ItauVencidaPage() {
  const fileRef = useRef(null)
  const [tipoSalida, setTipoSalida] = useState('')
  const [includeCrmSms, setIncludeCrmSms] = useState(false)
  const [includeCrmMail, setIncludeCrmMail] = useState(false)
  const [crmSmsDate, setCrmSmsDate] = useState('')
  const [crmSmsStart, setCrmSmsStart] = useState(initialTimes.start)
  const [crmSmsEnd, setCrmSmsEnd] = useState(initialTimes.end)
  const [crmMailDate, setCrmMailDate] = useState('')
  const [crmMailStart, setCrmMailStart] = useState(initialTimes.start)
  const [crmMailEnd, setCrmMailEnd] = useState(initialTimes.end)
  const [status, setStatus] = useState({ type: 'info', message: '' })
  const [loading, setLoading] = useState(false)

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 7000)
    }
  }

  const resetForm = () => {
    if (fileRef.current) fileRef.current.value = ''
    setTipoSalida('')
    setIncludeCrmSms(false)
    setIncludeCrmMail(false)
    setCrmSmsDate('')
    setCrmSmsStart(initialTimes.start)
    setCrmSmsEnd(initialTimes.end)
    setCrmMailDate('')
    setCrmMailStart(initialTimes.start)
    setCrmMailEnd(initialTimes.end)
  }

  const handleSubmit = async event => {
    event.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file) {
      updateStatus('danger', 'Debes subir el Excel de origen de ITAU VENCIDA.')
      return
    }
    if (!tipoSalida) {
      updateStatus('danger', 'Debes seleccionar el formato SMS AXIA o ATHENAS.')
      return
    }
    if (includeCrmSms && (!crmSmsDate || !crmSmsStart || !crmSmsEnd)) {
      updateStatus('danger', 'Debes completar fecha, hora inicio y hora fin para CRM SMS.')
      return
    }
    if (includeCrmMail && (!crmMailDate || !crmMailStart || !crmMailEnd)) {
      updateStatus('danger', 'Debes completar fecha, hora inicio y hora fin para CRM Mail.')
      return
    }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('tipo_salida', tipoSalida)
    if (includeCrmSms) {
      formData.append('include_crm_sms', 'on')
      formData.append('crm_sms_fecha', crmSmsDate)
      formData.append('crm_sms_hora_inicio', crmSmsStart)
      formData.append('crm_sms_hora_fin', crmSmsEnd)
    }
    if (includeCrmMail) {
      formData.append('include_crm_mail', 'on')
      formData.append('crm_mail_fecha', crmMailDate)
      formData.append('crm_mail_hora_inicio', crmMailStart)
      formData.append('crm_mail_hora_fin', crmMailEnd)
    }

    try {
      setLoading(true)
      const response = await submitItauVencida(formData)
      await assertExcelResponse(response, 'No se pudo generar ITAU VENCIDA.', [ZIP_MIME])
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'ITAU_VENCIDA.zip'
      triggerDownload(response.data, filename)
      updateStatus('success', 'ZIP ITAU VENCIDA generado correctamente.')
      resetForm()
    } catch (error) {
      updateStatus('danger', error?.message || 'No se pudo procesar ITAU VENCIDA.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Proceso Itaú</p>
            <h1 className="text-3xl font-semibold text-slate-900">ITAU VENCIDA</h1>
            <p className="mt-2 max-w-3xl text-slate-600">
              Carga una base completa. El sistema detecta la hoja de masividad y genera SMS, Mail y CRM según los grupos presentes.
            </p>
          </div>
          <Link to="/procesos" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div>
              <label className="text-sm font-medium text-slate-700">Excel base de origen</label>
              <input
                ref={fileRef}
                type="file"
                accept=".xlsx,.xls"
                className="mt-1 block w-full rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm"
                required
              />
              <p className="mt-2 text-xs text-slate-500">
                Se busca automáticamente una hoja con MASIVIDAD o MASIVIDADES. La hoja DETALLE se ignora si no contiene esa estructura.
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-slate-700">Formato de salida SMS</label>
                <select
                  value={tipoSalida}
                  onChange={event => setTipoSalida(event.target.value)}
                  className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm"
                  required
                >
                  <option value="">Selecciona formato</option>
                  <option value="AXIA">AXIA</option>
                  <option value="ATHENAS">ATHENAS</option>
                </select>
              </div>
              <div className="rounded-2xl border border-indigo-100 bg-indigo-50/50 px-4 py-3 text-sm text-slate-700">
                <p className="font-semibold">SMS soportados</p>
                <p className="mt-1 text-xs text-slate-600">Morosidad, compromiso de pago, compromiso roto y campaña.</p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 p-4">
              <label className="flex items-center gap-3 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={includeCrmSms}
                  onChange={event => setIncludeCrmSms(event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300"
                />
                Generar CRM SMS consolidado
              </label>
              <p className="mt-2 text-xs text-slate-500">Incluye todos los grupos SMS presentes. Usuario: VDAD. Observacion: ENVIO SIN RESPUESTA.</p>
              {includeCrmSms && (
                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <div>
                    <label className="text-xs font-medium text-slate-600">Fecha gestion SMS</label>
                    <input type="date" value={crmSmsDate} onChange={event => setCrmSmsDate(event.target.value)} className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-600">Hora inicio SMS</label>
                    <input type="time" value={crmSmsStart} onChange={event => setCrmSmsStart(event.target.value)} className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-600">Hora fin SMS</label>
                    <input type="time" value={crmSmsEnd} onChange={event => setCrmSmsEnd(event.target.value)} className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
                  </div>
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-200 p-4">
              <label className="flex items-center gap-3 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={includeCrmMail}
                  onChange={event => setIncludeCrmMail(event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300"
                />
                Generar CRM Mail consolidado
              </label>
              <p className="mt-2 text-xs text-slate-500">Consolida los Mail 84824 y 100998 disponibles. Usuario: VDAD. Observacion: ENVIO SIN RESPUESTA.</p>
              {includeCrmMail && (
                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <div>
                    <label className="text-xs font-medium text-slate-600">Fecha gestion Mail</label>
                    <input type="date" value={crmMailDate} onChange={event => setCrmMailDate(event.target.value)} className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-600">Hora inicio Mail</label>
                    <input type="time" value={crmMailStart} onChange={event => setCrmMailStart(event.target.value)} className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-600">Hora fin Mail</label>
                    <input type="time" value={crmMailEnd} onChange={event => setCrmMailEnd(event.target.value)} className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-wrap gap-3">
              <button type="submit" className="inline-flex items-center rounded-full bg-indigo-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500" disabled={loading}>
                {loading ? 'Procesando...' : 'Generar ITAU VENCIDA'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={resetForm}>
                Limpiar
              </button>
            </div>
          </form>
        </section>

        <section className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <p className="font-semibold text-slate-800">Contenido del ZIP</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
            <li>Un SMS consolidado con cualquiera de los cuatro mensajes presentes.</li>
            <li>Mail 84824 y/o 100998 en archivos separados.</li>
            <li>CRM SMS y CRM Mail con rangos de fecha y hora independientes.</li>
            <li>AXIA conserva XLSX y CSV complementario, igual que el módulo SMS actual.</li>
          </ul>
        </section>
      </div>
    </main>
  )
}

export default ItauVencidaPage
