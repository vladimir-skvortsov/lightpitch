import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import Button from '../components/Button'
import './Auth.scss'

const Login = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const from = location.state?.from?.pathname || '/dashboard'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    const result = await login(email, password)

    if (result.success) {
      navigate(from, { replace: true })
    } else {
      setError(result.error)
    }

    setLoading(false)
  }

  return (
    <main className='main'>
      <div className='container'>
        <div className='auth-page'>
          <div className='auth-card'>
            <div className='auth-header'>
              <h1>Вход в систему</h1>
            </div>

            <form onSubmit={handleSubmit} className='auth-form'>
              {error && <div className='error-message'>{error}</div>}

              <div className='form-group'>
                <label htmlFor='email'>Email</label>
                <input
                  type='email'
                  id='email'
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder='your@email.com'
                  disabled={loading}
                />
              </div>

              <div className='form-group'>
                <label htmlFor='password'>Пароль</label>
                <input
                  type='password'
                  id='password'
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder='Введите пароль'
                  disabled={loading}
                />
              </div>

              <Button type='submit' variant='primary' className='auth-submit' disabled={loading}>
                {loading ? 'Вход...' : 'Войти'}
              </Button>
            </form>

            <div className='auth-footer'>
              <p>
                Нет аккаунта?{' '}
                <Link to='/auth/register' className='auth-link'>
                  Зарегистрироваться
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

export default Login
