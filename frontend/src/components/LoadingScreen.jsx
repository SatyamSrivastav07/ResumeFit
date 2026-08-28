function LoadingScreen({ message = 'Checking your session…' }) {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-50 px-6" role="status">
      <div className="text-center">
        <span className="mx-auto block size-10 animate-spin rounded-full border-4 border-brand-100 border-t-brand-600" />
        <p className="mt-4 text-sm font-semibold text-slate-600">{message}</p>
      </div>
    </main>
  )
}

export default LoadingScreen
