import { Link } from 'react-router-dom'

const depuradores = [
  {
    title: 'Depurador de Direcciones',
    description: 'Limpieza de direcciones repetidas por RUT',
    to: '/depuradores/direcciones',
    icon: 'DIR',
  },
]

function Depuradores() {
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Depuradores</p>
            <h1 className="text-3xl font-semibold text-slate-900">Herramientas de limpieza</h1>
            <p className="mt-2 text-slate-600">Modulos para ordenar bases origen antes de usarlas en operacion.</p>
          </div>
          <Link to="/" className="text-sm text-indigo-600 hover:text-indigo-500">Volver</Link>
        </div>

        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {depuradores.map(card => (
            <Link
              key={card.title}
              to={card.to}
              className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-1 hover:shadow-lg"
            >
              <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-50 text-sm font-semibold text-cyan-700 ring-1 ring-cyan-100">
                {card.icon}
              </div>
              <h2 className="text-xl font-semibold text-slate-900">{card.title}</h2>
              <p className="mt-2 text-sm text-slate-600">{card.description}</p>
            </Link>
          ))}
        </div>
      </div>
    </main>
  )
}

export default Depuradores
