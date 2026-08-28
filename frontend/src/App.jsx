import { Navigate, Route, Routes } from 'react-router-dom'

import ProtectedRoute from './components/ProtectedRoute.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import HomePage from './pages/HomePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import JobDetailsPage from './pages/JobDetailsPage.jsx'
import OptimizationPage from './pages/OptimizationPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import ResumeDetailsPage from './pages/ResumeDetailsPage.jsx'
import ResumesPage from './pages/ResumesPage.jsx'

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route path="/resumes" element={<ProtectedRoute><ResumesPage /></ProtectedRoute>} />
      <Route path="/resumes/:resumeId" element={<ProtectedRoute><ResumeDetailsPage /></ProtectedRoute>} />
      <Route path="/jobs/:jobId" element={<ProtectedRoute><JobDetailsPage /></ProtectedRoute>} />
      <Route path="/optimizations/:optimizationId" element={<ProtectedRoute><OptimizationPage /></ProtectedRoute>} />
      <Route path="/404" element={<NotFoundPage />} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  )
}

export default App
