import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-50 px-6 text-center">
      <div>
        <p className="text-sm font-bold uppercase tracking-widest text-brand-700">404</p>
        <h1 className="mt-3 text-4xl font-black tracking-tight text-ink">Page not found</h1>
        <p className="mt-3 text-slate-600">The page you requested does not exist yet.</p>
        <Link
          to="/"
          className="mt-7 inline-block rounded-xl bg-brand-600 px-5 py-3 text-sm font-bold text-white"
        >
          Back to home
        </Link>
      </div>
    </main>
  )
}

export default NotFoundPage

