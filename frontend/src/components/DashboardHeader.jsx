import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '../hooks/useAuth.js'
import AppLogo from './AppLogo.jsx'

function DashboardHeader() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-5 lg:px-8">
        <AppLogo />
        <nav className="flex items-center gap-2 text-sm font-bold">
          <Link className="rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-50" to="/dashboard">Dashboard</Link>
          <Link className="rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-50" to="/resumes">My Resumes</Link>
          <button className="rounded-xl border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50" onClick={handleLogout} type="button">Logout</button>
        </nav>
      </div>
    </header>
  )
}

export default DashboardHeader
