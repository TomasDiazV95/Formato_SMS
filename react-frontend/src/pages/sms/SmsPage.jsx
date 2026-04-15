import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { mandantes, formatoSalida } from '../../data/constants'
import { submitSmsMasivo, submitSmsCrm, downloadSmsSample } from '../../api/sms'
import { triggerDownload, assertExcelResponse, ZIP_MIME } from '../../utils/download'
import InlineAlert from '../../components/InlineAlert'

const initialMasivoState = {
  mensaje: '',
  tipo_salida: '',
  mandante: '',
}

const initialCrmState = {
  fecha: '',
  hora_inicio: '',
  hora_fin: '',
  usuario: '',
  observacion: '',
}

function SmsPage() {
  const [masivoData, setMasivoData] = useState(initialMasivoState)
  const [crmData, setCrmData] = useState(initialCrmState)
  const [intervaloCrm, setIntervaloCrm] = useState('')
  const [mensajesPersonalizados, setMensajesPersonalizados] = useState(false)
  const [multiUsuarios, setMultiUsuarios] = useState(false)
  const [status, setStatus] = useState({ type: 'info', message: '' })
  const [loading, setLoading] = useState(false)
  const masivoFileRef = useRef(null)
  const crmFileRef = useRef(null)

  const updateStatus = (type, message) => {
    setStatus({ type, message })
    if (message) {
      setTimeout(() => setStatus({ type: 'info', message: '' }), 6000)
    }
  }

  const handleMasivoChange = e => {
    const { name, value } = e.target
    setMasivoData(prev => ({ ...prev, [name]: value }))
  }

  const handleCrmChange = e => {
    const { name, value } = e.target
    setCrmData(prev => ({ ...prev, [name]: value }))
  }

  const handleSampleDownload = async type => {
    try {
      const blob = await downloadSmsSample(type)
      triggerDownload(blob, `ejemplo_SMS_${type}.xlsx`)
    } catch (err) {
      updateStatus('danger', err.message || 'No se pudo descargar el ejemplo.')
    }
  }

  const handleSubmitMasivo = async e => {
    e.preventDefault()
    if (!masivoFileRef.current?.files?.[0]) {
      updateStatus('danger', 'Debes adjuntar un archivo Excel para masividad SMS.')
      return
    }

    const formData = new FormData()
    formData.append('file', masivoFileRef.current.files[0])
    formData.append('mensaje', masivoData.mensaje)
    formData.append('tipo_salida', masivoData.tipo_salida)
    formData.append('mandante', masivoData.mandante)
    if (mensajesPersonalizados) formData.append('mensajes_personalizados', 'on')

    try {
      setLoading(true)
      const response = await submitSmsMasivo(formData)
      await assertExcelResponse(response, 'Error generando la carga SMS.')
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'masivo_sms.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Archivo generado correctamente.')
    } catch (err) {
      const message = err?.message || err?.response?.data || 'Error generando el archivo.'
      updateStatus('danger', message)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitCrm = async e => {
    e.preventDefault()
    if (!crmFileRef.current?.files?.[0]) {
      updateStatus('danger', 'Debes adjuntar un archivo Excel para la carga CRM.')
      return
    }

    const formData = new FormData()
    formData.append('file', crmFileRef.current.files[0])
    Object.entries(crmData).forEach(([key, value]) => formData.append(key, value))
    if (intervaloCrm) formData.append('intervalo', intervaloCrm)
    if (multiUsuarios) formData.append('multiples_usuarios', 'on')

    try {
      setLoading(true)
      const response = await submitSmsCrm(formData)
      await assertExcelResponse(response, 'Error generando la carga CRM.', multiUsuarios ? [ZIP_MIME] : [])
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'crm_sms.xlsx'
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
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Proceso SMS</p>
            <h1 className="text-3xl font-semibold text-slate-900">Masividades Athenas / AXIA</h1>
            <p className="mt-2 max-w-2xl text-slate-600">
              Este módulo consume los mismos endpoints de Flask. Adjunta el Excel de origen y selecciona el mandante correspondiente.
            </p>
          </div>
          <Link to="/procesos" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-6">
            <h2 className="text-xl font-semibold text-slate-900">Generador Athenas / AXIA</h2>
            <p className="text-sm text-slate-600">Genera el layout con mandante, mensaje y formato seleccionados.</p>
          </header>
          <form className="space-y-4" onSubmit={handleSubmitMasivo}>
            <div>
              <label className="text-sm font-medium text-slate-700">Archivo Excel Base</label>
              <input ref={masivoFileRef} type="file" accept=".xlsx,.xls" className="mt-1 block w-full rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm" required />
              <p className="mt-2 text-xs text-slate-500">Debe contener columnas RUT, OP y FONO.</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-slate-700">Mensaje SMS</label>
                <input
                  name="mensaje"
                  value={masivoData.mensaje}
                  onChange={handleMasivoChange}
                  type="text"
                  className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm disabled:bg-slate-50"
                  placeholder={mensajesPersonalizados ? 'Se tomará desde el Excel' : 'Ej: Hola! Te contactamos por...'}
                  required={!mensajesPersonalizados}
                  disabled={mensajesPersonalizados}
                />
                <label className="mt-2 flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 px-3 py-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    className="h-5 w-5 rounded border-slate-300"
                    checked={mensajesPersonalizados}
                    onChange={e => setMensajesPersonalizados(e.target.checked)}
                  />
                  <span>Mensajes personalizados</span>
                </label>
                {mensajesPersonalizados && (
                  <p className="mt-1 text-xs text-slate-500">Incluye una columna MENSAJE en tu Excel para usar un texto distinto por fila. Las filas vacías usarán el primer mensaje disponible.</p>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Mandante</label>
                <select name="mandante" value={masivoData.mandante} onChange={handleMasivoChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required>
                  <option value="">Selecciona mandante</option>
                  {mandantes.map(item => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-slate-700">Formato de salida</label>
                <select name="tipo_salida" value={masivoData.tipo_salida} onChange={handleMasivoChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required>
                  <option value="">Selecciona formato</option>
                  {formatoSalida.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end gap-2">
                <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600 transition hover:border-slate-300" onClick={() => handleSampleDownload('ATHENAS')}>
                  Ejemplo Athenas
                </button>
                <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600 transition hover:border-slate-300" onClick={() => handleSampleDownload('AXIA')}>
                  Ejemplo AXIA
                </button>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button className="inline-flex items-center rounded-full bg-indigo-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500" type="submit" disabled={loading}>
                {loading ? 'Procesando…' : 'Generar archivo'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={() => {
                setMasivoData(initialMasivoState)
                setMensajesPersonalizados(false)
                if (masivoFileRef.current) masivoFileRef.current.value = ''
              }}>
                Limpiar campos
              </button>
            </div>
          </form>
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-6">
            <h2 className="text-xl font-semibold text-slate-900">Carga CRM</h2>
            <p className="text-sm text-slate-600">Distribuye registros cada 5 segundos o según el intervalo definido.</p>
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
                <label className="text-sm font-medium text-slate-700">Usuario CRM</label>
                <input
                  type="text"
                  name="usuario"
                  value={crmData.usuario}
                  onChange={handleCrmChange}
                  className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm disabled:bg-slate-50"
                  required={!multiUsuarios}
                  disabled={multiUsuarios}
                  placeholder={multiUsuarios ? 'Se tomará desde el Excel' : 'Ej: jriveros'}
                />
                <label className="mt-2 flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 px-3 py-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    className="h-5 w-5 rounded border-slate-300"
                    checked={multiUsuarios}
                    onChange={e => setMultiUsuarios(e.target.checked)}
                  />
                  <span>Multiples Usuarios</span>
                </label>
                {multiUsuarios && (
                  <p className="mt-1 text-xs text-slate-500">Incluye una columna USUARIO_CRM/USUARIO/AGENTE en el Excel para generar un archivo por usuario y descargar un ZIP.</p>
                )}
               </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Observación</label>
                <input type="text" name="observacion" value={crmData.observacion} onChange={handleCrmChange} className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" placeholder="Ej: SMS MASIVO" />
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
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={() => {
                setCrmData(initialCrmState)
                setIntervaloCrm('')
                setMultiUsuarios(false)
                if (crmFileRef.current) crmFileRef.current.value = ''
              }}>
                Limpiar campos
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  )
}

export default SmsPage
