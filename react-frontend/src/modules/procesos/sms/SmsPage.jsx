import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { mandantes, formatoSalida } from '../../../data/constants'
import { submitSmsMasivo, downloadSmsSample } from '../../../api/sms'
import { createCrmSession } from '../../../api/crm'
import { fetchProcessHistory } from '../../../api/reports'
import { triggerDownload, assertExcelResponse } from '../../../utils/download'
import InlineAlert from '../../../components/InlineAlert'
import useStatusMessage from '../../../hooks/useStatusMessage'

const initialMasivoState = {
  mensaje: '',
  tipo_salida: '',
  mandante: '',
}

function SmsPage() {
  const navigate = useNavigate()
  const [masivoData, setMasivoData] = useState(initialMasivoState)
  const [mensajesPersonalizados, setMensajesPersonalizados] = useState(false)
  const [itauCarterizado, setItauCarterizado] = useState(false)
  const { status, updateStatus, clearStatus } = useStatusMessage()
  const [crmSeedFile, setCrmSeedFile] = useState(null)
  const [historyRows, setHistoryRows] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [loading, setLoading] = useState(false)
  const masivoFileRef = useRef(null)

  const handleMasivoChange = e => {
    const { name, value } = e.target
    setMasivoData(prev => ({ ...prev, [name]: value }))
  }

  const loadHistory = async () => {
    try {
      setHistoryLoading(true)
      const data = await fetchProcessHistory({ proceso: 'sms', limit: 20 })
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
    const selectedFile = masivoFileRef.current.files[0]

    const formData = new FormData()
    formData.append('file', masivoFileRef.current.files[0])
    formData.append('mensaje', masivoData.mensaje)
    formData.append('tipo_salida', masivoData.tipo_salida)
    formData.append('mandante', masivoData.mandante)
    if (itauCarterizado) {
      formData.append('modo_carterizado_itau', 'on')
    }
    if (mensajesPersonalizados) formData.append('mensajes_personalizados', 'on')

    try {
      setLoading(true)
      const response = await submitSmsMasivo(formData)
      await assertExcelResponse(response, 'Error generando la carga SMS.')
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'masivo_sms.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Archivo generado correctamente.')
      setCrmSeedFile(selectedFile)
      loadHistory()
    } catch (err) {
      const message = err?.message || err?.response?.data || 'Error generando el archivo.'
      updateStatus('danger', message)
    } finally {
      setLoading(false)
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
      updateStatus('danger', 'Primero genera un archivo de masividad para continuar en CRM.')
      return
    }
    try {
      setLoading(true)
      const response = await createCrmSession({ file: crmSeedFile, mode: 'sms_ivr', source: 'sms' })
      if (response.status >= 400 || !response.data?.token) {
        throw new Error(response.data?.message || 'No se pudo crear la sesión de CRM.')
      }
      navigate(`/procesos/crm?token=${encodeURIComponent(response.data.token)}&mode=sms_ivr`)
    } catch (err) {
      updateStatus('danger', err?.message || 'No se pudo abrir CRM unificado.')
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
              Este módulo genera la carga SMS y permite continuar al CRM unificado con el mismo archivo de origen.
            </p>
          </div>
          <Link to="/procesos" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type} onDismiss={clearStatus}>{status.message}</InlineAlert>}

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
              <button
                type="button"
                className="rounded-full border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                onClick={handleContinueCrm}
                disabled={loading || !crmSeedFile}
              >
                Continuar en CRM
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={() => {
                setMasivoData(initialMasivoState)
                setMensajesPersonalizados(false)
                setItauCarterizado(false)
                setCrmSeedFile(null)
                if (masivoFileRef.current) masivoFileRef.current.value = ''
              }}>
                Limpiar campos
              </button>
            </div>
          </form>
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Historial de este proceso</h2>
              <p className="text-sm text-slate-600">Registros recientes generados desde SMS.</p>
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
                    <td colSpan={5} className="px-3 py-6 text-center text-slate-500">Aún no hay cargas registradas para SMS.</td>
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

export default SmsPage
