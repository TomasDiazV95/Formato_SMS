import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../../components/InlineAlert'
import { mandantes } from '../../data/constants'
import { campo1Options } from '../../data/ivrOptions'
import { downloadIvrSample, submitIvrAthenas, submitIvrCrm } from '../../api/ivr'
import { triggerDownload, assertExcelResponse, ZIP_MIME } from '../../utils/download'

const initialIvrState = {
  mandante: '',
  campo1: '',
}

const initialCrmState = {
  fecha: '',
  hora_inicio: '',
  hora_fin: '',
  usuario: '',
  observacion: '',
}

function IvrPage() {
  const [ivrData, setIvrData] = useState(initialIvrState)
  const [crmData, setCrmData] = useState(initialCrmState)
  const [intervaloCrm, setIntervaloCrm] = useState('')
  const [autoUsuarios, setAutoUsuarios] = useState(false)
  const [status, setStatus] = useState({ type: 'info', message: '' })
  const [loading, setLoading] = useState(false)

  const ivrFileRef = useRef(null)
  const crmFileRef = useRef(null)

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 6000)
    }
  }

  const handleIvrChange = e => {
    const { name, value } = e.target
    setIvrData(prev => ({ ...prev, [name]: value }))
  }

  const handleCrmChange = e => {
    const { name, value } = e.target
    setCrmData(prev => ({ ...prev, [name]: value }))
  }

  const handleSample = async () => {
    try {
      const blob = await downloadIvrSample()
      triggerDownload(blob, 'ejemplo_IVR.xlsx')
    } catch (err) {
      updateStatus('danger', err.message || 'No se pudo descargar el ejemplo IVR.')
    }
  }

  const handleSubmitIvr = async e => {
    e.preventDefault()
    if (!ivrFileRef.current?.files?.[0]) {
      updateStatus('danger', 'Debes adjuntar un archivo Excel para la carga IVR.')
      return
    }
    const formData = new FormData()
    formData.append('file', ivrFileRef.current.files[0])
    formData.append('mandante', ivrData.mandante)
    formData.append('campo1', ivrData.campo1)
    try {
      setLoading(true)
      const response = await submitIvrAthenas(formData)
      await assertExcelResponse(response, 'Error generando la carga IVR.')
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'carga_IVR.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Carga IVR generada correctamente.')
    } catch (err) {
      const message = err?.message || err?.response?.data || 'Error generando la carga IVR.'
      updateStatus('danger', message)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitCrm = async e => {
    e.preventDefault()
    if (!crmFileRef.current?.files?.[0]) {
      updateStatus('danger', 'Debes adjuntar un archivo para la carga CRM.')
      return
    }
    const formData = new FormData()
    formData.append('file', crmFileRef.current.files[0])
    Object.entries(crmData).forEach(([key, value]) => formData.append(key, value))
    if (intervaloCrm) formData.append('intervalo', intervaloCrm)
    if (autoUsuarios) formData.append('usar_usuarios_archivo', 'on')
    try {
      setLoading(true)
      const response = await submitIvrCrm(formData)
      await assertExcelResponse(response, 'Error generando la carga CRM.', autoUsuarios ? [ZIP_MIME] : [])
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'carga_IVR_CRM.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Carga CRM generada correctamente.')
    } catch (err) {
      const message = err?.message || err?.response?.data || 'Error generando la carga CRM.'
      updateStatus('danger', message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Proceso IVR</p>
            <h1 className="text-3xl font-semibold text-slate-900">Cargas IVR Athenas / CRM</h1>
            <p className="mt-2 max-w-2xl text-slate-600">Sube la base y selecciona el CAMPO1 que corresponde a cada mandante.</p>
          </div>
          <Link to="/procesos" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-6">
            <h2 className="text-xl font-semibold text-slate-900">Carga IVR (Athenas)</h2>
            <p className="text-sm text-slate-600">Los archivos se generan con la misma lógica del backend actual.</p>
          </header>
          <form className="space-y-4" onSubmit={handleSubmitIvr}>
            <div>
              <label className="text-sm font-medium text-slate-700">Archivo Excel Base</label>
              <input ref={ivrFileRef} type="file" accept=".xlsx,.xls" className="mt-1 block w-full rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm" required />
              <p className="mt-2 text-xs text-slate-500">Debe contener columnas Telefóno, RUT/OP y opcionalmente nombre.</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-slate-700">Mandante</label>
                <select name="mandante" value={ivrData.mandante} onChange={handleIvrChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required>
                  <option value="">Selecciona mandante</option>
                  {mandantes.map(item => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">CAMPO1</label>
                <select name="campo1" value={ivrData.campo1} onChange={handleIvrChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required>
                  <option value="">Seleccione CAMPO1</option>
                  {campo1Options.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button className="inline-flex items-center rounded-full bg-indigo-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500" type="submit" disabled={loading}>
                {loading ? 'Procesando…' : 'Generar archivo'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={() => {
                setIvrData(initialIvrState)
                if (ivrFileRef.current) ivrFileRef.current.value = ''
              }}>
                Limpiar campos
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={handleSample}>
                Descargar ejemplo
              </button>
            </div>
          </form>
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-6">
            <h2 className="text-xl font-semibold text-slate-900">Carga IVR CRM</h2>
            <p className="text-sm text-slate-600">Define fechas, horarios e intervalo; el backend seguirá distribuyendo cada registro.</p>
          </header>
          <form className="space-y-4" onSubmit={handleSubmitCrm}>
            <div>
              <label className="text-sm font-medium text-slate-700">Archivo Excel Base</label>
              <input ref={crmFileRef} type="file" accept=".xlsx,.xls" className="mt-1 block w-full rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm" required />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="text-sm font-medium text-slate-700">Fecha de gestión</label>
                <input type="date" name="fecha" value={crmData.fecha} onChange={handleCrmChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Hora inicio</label>
                <input type="time" name="hora_inicio" value={crmData.hora_inicio} onChange={handleCrmChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Hora fin</label>
                <input type="time" name="hora_fin" value={crmData.hora_fin} onChange={handleCrmChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="text-sm font-medium text-slate-700">Usuario</label>
                <input
                  type="text"
                  name="usuario"
                  value={crmData.usuario}
                  onChange={handleCrmChange}
                  className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm disabled:bg-slate-50"
                  required={!autoUsuarios}
                  disabled={autoUsuarios}
                  placeholder={autoUsuarios ? 'Se tomará desde el Excel' : 'Ej: jriveros'}
                />
                <label className="mt-2 flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 px-3 py-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    className="h-5 w-5 rounded border-slate-300"
                    checked={autoUsuarios}
                    onChange={e => setAutoUsuarios(e.target.checked)}
                  />
                  <span>Múltiples Usuarios</span>
                </label>
                {autoUsuarios && (
                  <p className="mt-1 text-xs text-slate-500">Incluye una columna USUARIO_CRM/USUARIO/AGENTE en el Excel para dividir las cargas y descargar un ZIP con un archivo por usuario.</p>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Observación</label>
                <input type="text" name="observacion" value={crmData.observacion} onChange={handleCrmChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" placeholder="Ej: IVR" />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Intervalo (seg)</label>
                <input type="number" min="1" value={intervaloCrm} onChange={e => setIntervaloCrm(e.target.value)} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" placeholder="Opcional" />
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button className="inline-flex items-center rounded-full bg-indigo-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500" type="submit" disabled={loading}>
                {loading ? 'Procesando…' : 'Generar CRM'}
              </button>
              <button
                type="button"
                className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600"
                onClick={() => {
                  setCrmData(initialCrmState)
                  setIntervaloCrm('')
                  setAutoUsuarios(false)
                  if (crmFileRef.current) crmFileRef.current.value = ''
                }}
              >
                Limpiar campos
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  )
}

export default IvrPage
