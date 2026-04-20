function InlineAlert({ variant = 'info', children }) {
  const palette = {
    info: 'bg-sky-50 text-sky-800 border-sky-200',
    success: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    warning: 'bg-amber-50 text-amber-900 border-amber-200',
    danger: 'bg-rose-50 text-rose-800 border-rose-200',
  }

  const classes = palette[variant] || palette.info

  return (
    <div className={`rounded-2xl border px-4 py-3 text-sm ${classes}`}>
      {children}
    </div>
  )
}

export default InlineAlert
