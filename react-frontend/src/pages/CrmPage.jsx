import { useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import InlineAlert from '../components/InlineAlert'
import { mandantes } from '../data/constants'
import { submitCrmCarga } from '../api/crm'
import { triggerDownload, assertExcelResponse, ZIP_MIME } from '../utils/download'

const initialFormState = {
  fecha: '',
  hora_inicio: '',
  hora_fin: '',
  usuario: '',
  observacion: '',
}

function CrmPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const token = (searchParams.get('token') || '').trim()
  const modeParam = (searchParams.get('mode') || '').trim().toLowerCase()

  const fileRef = useRef(null)
  const [mode, setMode] = useState(modeParam === 'mail' ? 'mail' : 'sms_ivr')
  const [form, setForm] = useState(initialFormState)
  const [mandanteSalida, setMandanteSalida] = useState('')
  const [intervalo, setIntervalo] = useState('')
  const [multiUsuarios, setMultiUsuarios] = useState(false)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState({ type: 'info', message: '' })

  const hasSession = token.length > 0
  const modeLabel = mode === 'mail' ? 'Mail' : 'SMS/IVR'

  const requiresUsuario = useMemo(() => {
    if (mode === 'mail') return true
    return !multiUsuarios
  }, [mode, multiUsuarios])

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 6000)
    }
  }

  const handleChange = event => {
    const { name, value } = event.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  const handleModeChange = event => {
    const nextMode = event.target.value
    setMode(nextMode)
    const next = new URLSearchParams(searchParams)
    next.set('mode', nextMode)
    setSearchParams(next, { replace: true })
  }

  const handleSubmit = async event => {
    event.preventDefault()

    if (!hasSession && !fileRef.current?.files?.[0]) {
      updateStatus('danger', 'Debes subir un archivo manual o llegar con sesión precargada.')
      return
    }
    if (requiresUsuario && !form.usuario.trim()) {
      updateStatus('danger', 'Debes indicar usuario para generar la carga CRM.')
      return
    }
    if (!mandanteSalida) {
      updateStatus('danger', 'Debes seleccionar mandante para nombrar el archivo de salida.')
      return
    }

    const formData = new FormData()
    formData.append('mode', mode)
    formData.append('mandante_salida', mandanteSalida)
    if (token) formData.append('token', token)
    if (!hasSession && fileRef.current?.files?.[0]) formData.append('file', fileRef.current.files[0])
    Object.entries(form).forEach(([key, value]) => formData.append(key, value))
    if (intervalo) formData.append('intervalo', intervalo)
    if (mode === 'sms_ivr' && multiUsuarios) formData.append('multi_usuarios', 'on')

    try {
      setLoading(true)
      const response = await submitCrmCarga(formData)
      const allowZip = mode === 'sms_ivr' && multiUsuarios
      await assertExcelResponse(response, 'Error generando la carga CRM unificada.', allowZip ? [ZIP_MIME] : [])
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'carga_crm.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', `Carga CRM ${modeLabel} generada correctamente.`)
    } catch (error) {
      updateStatus('danger', error?.message || 'Error generando la carga CRM.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Proceso CRM</p>
            <h1 className="text-3xl font-semibold text-slate-900">CRM unificado Mail / SMS-IVR</h1>
            <p className="mt-2 max-w-2xl text-slate-600">Puedes continuar desde una sesión precargada o subir archivo manual para generar la carga final.</p>
          </div>
          <Link to="/procesos" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-6 space-y-2">
            <h2 className="text-xl font-semibold text-slate-900">Generador CRM</h2>
            {hasSession ? (
              <p className="text-sm text-emerald-700">Sesión precargada activa. Se usará el archivo del proceso previo.</p>
            ) : (
              <p className="text-sm text-slate-600">Sin sesión precargada: debes adjuntar un archivo.</p>
            )}
          </header>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-slate-700">Modo CRM</label>
                <select value={mode} onChange={handleModeChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm">
                  <option value="sms_ivr">SMS/IVR</option>
                  <option value="mail">Mail</option>
                </select>
                {mode === 'mail' && (
                  <p className="mt-1 text-xs text-slate-500">La opción Múltiples usuarios aplica solo para modo SMS/IVR.</p>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Archivo base</label>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  className="mt-1 block w-full rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm disabled:bg-slate-50"
                  required={!hasSession}
                  disabled={hasSession}
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-slate-700">Mandante (nombre de salida)</label>
                <select value={mandanteSalida} onChange={event => setMandanteSalida(event.target.value)} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required>
                  <option value="">Selecciona mandante</option>
                  {mandantes.map(item => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-slate-500">Este campo solo afecta el nombre del archivo final descargado.</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="text-sm font-medium text-slate-700">Fecha de gestión</label>
                <input type="date" name="fecha" value={form.fecha} onChange={handleChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Hora inicio</label>
                <input type="time" name="hora_inicio" value={form.hora_inicio} onChange={handleChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Hora fin</label>
                <input type="time" name="hora_fin" value={form.hora_fin} onChange={handleChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="text-sm font-medium text-slate-700">Usuario CRM</label>
                <input
                  type="text"
                  name="usuario"
                  value={form.usuario}
                  onChange={handleChange}
                  className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm disabled:bg-slate-50"
                  required={requiresUsuario}
                  disabled={mode === 'sms_ivr' && multiUsuarios}
                  placeholder={mode === 'sms_ivr' && multiUsuarios ? 'Se toma desde Excel' : 'Ej: jriveros'}
                />
                {mode === 'sms_ivr' && (
                  <label className="mt-2 flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 px-3 py-2 text-sm text-slate-600">
                    <input
                      type="checkbox"
                      className="h-5 w-5 rounded border-slate-300"
                      checked={multiUsuarios}
                      onChange={event => setMultiUsuarios(event.target.checked)}
                    />
                    <span>Múltiples usuarios</span>
                  </label>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Observación</label>
                <input type="text" name="observacion" value={form.observacion} onChange={handleChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" placeholder="Opcional" />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Intervalo (seg)</label>
                <input type="number" min="1" value={intervalo} onChange={event => setIntervalo(event.target.value)} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" placeholder="Vacío = automático" />
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button type="submit" className="inline-flex items-center rounded-full bg-indigo-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500" disabled={loading}>
                {loading ? 'Procesando…' : 'Generar CRM'}
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  )
}

export default CrmPage
