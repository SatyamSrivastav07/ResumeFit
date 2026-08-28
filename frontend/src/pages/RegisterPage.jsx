import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import AuthLayout from '../components/AuthLayout.jsx'
import { useAuth } from '../hooks/useAuth.js'
import { getAuthErrorMessage } from '../utils/authErrors.js'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validate(form) {
  if (!form.name.trim()) return 'Enter your name.'
  if (!EMAIL_PATTERN.test(form.email.trim())) return 'Enter a valid email address.'
  if (form.password.length < 6) return 'Password must contain at least 6 characters.'
  if (form.password !== form.confirmPassword) return 'Passwords do not match.'
  return ''
}

function RegisterPage() {
  const { register, user, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', confirmPassword: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!authLoading && user) {
      navigate('/dashboard', { replace: true })
    }
  }, [authLoading, navigate, user])

  function handleChange(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
    setError('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const validationError = validate(form)

    if (validationError) {
      setError(validationError)
      return
    }

    setSubmitting(true)
    setError('')
    try {
      await register(form.email.trim(), form.password)
      navigate('/dashboard', { replace: true })
    } catch (firebaseError) {
      setError(getAuthErrorMessage(firebaseError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      eyebrow="Create your account"
      title="Start with a truthful resume"
      description="Create a secure account now. Your resume workspace arrives in the next phase."
      footer={
        <>
          Already have an account?{' '}
          <Link className="font-bold text-brand-700 hover:text-brand-900" to="/login">
            Log in
          </Link>
        </>
      }
    >
      <form className="space-y-4" onSubmit={handleSubmit} noValidate>
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
            {error}
          </div>
        )}

        <label className="block">
          <span className="text-sm font-bold text-slate-700">Name</span>
          <input
            autoComplete="name"
            className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-ink shadow-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            name="name"
            onChange={handleChange}
            placeholder="Your name"
            type="text"
            value={form.name}
          />
        </label>

        <label className="block">
          <span className="text-sm font-bold text-slate-700">Email</span>
          <input
            autoComplete="email"
            className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-ink shadow-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            name="email"
            onChange={handleChange}
            placeholder="you@example.com"
            type="email"
            value={form.email}
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm font-bold text-slate-700">Password</span>
            <input
              autoComplete="new-password"
              className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-ink shadow-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              name="password"
              onChange={handleChange}
              placeholder="6+ characters"
              type="password"
              value={form.password}
            />
          </label>
          <label className="block">
            <span className="text-sm font-bold text-slate-700">Confirm password</span>
            <input
              autoComplete="new-password"
              className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-ink shadow-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              name="confirmPassword"
              onChange={handleChange}
              placeholder="Repeat password"
              type="password"
              value={form.confirmPassword}
            />
          </label>
        </div>

        <button
          className="w-full rounded-xl bg-brand-600 px-5 py-3.5 text-sm font-bold text-white shadow-lg shadow-brand-600/20 transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={submitting || authLoading}
          type="submit"
        >
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </AuthLayout>
  )
}

export default RegisterPage
