import { Link } from 'react-router-dom'

const procesos = [
  { title: 'SMS', description: 'Masividades Athenas/AXIA + CRM', to: '/procesos/sms', icon: '📩', disabled: false },
  { title: 'IVR', description: 'Cargas Athenas y CRM', to: '/procesos/ivr', icon: '📞', disabled: false },
  { title: 'Mail', description: 'Plantillas y carga CRM', to: '/procesos/mail', icon: '✉️', disabled: false },
]

function Procesos() {
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Procesos</p>
            <h1 className="text-3xl font-semibold text-slate-900">Generadores disponibles</h1>
            <p className="mt-2 text-slate-600">SMS, IVR y Mail ya corren en React reutilizando los mismos endpoints Flask.</p>
          </div>
          <Link to="/" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {procesos.map(proc => (
            proc.disabled ? (
              <div key={proc.title} className="rounded-3xl bg-white p-6 opacity-50 ring-1 ring-slate-200">
                <div className="text-3xl">{proc.icon}</div>
                <h2 className="mt-4 text-xl font-semibold text-slate-900">{proc.title}</h2>
                <p className="mt-2 text-sm text-slate-600">{proc.description}</p>
                <p className="mt-4 text-xs uppercase tracking-wide text-slate-500">Próximamente</p>
              </div>
            ) : (
              <Link key={proc.title} to={proc.to} className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-1 hover:shadow-lg">
                <div className="text-3xl">{proc.icon}</div>
                <h2 className="mt-4 text-xl font-semibold text-slate-900">{proc.title}</h2>
                <p className="mt-2 text-sm text-slate-600">{proc.description}</p>
              </Link>
            )
          ))}
        </div>
      </div>
    </main>
  )
}

export default Procesos
