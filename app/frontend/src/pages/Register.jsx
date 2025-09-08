import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import Button from '../components/Button'
import './Auth.scss'

const Register = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const { register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    // Validate password confirmation
    if (password !== confirmPassword) {
      setError('Пароли не совпадают')
      setLoading(false)
      return
    }

    // Validate password length
    if (password.length < 6) {
      setError('Пароль должен содержать минимум 6 символов')
      setLoading(false)
      return
    }

    const result = await register(email, password, fullName)

    if (result.success) {
      navigate('/dashboard')
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
              <h1>Регистрация</h1>
              <p>Создайте новую учетную запись</p>
            </div>

            <form onSubmit={handleSubmit} className='auth-form'>
              {error && <div className='error-message'>{error}</div>}

              <div className='form-group'>
                <label htmlFor='fullName'>Полное имя</label>
                <input
                  type='text'
                  id='fullName'
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  placeholder='Иван Иванов'
                  disabled={loading}
                />
              </div>

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
                  placeholder='Минимум 6 символов'
                  disabled={loading}
                />
              </div>

              <div className='form-group'>
                <label htmlFor='confirmPassword'>Подтвердите пароль</label>
                <input
                  type='password'
                  id='confirmPassword'
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  placeholder='Повторите пароль'
                  disabled={loading}
                />
              </div>

              <Button type='submit' variant='primary' className='auth-submit' disabled={loading}>
                {loading ? 'Регистрация...' : 'Зарегистрироваться'}
              </Button>
            </form>

            <div className='auth-footer'>
              <p>
                Уже есть аккаунт?{' '}
                <Link to='/auth/login' className='auth-link'>
                  Войти
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

export default Register
