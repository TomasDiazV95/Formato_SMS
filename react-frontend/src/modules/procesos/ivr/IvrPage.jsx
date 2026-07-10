import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../../../components/InlineAlert'
import { mandantes } from '../../../data/constants'
import { campo1Options } from '../../../data/ivrOptions'
import { downloadIvrSample, fetchIvrCampo1Options, submitIvrAthenas } from '../../../api/ivr'
import { triggerDownload, assertExcelResponse, ZIP_MIME } from '../../../utils/download'

const initialIvrState = {
  mandante: '',
  campo1: '',
}

const ivrCrmRules = {
  'Santander Consumer Terreno': { usuario: 'jriveros', observacion: '' },
  'Santander Consumer Telefonía': { usuario: 'jriveros', observacion: '' },
  'Santander Consumer Judicial': { usuario: 'jriveros', observacion: '' },
  'General Motors': { usuario: 'jriveros', observacion: 'IVR' },
  'Itau Vencida': { usuario: 'VDAD', observacion: '' },
  'Itau Castigo': { usuario: 'VDAD', observacion: '' },
  'Banco Internacional': { usuario: 'VDAD', observacion: '' },
  'Santander Hipotecario': { usuario: 'VDAD', observacion: '' },
  'La Araucana': { usuario: 'VDAD', observacion: '' },
  Tanner: { usuario: 'VDAD', observacion: '' },
}

function IvrPage() {
  const [ivrData, setIvrData] = useState(initialIvrState)
  const [status, setStatus] = useState({ type: 'info', message: '' })
  const [campo1Catalog, setCampo1Catalog] = useState(campo1Options)
  const [includeCrm, setIncludeCrm] = useState(false)
  const [crmDate, setCrmDate] = useState('')
  const [crmStartTime, setCrmStartTime] = useState('10:00')
  const [crmEndTime, setCrmEndTime] = useState('18:00')
  const [loading, setLoading] = useState(false)

  const ivrFileRef = useRef(null)
  const crmRule = ivrCrmRules[ivrData.mandante]
  const crmDisabled = !crmRule

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

  const resetForm = () => {
    setIvrData(initialIvrState)
    setIncludeCrm(false)
    setCrmDate('')
    setCrmStartTime('10:00')
    setCrmEndTime('18:00')
    if (ivrFileRef.current) ivrFileRef.current.value = ''
  }

  const handleSubmitIvr = async e => {
    e.preventDefault()
    if (!ivrFileRef.current?.files?.[0]) {
      updateStatus('danger', 'Debes adjuntar un archivo Excel para la carga IVR.')
      return
    }
    if (includeCrm && crmDisabled) {
      updateStatus('danger', 'No hay regla CRM configurada para este mandante en IVR.')
      return
    }
    if (includeCrm && (!crmDate || !crmStartTime || !crmEndTime)) {
      updateStatus('danger', 'Debes completar fecha, hora inicio y hora fin para CRM.')
      return
    }
    const formData = new FormData()
    formData.append('file', ivrFileRef.current.files[0])
    formData.append('mandante', ivrData.mandante)
    formData.append('campo1', ivrData.campo1)
    if (includeCrm) {
      formData.append('include_crm', 'on')
      formData.append('crm_fecha', crmDate)
      formData.append('crm_hora_inicio', crmStartTime)
      formData.append('crm_hora_fin', crmEndTime)
    }
    try {
      setLoading(true)
      const response = await submitIvrAthenas(formData)
      await assertExcelResponse(response, 'Error generando la carga IVR.', [ZIP_MIME])
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replaceAll('"', '') || 'carga_IVR.xlsx'
      triggerDownload(response.data, filename)
      updateStatus('success', 'Carga IVR generada correctamente.')
      resetForm()
    } catch (err) {
      const message = err?.message || err?.response?.data || 'Error generando la carga IVR.'
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
            <h1 className="text-3xl font-semibold text-slate-900">Cargas IVR Athenas</h1>
            <p className="mt-2 max-w-2xl text-slate-600">Sube la base y selecciona el CAMPO1 que corresponde a cada mandante.</p>
          </div>
          <Link to="/procesos" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-6">
            <h2 className="text-xl font-semibold text-slate-900">Carga IVR (Athenas)</h2>
            <p className="text-sm text-slate-600">Genera IVR y opcionalmente entrega el CRM listo en el mismo ZIP.</p>
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

            <div className="rounded-2xl border border-slate-200 p-4">
              <label className="flex items-center gap-3 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={includeCrm}
                  onChange={e => setIncludeCrm(e.target.checked)}
                  disabled={crmDisabled}
                  className="h-4 w-4 rounded border-slate-300"
                />
                Generar archivo CRM junto con IVR
              </label>
              {crmRule && <p className="mt-2 text-xs text-slate-500">Usuario CRM fijo: {crmRule.usuario}. Observacion fija: {crmRule.observacion || 'vacia'}.</p>}
              {!crmRule && ivrData.mandante && <p className="mt-2 text-xs text-amber-600">No hay regla CRM configurada para este mandante.</p>}
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

            <div className="flex flex-wrap gap-3">
              <button className="inline-flex items-center rounded-full bg-indigo-600 px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500" type="submit" disabled={loading}>
                {loading ? 'Procesando…' : 'Generar archivo'}
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={() => {
                resetForm()
              }}>
                Limpiar campos
              </button>
              <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={handleSample}>
                Descargar ejemplo
              </button>
            </div>
          </form>
        </section>

      </div>
    </main>
  )
}

export default IvrPage
