import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='loading'>
            <div className='spinner'></div>
            <p>Проверка авторизации...</p>
          </div>
        </div>
      </main>
    )
  }

  if (!isAuthenticated()) {
    // Redirect to login page with return url
    return <Navigate to='/auth/login' state={{ from: location }} replace />
  }

  return children
}

export default ProtectedRoute
