import { Link } from 'react-router-dom'

const cards = [
  { title: 'Procesos', description: 'SMS, IVR y Mail', to: '/procesos', icon: '⚙️' },
  { title: 'Cargas', description: 'Módulos GM y Santander', to: '/cargas', icon: '📦' },
  { title: 'Reportes', description: 'Consolidados y filtros por mandante', to: '/reportes', icon: '📊' },
  { title: 'Resultantes', description: 'Gestiones por fecha y mandante', to: '/resultantes', icon: '🧾' },
]

function Portal() {
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-4xl">
        <header className="mb-8 text-center">
          <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Phoenix Service</p>
          <h1 className="text-3xl font-semibold text-slate-900">Centro de Operaciones</h1>
          <p className="mt-3 text-slate-600">Selecciona la sección que necesitas. Todos los procesos siguen conectados al backend actual.</p>
        </header>

        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          {cards.map(card => (
            <Link
              key={card.title}
              to={card.to}
              className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-1 hover:shadow-lg"
            >
              <div className="mb-4 text-4xl">{card.icon}</div>
              <h2 className="text-xl font-semibold text-slate-900">{card.title}</h2>
              <p className="mt-2 text-sm text-slate-600">{card.description}</p>
            </Link>
          ))}
        </div>
      </div>
    </main>
  )
}

export default Portal
