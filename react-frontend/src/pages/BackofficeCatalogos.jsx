import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import InlineAlert from '../components/InlineAlert'
import {
  createCampo1Item,
  deleteCampo1Item,
  fetchCampo1Catalogo,
  fetchCatalogosBackoffice,
  updateCampo1Item,
} from '../api/backoffice'

const initialCampo1Form = {
  label: '',
  value: '',
  active: true,
}

function BackofficeCatalogos() {
  const [loading, setLoading] = useState(false)
  const [payload, setPayload] = useState(null)
  const [campo1Items, setCampo1Items] = useState([])
  const [campo1Form, setCampo1Form] = useState(initialCampo1Form)
  const [editingId, setEditingId] = useState(null)
  const [savingCampo1, setSavingCampo1] = useState(false)
  const [status, setStatus] = useState({ type: 'info', message: '' })

  const mandantesDb = payload?.catalogs?.mandantes?.db || []
  const mandantesApp = payload?.catalogs?.mandantes?.app_constants || []
  const procesosDb = payload?.catalogs?.procesos?.db || []
  const templates = payload?.catalogs?.mail_templates || []

  const activeMandantes = useMemo(() => mandantesDb.filter(item => item.activo), [mandantesDb])
  const activeProcesos = useMemo(() => procesosDb.filter(item => item.activo), [procesosDb])
  const activeCampo1 = useMemo(() => campo1Items.filter(item => item.active), [campo1Items])

  const loadCatalogos = async () => {
    try {
      setLoading(true)
      const data = await fetchCatalogosBackoffice()
      setPayload(data)
      const warningCount = Array.isArray(data?.warnings) ? data.warnings.length : 0
      if (warningCount > 0) {
        setStatus({ type: 'warning', message: `Catalogos cargados con ${warningCount} advertencia(s).` })
      } else {
        setStatus({ type: 'success', message: 'Catalogos cargados correctamente.' })
      }
    } catch (error) {
      setStatus({ type: 'danger', message: error?.message || 'No se pudieron cargar los catalogos.' })
      setPayload(null)
    } finally {
      setLoading(false)
    }
  }

  const loadCampo1 = async () => {
    try {
      const data = await fetchCampo1Catalogo()
      setCampo1Items(Array.isArray(data?.items) ? data.items : [])
    } catch (error) {
      setStatus({ type: 'danger', message: error?.message || 'No se pudo cargar CAMPO1.' })
      setCampo1Items([])
    }
  }

  useEffect(() => {
    loadCatalogos()
    loadCampo1()
  }, [])

  const startEditCampo1 = item => {
    setEditingId(item.id)
    setCampo1Form({
      label: item.label,
      value: item.value,
      active: item.active,
    })
  }

  const cancelEditCampo1 = () => {
    setEditingId(null)
    setCampo1Form(initialCampo1Form)
  }

  const handleCampo1Submit = async e => {
    e.preventDefault()
    if (!campo1Form.label.trim() || !campo1Form.value.trim()) {
      setStatus({ type: 'danger', message: 'Debes completar label y value para CAMPO1.' })
      return
    }

    try {
      setSavingCampo1(true)
      if (editingId) {
        await updateCampo1Item(editingId, {
          label: campo1Form.label,
          value: campo1Form.value,
          active: campo1Form.active,
        })
        setStatus({ type: 'success', message: 'CAMPO1 actualizado correctamente.' })
      } else {
        await createCampo1Item({
          label: campo1Form.label,
          value: campo1Form.value,
          active: campo1Form.active,
        })
        setStatus({ type: 'success', message: 'CAMPO1 creado correctamente.' })
      }
      cancelEditCampo1()
      await loadCampo1()
    } catch (error) {
      setStatus({ type: 'danger', message: error?.message || 'No se pudo guardar CAMPO1.' })
    } finally {
      setSavingCampo1(false)
    }
  }

  const handleCampo1Delete = async item => {
    if (!window.confirm(`Eliminar CAMPO1 '${item.label}'?`)) return
    try {
      setSavingCampo1(true)
      await deleteCampo1Item(item.id)
      setStatus({ type: 'success', message: 'CAMPO1 eliminado.' })
      if (editingId === item.id) {
        cancelEditCampo1()
      }
      await loadCampo1()
    } catch (error) {
      setStatus({ type: 'danger', message: error?.message || 'No se pudo eliminar CAMPO1.' })
    } finally {
      setSavingCampo1(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-6xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Backoffice</p>
            <h1 className="text-3xl font-semibold text-slate-900">Catalogos del sistema</h1>
            <p className="mt-2 max-w-3xl text-slate-600">Modulo con foco en CRUD de CAMPO1 para IVR y panel de referencia para catalogos base.</p>
          </div>
          <div className="flex items-center gap-3">
            <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600" onClick={() => { loadCatalogos(); loadCampo1() }} disabled={loading || savingCampo1}>
              {loading ? 'Actualizando...' : 'Actualizar'}
            </button>
            <Link to="/" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
          </div>
        </div>

        {status.message && <InlineAlert variant={status.type}>{status.message}</InlineAlert>}

        {Array.isArray(payload?.warnings) && payload.warnings.length > 0 && (
          <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-700">Advertencias</h2>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-amber-800">
              {payload.warnings.map(item => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        )}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <article className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Mandantes DB</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{mandantesDb.length}</p>
            <p className="mt-1 text-sm text-slate-500">Activos: {activeMandantes.length}</p>
          </article>
          <article className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Procesos DB</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{procesosDb.length}</p>
            <p className="mt-1 text-sm text-slate-500">Activos: {activeProcesos.length}</p>
          </article>
          <article className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">CAMPO1 IVR</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{campo1Items.length}</p>
            <p className="mt-1 text-sm text-slate-500">Activos: {activeCampo1.length}</p>
          </article>
          <article className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Plantillas Mail</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{templates.length}</p>
            <p className="mt-1 text-sm text-slate-500">Layouts registrados</p>
          </article>
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-4">
            <h2 className="text-xl font-semibold text-slate-900">CRUD CAMPO1 (IVR)</h2>
            <p className="text-sm text-slate-600">Los cambios impactan directamente el selector CAMPO1 del modulo IVR.</p>
          </header>

          <form className="grid gap-3 rounded-2xl border border-slate-200 p-4 md:grid-cols-4" onSubmit={handleCampo1Submit}>
            <input
              type="text"
              placeholder="Label"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={campo1Form.label}
              onChange={e => setCampo1Form(prev => ({ ...prev, label: e.target.value }))}
              required
            />
            <input
              type="text"
              placeholder="Value"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={campo1Form.value}
              onChange={e => setCampo1Form(prev => ({ ...prev, value: e.target.value }))}
              required
            />
            <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={campo1Form.active}
                onChange={e => setCampo1Form(prev => ({ ...prev, active: e.target.checked }))}
              />
              Activo
            </label>
            <div className="flex gap-2">
              <button type="submit" className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white" disabled={savingCampo1}>
                {savingCampo1 ? 'Guardando...' : editingId ? 'Guardar cambios' : 'Crear'}
              </button>
              {editingId && (
                <button type="button" className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700" onClick={cancelEditCampo1}>
                  Cancelar
                </button>
              )}
            </div>
          </form>

          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="px-3 py-2 font-medium">ID</th>
                  <th className="px-3 py-2 font-medium">Label</th>
                  <th className="px-3 py-2 font-medium">Value</th>
                  <th className="px-3 py-2 font-medium">Estado</th>
                  <th className="px-3 py-2 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {campo1Items.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-6 text-center text-slate-500">No hay registros CAMPO1.</td>
                  </tr>
                ) : (
                  campo1Items.map(item => (
                    <tr key={item.id} className="border-t border-slate-100">
                      <td className="px-3 py-2 text-slate-700">{item.id}</td>
                      <td className="px-3 py-2 font-semibold text-slate-900">{item.label}</td>
                      <td className="px-3 py-2 text-slate-700">{item.value}</td>
                      <td className="px-3 py-2 text-slate-700">{item.active ? 'Activo' : 'Inactivo'}</td>
                      <td className="px-3 py-2">
                        <div className="flex gap-2">
                          <button type="button" className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-700" onClick={() => startEditCampo1(item)}>
                            Editar
                          </button>
                          <button type="button" className="rounded-full border border-rose-200 px-3 py-1 text-xs text-rose-700" onClick={() => handleCampo1Delete(item)}>
                            Eliminar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-4">
            <h2 className="text-xl font-semibold text-slate-900">Mandantes (base de datos)</h2>
            <p className="text-sm text-slate-600">Fuente principal para catalogo operativo. Incluye codigo y estado activo.</p>
          </header>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="px-3 py-2 font-medium">ID</th>
                  <th className="px-3 py-2 font-medium">Codigo</th>
                  <th className="px-3 py-2 font-medium">Nombre</th>
                  <th className="px-3 py-2 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {mandantesDb.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-3 py-6 text-center text-slate-500">Sin datos de mandantes en base.</td>
                  </tr>
                ) : (
                  mandantesDb.map(item => (
                    <tr key={`${item.id}-${item.codigo}`} className="border-t border-slate-100">
                      <td className="px-3 py-2 text-slate-700">{item.id}</td>
                      <td className="px-3 py-2 font-semibold text-slate-900">{item.codigo}</td>
                      <td className="px-3 py-2 text-slate-700">{item.nombre}</td>
                      <td className="px-3 py-2 text-slate-700">{item.activo ? 'Activo' : 'Inactivo'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <header className="mb-4">
            <h2 className="text-xl font-semibold text-slate-900">Procesos (base de datos)</h2>
            <p className="text-sm text-slate-600">Incluye tipo de proceso y costo unitario configurado.</p>
          </header>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="px-3 py-2 font-medium">ID</th>
                  <th className="px-3 py-2 font-medium">Codigo</th>
                  <th className="px-3 py-2 font-medium">Descripcion</th>
                  <th className="px-3 py-2 font-medium">Tipo</th>
                  <th className="px-3 py-2 font-medium">Costo unitario</th>
                  <th className="px-3 py-2 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {procesosDb.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-slate-500">Sin datos de procesos en base.</td>
                  </tr>
                ) : (
                  procesosDb.map(item => (
                    <tr key={`${item.id}-${item.codigo}`} className="border-t border-slate-100">
                      <td className="px-3 py-2 text-slate-700">{item.id}</td>
                      <td className="px-3 py-2 font-semibold text-slate-900">{item.codigo}</td>
                      <td className="px-3 py-2 text-slate-700">{item.descripcion}</td>
                      <td className="px-3 py-2 text-slate-700">{item.tipo}</td>
                      <td className="px-3 py-2 text-slate-700">{Number(item.costo_unitario || 0).toLocaleString('es-CL')}</td>
                      <td className="px-3 py-2 text-slate-700">{item.activo ? 'Activo' : 'Inactivo'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="grid gap-6 md:grid-cols-2">
          <article className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
            <h2 className="text-xl font-semibold text-slate-900">Mandantes en constantes de app</h2>
            <p className="mt-1 text-sm text-slate-600">Referencia fallback usada en formularios y validaciones.</p>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">
              {mandantesApp.map(item => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
            <h2 className="text-xl font-semibold text-slate-900">Plantillas de Mail</h2>
            <p className="mt-1 text-sm text-slate-600">Catalogo de plantillas activas para generacion de layout mail/template.</p>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">
              {templates.map(item => (
                <li key={item.code}>{item.label} ({item.code})</li>
              ))}
            </ul>
          </article>
        </section>
      </div>
    </main>
  )
}

export default BackofficeCatalogos
