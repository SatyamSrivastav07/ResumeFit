function AppLogo() {
  return (
    <div className="flex items-center gap-3" aria-label="ResumeFit AI home">
      <span
        aria-hidden="true"
        className="grid size-9 place-items-center rounded-xl bg-brand-600 text-sm font-black text-white shadow-sm"
      >
        RF
      </span>
      <span className="text-lg font-bold tracking-tight text-ink">
        ResumeFit <span className="text-brand-600">AI</span>
      </span>
    </div>
  )
}

export default AppLogo

