import { Link } from 'react-router-dom'

import AppLogo from './AppLogo.jsx'

function AuthLayout({ eyebrow, title, description, children, footer }) {
  return (
    <div className="grid min-h-screen bg-slate-50 lg:grid-cols-[0.95fr_1.05fr]">
      <aside className="hidden bg-brand-900 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <Link to="/" className="w-fit rounded-lg bg-white px-3 py-2">
          <AppLogo />
        </Link>
        <div className="max-w-lg">
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-100">
            Accurate by design
          </p>
          <p className="mt-5 text-4xl font-black leading-tight tracking-tight">
            Tailor your story to the role, while keeping every detail true.
          </p>
          <div className="mt-8 h-1 w-16 rounded-full bg-brand-500" />
        </div>
        <p className="text-sm text-brand-100">Your credentials are handled securely by Firebase Authentication.</p>
      </aside>

      <main className="flex items-center justify-center px-6 py-10 sm:px-10">
        <div className="w-full max-w-md">
          <Link to="/" className="mb-10 block w-fit rounded-lg lg:hidden">
            <AppLogo />
          </Link>
          <p className="text-sm font-bold uppercase tracking-[0.16em] text-brand-700">{eyebrow}</p>
          <h1 className="mt-3 text-4xl font-black tracking-tight text-ink">{title}</h1>
          <p className="mt-3 leading-7 text-slate-600">{description}</p>
          <div className="mt-8">{children}</div>
          <div className="mt-7 text-center text-sm text-slate-600">{footer}</div>
        </div>
      </main>
    </div>
  )
}

export default AuthLayout
