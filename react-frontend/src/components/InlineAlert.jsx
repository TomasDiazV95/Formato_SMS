function InlineAlert({ variant = 'info', children, onDismiss }) {
  const palette = {
    info: 'bg-sky-50 text-sky-800 border-sky-200',
    success: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    warning: 'bg-amber-50 text-amber-900 border-amber-200',
    danger: 'bg-rose-50 text-rose-800 border-rose-200',
  }

  const classes = palette[variant] || palette.info

  return (
    <div className={`flex items-start justify-between gap-3 rounded-2xl border px-4 py-3 text-sm ${classes}`}>
      <div className="min-w-0 flex-1 whitespace-pre-wrap break-words">
        {children}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded-full px-2 py-1 text-xs font-semibold opacity-70 transition hover:opacity-100"
          aria-label="Cerrar mensaje"
        >
          Cerrar
        </button>
      )}
    </div>
  )
}

export default InlineAlert
