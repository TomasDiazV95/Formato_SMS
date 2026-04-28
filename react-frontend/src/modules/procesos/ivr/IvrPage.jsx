import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import InlineAlert from '../../../components/InlineAlert'
import { mandantes } from '../../../data/constants'
import { campo1Options } from '../../../data/ivrOptions'
import { downloadIvrSample, fetchIvrCampo1Options, submitIvrAthenas } from '../../../api/ivr'
import { createCrmSession } from '../../../api/crm'
import { fetchProcessHistory } from '../../../api/reports'
import { triggerDownload, assertExcelResponse } from '../../../utils/download'
import useStatusMessage from '../../../hooks/useStatusMessage'

const initialIvrState = {
  mandante: '',
  campo1: '',
}

function IvrPage() {
  const navigate = useNavigate()
  const [ivrData, setIvrData] = useState(initialIvrState)
  const { status, updateStatus, clearStatus } = useStatusMessage()
  const [campo1Catalog, setCampo1Catalog] = useState(campo1Options)
  const [crmSeedFile, setCrmSeedFile] = useState(null)
  const [historyRows, setHistoryRows] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [loading, setLoading] = useState(false)

  const ivrFileRef = useRef(null)

  const handleIvrChange = e => {
    const { name, value } = e.target
    setIvrData(prev => ({ ...prev, [name]: value }))
  }

  const loadHistory = async () => {
    try {
      setHistoryLoading(true)
      const data = await fetchProcessHistory({ proceso: 'ivr', limit: 20 })
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

  useEffect(() => {
    const loadCampo1 = async () => {
      try {
        const items = await fetchIvrCampo1Options()
        if (items.length > 0) {
          setCampo1Catalog(items)
        }
      } catch {
        setCampo1Catalog(campo1Options)
      }
    }
    loadCampo1()
  }, [])

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
    const selectedFile = ivrFileRef.current.files[0]
    formData.append('file', selectedFile)
    formData.append('mandante', ivrData.mandante)
    formData.append('campo1', ivrData.campo1)
    try {
      setLoading(true)
      const response = await submitIvrAthenas(formData)
      await assertExcelResponse(response, 'Error generando la carga IVR.')
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'carga_IVR.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Carga IVR generada correctamente.')
      setCrmSeedFile(selectedFile)
      loadHistory()
    } catch (err) {
      const message = err?.message || err?.response?.data || 'Error generando la carga IVR.'
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
      updateStatus('danger', 'Primero genera una carga IVR para continuar en CRM.')
      return
    }
    try {
      setLoading(true)
      const response = await createCrmSession({ file: crmSeedFile, mode: 'sms_ivr', source: 'ivr' })
      if (response.status >= 400 || !response.data?.token) {
        throw new Error(response.data?.message || 'No se pudo crear la sesión CRM.')
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
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Proceso IVR</p>
            <h1 className="text-3xl font-semibold text-slate-900">Cargas IVR Athenas</h1>
            <p className="mt-2 max-w-2xl text-slate-600">Sube la base y selecciona el CAMPO1 que corresponde a cada mandante.</p>
          </div>
          <Link to="/procesos" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type} onDismiss={clearStatus}>{status.message}</InlineAlert>}

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
                  {campo1Catalog.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
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
                setIvrData(initialIvrState)
                setCrmSeedFile(null)
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
          <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Historial de este proceso</h2>
              <p className="text-sm text-slate-600">Registros recientes generados desde IVR.</p>
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
                    <td colSpan={5} className="px-3 py-6 text-center text-slate-500">Aún no hay cargas registradas para IVR.</td>
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

export default IvrPage
