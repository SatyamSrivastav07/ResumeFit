import { Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '../hooks/useAuth.js'
import LoadingScreen from './LoadingScreen.jsx'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <LoadingScreen />
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}

export default ProtectedRoute
