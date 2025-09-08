import { Routes, Route, Link } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Button from './components/Button'
import './App.scss'

import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Home from './pages/Home'
import PitchDetail from './pages/PitchDetail'
import CreatePitch from './pages/CreatePitch'
import EditPitch from './pages/EditPitch'
import RecordVideo from './pages/RecordVideo'
import UploadVideo from './pages/UploadVideo'
import PitchResults from './pages/PitchResults'
import PresentationAnalysis from './pages/PresentationAnalysis'
import SpeechAnalysis from './pages/SpeechAnalysis'
import TrainingSessions from './pages/TrainingSessions'
import HypotheticalQuestions from './pages/HypotheticalQuestions'

const Header = () => {
  const { isAuthenticated, user, logout } = useAuth()

  return (
    <header className='header'>
      <Link to='/' className='logo-link'>
        <h1 className='logo'>
          <span className='logo-light'>лайт</span>
          <span className='logo-pitch'>питч</span>
        </h1>
      </Link>
      <p className='subtitle'>AI-помощник для презентаций и питчей</p>

      <nav className='nav'>
        {isAuthenticated() ? (
          <div className='nav-authenticated'>
            <span className='user-greeting'>Привет, {user?.full_name}!</span>
            <Button onClick={logout} variant='default' size='small'>
              Выйти
            </Button>
          </div>
        ) : (
          <div className='nav-guest'>
            <Button as={Link} to='/auth/login' variant='default' size='small'>
              Войти
            </Button>
            <Button as={Link} to='/auth/register' variant='default' size='small'>
              Регистрация
            </Button>
          </div>
        )}
      </nav>
    </header>
  )
}

// Main page component that shows Landing or Dashboard based on auth status
const MainPage = () => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='loading'>
            <div className='spinner'></div>
            <p>Загрузка...</p>
          </div>
        </div>
      </main>
    )
  }

  return isAuthenticated() ? <Dashboard /> : <Landing />
}

const App = () => {
  return (
    <AuthProvider>
      <div className='app'>
        <Header />

        {/* Routes */}
        <Routes>
          <Route path='/' element={<MainPage />} />
          <Route path='/auth/login' element={<Login />} />
          <Route path='/auth/register' element={<Register />} />

          {/* Protected Routes */}
          <Route
            path='/dashboard'
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path='/home'
            element={
              <ProtectedRoute>
                <Home />
              </ProtectedRoute>
            }
          />

          <Route
            path='/create'
            element={
              <ProtectedRoute>
                <CreatePitch />
              </ProtectedRoute>
            }
          />

          <Route
            path='/pitch/:id'
            element={
              <ProtectedRoute>
                <PitchDetail />
              </ProtectedRoute>
            }
          />

          <Route
            path='/pitch/:id/edit'
            element={
              <ProtectedRoute>
                <EditPitch />
              </ProtectedRoute>
            }
          />

          <Route
            path='/pitch/:id/record'
            element={
              <ProtectedRoute>
                <RecordVideo />
              </ProtectedRoute>
            }
          />

          <Route
            path='/pitch/:id/upload'
            element={
              <ProtectedRoute>
                <UploadVideo />
              </ProtectedRoute>
            }
          />

          <Route
            path='/pitch/:id/results'
            element={
              <ProtectedRoute>
                <PitchResults />
              </ProtectedRoute>
            }
          />

          <Route
            path='/pitch/:id/presentation-analysis'
            element={
              <ProtectedRoute>
                <PresentationAnalysis />
              </ProtectedRoute>
            }
          />

          <Route
            path='/pitch/:id/speech-analysis'
            element={
              <ProtectedRoute>
                <SpeechAnalysis />
              </ProtectedRoute>
            }
          />

          <Route
            path='/pitch/:id/training-sessions'
            element={
              <ProtectedRoute>
                <TrainingSessions />
              </ProtectedRoute>
            }
          />

          <Route
            path='/pitch/:id/hypothetical-questions'
            element={
              <ProtectedRoute>
                <HypotheticalQuestions />
              </ProtectedRoute>
            }
          />

          <Route path='*' element={<NotFound />} />
        </Routes>
      </div>
    </AuthProvider>
  )
}

// Компонент для 404 страницы
const NotFound = () => {
  return (
    <main className='main'>
      <div className='container'>
        <div className='empty-state'>
          <div className='empty-icon'>😕</div>
          <h3>Страница не найдена</h3>
          <p>Запрашиваемая страница не существует</p>
          <Button variant='primary' as={Link} to='/'>
            Перейти на главную
          </Button>
        </div>
      </div>
    </main>
  )
}

export default App
