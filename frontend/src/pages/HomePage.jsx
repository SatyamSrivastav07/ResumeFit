import { Link } from 'react-router-dom'

import AppLogo from '../components/AppLogo.jsx'
import FeatureCard from '../components/FeatureCard.jsx'
import { useAuth } from '../hooks/useAuth.js'

const steps = [
  {
    title: 'Upload your resume',
    description: 'Start with the experience, skills, and achievements already supported by your resume.',
  },
  {
    title: 'Add the job description',
    description: 'Compare your background with the role using a clear, deterministic ATS analysis.',
  },
  {
    title: 'Review every change',
    description: 'Accept, reject, or edit truthful suggestions before generating your tailored PDF.',
  },
]

function HomePage() {
  const { user, loading } = useAuth()

  return (
    <div className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_right,_#d8f7ed_0,_transparent_35%)]">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6 lg:px-8">
        <AppLogo />
        <div className="flex items-center gap-3">
          {!loading && !user && (
            <Link className="text-sm font-bold text-slate-600 hover:text-brand-700" to="/login">
              Log in
            </Link>
          )}
          <Link
            className="rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-bold text-white shadow-sm hover:bg-brand-700"
            to={user ? '/dashboard' : '/register'}
          >
            {user ? 'Dashboard' : 'Get started'}
          </Link>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-7xl gap-14 px-6 pb-20 pt-16 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:px-8 lg:pb-28 lg:pt-24">
          <div>
            <p className="mb-5 text-sm font-bold uppercase tracking-[0.18em] text-brand-700">
              Truthful tailoring. Stronger applications.
            </p>
            <h1 className="max-w-3xl text-5xl font-black leading-[1.05] tracking-tight text-ink sm:text-6xl">
              Make your resume fit the role—without inventing a thing.
            </h1>
            <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-600">
              ResumeFit AI helps you highlight the experience you already have, align it with the job, and create a clean ATS-friendly resume you can stand behind.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-4">
              <Link
                to={user ? '/dashboard' : '/register'}
                className="rounded-xl bg-brand-600 px-6 py-3.5 text-sm font-bold text-white shadow-lg shadow-brand-600/20 hover:bg-brand-700"
              >
                Tailor My Resume
              </Link>
              <span className="text-sm text-slate-500">Create an account to access your dashboard.</span>
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-lg">
            <div className="absolute -inset-5 -z-10 rotate-2 rounded-[2rem] bg-brand-100/70" />
            <div className="rounded-[1.5rem] border border-slate-200 bg-white p-7 shadow-card sm:p-9">
              <div className="flex items-center justify-between border-b border-slate-100 pb-5">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Resume match</p>
                  <p className="mt-1 text-lg font-bold">Software Engineer</p>
                </div>
                <span className="text-4xl font-black text-brand-600">74%</span>
              </div>
              <div className="mt-6 space-y-5">
                <div>
                  <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">Matched skills</p>
                  <div className="flex flex-wrap gap-2">
                    {['React', 'JavaScript', 'REST APIs', 'MongoDB'].map((skill) => (
                      <span key={skill} className="rounded-lg bg-brand-50 px-3 py-1.5 text-xs font-semibold text-brand-700">
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-amber-800">Skills gap</p>
                  <p className="mt-1 text-sm leading-6 text-amber-900">
                    Missing skills stay recommendations and are never inserted into your resume.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-slate-200 bg-white/75">
          <div className="mx-auto max-w-7xl px-6 py-16 lg:px-8">
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-700">How it works</p>
            <div className="mt-7 grid gap-5 md:grid-cols-3">
              {steps.map((step, index) => (
                <FeatureCard key={step.title} number={index + 1} {...step} />
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="mx-auto flex max-w-7xl flex-col gap-3 px-6 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between lg:px-8">
        <AppLogo />
        <p>Built around factual accuracy and user control.</p>
      </footer>
    </div>
  )
}

export default HomePage
