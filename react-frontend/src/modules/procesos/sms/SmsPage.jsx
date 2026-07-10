import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { mandantes, formatoSalida } from '../../../data/constants'
import { submitSmsMasivo, downloadSmsSample } from '../../../api/sms'
import { triggerDownload, assertExcelResponse, ZIP_MIME } from '../../../utils/download'
import InlineAlert from '../../../components/InlineAlert'

const initialMasivoState = {
  mensaje: '',
  tipo_salida: '',
  mandante: '',
}

const smsCrmRules = {
  'Itau Vencida': { usuario: 'VDAD', observacion: 'ENVIO SIN RESPUESTA' },
  'Itau Castigo': { usuario: 'VDAD', observacion: 'ENVIO SIN RESPUESTA' },
  'Banco Internacional': { usuario: 'VDAD', observacion: '' },
  'Santander Hipotecario': { usuario: 'VDAD', observacion: '' },
  'Santander Consumer Terreno': { usuario: 'jriveros', observacion: '' },
  'Santander Consumer Telefonía': { usuario: 'jriveros', observacion: '' },
  'Santander Consumer Judicial': { usuario: 'jriveros', observacion: '' },
  'General Motors': { usuario: 'jriveros', observacion: 'SMS' },
  'La Araucana': { usuario: 'VDAD', observacion: '' },
  Tanner: { usuario: 'VDAD', observacion: '' },
}

function SmsPage() {
  const [masivoData, setMasivoData] = useState(initialMasivoState)
  const [mensajesPersonalizados, setMensajesPersonalizados] = useState(false)
  const [itauCarterizado, setItauCarterizado] = useState(false)
  const [includeCrm, setIncludeCrm] = useState(false)
  const [crmDate, setCrmDate] = useState('')
  const [crmStartTime, setCrmStartTime] = useState('10:00')
  const [crmEndTime, setCrmEndTime] = useState('18:00')
  const [status, setStatus] = useState({ type: 'info', message: '' })
  const [loading, setLoading] = useState(false)
  const masivoFileRef = useRef(null)
  const crmRule = smsCrmRules[masivoData.mandante]
  const crmDisabled = masivoData.mandante === 'CAJA18' || !crmRule

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

  const handleSampleDownload = async type => {
    try {
      const blob = await downloadSmsSample(type)
      triggerDownload(blob, `ejemplo_SMS_${type}.xlsx`)
    } catch (err) {
      updateStatus('danger', err.message || 'No se pudo descargar el ejemplo.')
    }
  }

  const resetForm = () => {
    setMasivoData(initialMasivoState)
    setMensajesPersonalizados(false)
    setItauCarterizado(false)
    setIncludeCrm(false)
    setCrmDate('')
    setCrmStartTime('10:00')
    setCrmEndTime('18:00')
    if (masivoFileRef.current) masivoFileRef.current.value = ''
  }

  const handleSubmitMasivo = async e => {
    e.preventDefault()
    if (!masivoFileRef.current?.files?.[0]) {
      updateStatus('danger', 'Debes adjuntar un archivo Excel para masividad SMS.')
      return
    }
    if (includeCrm && crmDisabled) {
      updateStatus('danger', masivoData.mandante === 'CAJA18' ? 'CAJA18 no genera CRM desde SMS.' : 'No hay regla CRM configurada para este mandante.')
      return
    }
    if (includeCrm && (!crmDate || !crmStartTime || !crmEndTime)) {
      updateStatus('danger', 'Debes completar fecha, hora inicio y hora fin para CRM.')
      return
    }

    const formData = new FormData()
    formData.append('file', masivoFileRef.current.files[0])
    formData.append('mensaje', masivoData.mensaje)
    formData.append('tipo_salida', masivoData.tipo_salida)
    formData.append('mandante', masivoData.mandante)
    if (itauCarterizado) {
      formData.append('modo_carterizado_itau', 'on')
    }
    if (mensajesPersonalizados) formData.append('mensajes_personalizados', 'on')
    if (includeCrm) {
      formData.append('include_crm', 'on')
      formData.append('crm_fecha', crmDate)
      formData.append('crm_hora_inicio', crmStartTime)
      formData.append('crm_hora_fin', crmEndTime)
    }

    try {
      setLoading(true)
      const response = await submitSmsMasivo(formData)
      await assertExcelResponse(response, 'Error generando la carga SMS.', [ZIP_MIME])
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'masivo_sms.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Archivo generado correctamente.')
      resetForm()
    } catch (err) {
      const message = err?.message || err?.response?.data || 'Error generando el archivo.'
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
              Este módulo genera la carga SMS y opcionalmente entrega el CRM listo en el mismo ZIP.
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
                  placeholder={itauCarterizado ? 'Se usará la plantilla Itaú seleccionada' : mensajesPersonalizados ? 'Se tomará desde el Excel' : 'Ej: Hola! Te contactamos por...'}
                  required={!mensajesPersonalizados && !itauCarterizado}
                  disabled={mensajesPersonalizados || itauCarterizado}
                />
                <label className="mt-2 flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 px-3 py-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    className="h-5 w-5 rounded border-slate-300"
                    checked={mensajesPersonalizados}
                    onChange={e => {
                      if (itauCarterizado) return
                      setMensajesPersonalizados(e.target.checked)
                    }}
                    disabled={itauCarterizado}
                  />
                  <span>Mensajes personalizados</span>
                </label>
                {mensajesPersonalizados && (
                  <p className="mt-1 text-xs text-slate-500">Incluye una columna MENSAJE en tu Excel para usar un texto distinto por fila. Las filas vacías usarán el primer mensaje disponible.</p>
                )}
                <label className="mt-2 flex cursor-pointer items-center gap-3 rounded-2xl border border-indigo-100 bg-indigo-50/40 px-3 py-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    className="h-5 w-5 rounded border-slate-300"
                    checked={itauCarterizado}
                    onChange={e => {
                      const checked = e.target.checked
                      setItauCarterizado(checked)
                      setMasivoData(prev => ({
                        ...prev,
                        mandante: checked ? 'Itau Vencida' : prev.mandante,
                        mensaje: checked ? '' : prev.mensaje,
                      }))
                      if (checked) setMensajesPersonalizados(false)
                    }}
                  />
                  <span>Modo SMS Carterizado Itaú</span>
                </label>
                {itauCarterizado && (
                  <div className="mt-2 rounded-2xl border border-indigo-100 bg-white px-3 py-3">
                    <p className="text-sm font-medium text-slate-700">Tipo de SMS automático por columna MASIVIDAD</p>
                    <p className="mt-1 text-xs text-slate-500">Valores esperados en MASIVIDAD: SMS MOROSIDAD, SMS COMPROMISO DE PAGO y SMS COMPROMISO ROTO. El mensaje final agrega el número del ejecutivo según CARTERIZADO.</p>
                  </div>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Mandante</label>
                <select
                  name="mandante"
                  value={masivoData.mandante}
                  onChange={handleMasivoChange}
                  className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm disabled:bg-slate-50"
                  required
                  disabled={itauCarterizado}
                >
                  <option value="">Selecciona mandante</option>
                  {mandantes.map(item => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
                {itauCarterizado && (
                  <p className="mt-2 text-xs text-slate-500">Modo fijo en Itau Vencida. Excel esperado: RUT, DV, OPERACION, NOMBRE DEL CLIENTE, CARTERIZADO y FONO.</p>
                )}
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
                resetForm()
              }}>
                Limpiar campos
              </button>
            </div>

            <div className="rounded-2xl border border-slate-200 p-4">
              <label className="flex items-center gap-3 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={includeCrm}
                  onChange={e => setIncludeCrm(e.target.checked)}
                  disabled={crmDisabled}
                  className="h-4 w-4 rounded border-slate-300"
                />
                Generar archivo CRM junto con SMS
              </label>
              {masivoData.mandante === 'CAJA18' && <p className="mt-2 text-xs text-amber-600">CAJA18 no genera CRM desde SMS.</p>}
              {crmRule && <p className="mt-2 text-xs text-slate-500">Usuario CRM fijo: {crmRule.usuario}. Observacion fija: {crmRule.observacion || 'vacia'}.</p>}
              {includeCrm && (
                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <div>
                    <label className="text-sm font-medium text-slate-700">Fecha gestion</label>
                    <input type="date" value={crmDate} onChange={e => setCrmDate(e.target.value)} className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required={includeCrm} />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-slate-700">Hora inicio</label>
                    <input type="time" value={crmStartTime} onChange={e => setCrmStartTime(e.target.value)} className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required={includeCrm} />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-slate-700">Hora fin</label>
                    <input type="time" value={crmEndTime} onChange={e => setCrmEndTime(e.target.value)} className="mt-1 block w-full rounded-2xl border border-slate-200 px-4 py-2 text-sm" required={includeCrm} />
                  </div>
                </div>
              )}
            </div>
          </form>
        </section>

      </div>
    </main>
  )
}

export default SmsPage
