import { Link } from 'react-router-dom'

const cargas = [
  { title: 'Carga General Motors', description: 'Procesamiento + comparación Collection', to: '/cargas/gm', icon: '🚗' },
  { title: 'Carga BIT', description: 'Asignación CRM + datos adicionales', to: '/cargas/bit', icon: '🧩' },
  { title: 'Carga Tanner', description: 'Asignación CRM con mapeo de tramos', to: '/cargas/tanner', icon: '📁' },
  { title: 'Carga Porsche', description: 'Asignación CRM mensual desde base origen', to: '/cargas/porsche', icon: '🏎️' },
  { title: 'Santander Hipotecario', description: 'CSV → CRM / Masividad', to: '/cargas/santander', icon: '🏦' },
]

function Cargas() {
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Cargas</p>
            <h1 className="text-3xl font-semibold text-slate-900">Módulos disponibles</h1>
            <p className="mt-2 text-slate-600">Los módulos viven en React, reutilizando los endpoints existentes de Flask.</p>
          </div>
          <Link to="/" className="text-sm text-indigo-600 hover:text-indigo-500">← Volver</Link>
        </div>

        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {cargas.map(card => (
            <Link key={card.title} to={card.to} className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-1 hover:shadow-lg">
              <div className="text-3xl">{card.icon}</div>
              <h2 className="mt-4 text-xl font-semibold text-slate-900">{card.title}</h2>
              <p className="mt-2 text-sm text-slate-600">{card.description}</p>
            </Link>
          ))}
        </div>
      </div>
    </main>
  )
}

export default Cargas
