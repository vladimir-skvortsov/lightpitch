import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import Button from '../components/Button'
import './Dashboard.scss'

const Dashboard = () => {
  const { getAuthHeaders } = useAuth()
  const [pitches, setPitches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchPitches = async () => {
      try {
        const response = await fetch('/api/v1/pitches/', {
          headers: getAuthHeaders(),
        })

        if (response.ok) {
          const data = await response.json()
          setPitches(data)
        } else {
          throw new Error('Failed to fetch pitches')
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchPitches()
  }, [getAuthHeaders])

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  if (loading) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='loading'>
            <div className='spinner'></div>
            <p>Загрузка питчей...</p>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className='main'>
      <div className='container'>
        <div className='dashboard-page'>
          <div className='dashboard-header'>
            <div className='welcome-section'>
              <h1>Ваши выступления</h1>
            </div>
            <div className='header-actions'>
              <Button variant='primary' as={Link} to='/create'>
                Добавить
              </Button>
            </div>
          </div>

          {error && <div className='error-message'>⚠️ {error}</div>}

          <div className='dashboard-content'>
            {pitches.length === 0 ? (
              <div className='empty-state'>
                <div className='empty-icon'>🎯</div>
                <h3>У вас пока нет питчей</h3>
                <p>Создайте свой первый питч и начните улучшать навыки выступлений</p>
                <Button variant='primary' as={Link} to='/create'>
                  Создать первый питч
                </Button>
              </div>
            ) : (
              <div className='pitches-grid'>
                {pitches.map((pitch) => (
                  <Link to={`/pitch/${pitch.id}`} key={pitch.id}>
                    <div className='pitch-card'>
                      <h3 className='pitch-title'>{pitch.title}</h3>
                      <div className='pitch-date'>{formatDate(pitch.created_at)}</div>
                      {pitch.tags && pitch.tags.length > 0 && (
                        <div className='pitch-tags'>
                          {pitch.tags.map((tag, index) => (
                            <span key={index} className='tag'>
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                      <p className={`pitch-description ${!pitch.description ? 'pitch-description--placeholder' : ''}`}>
                        {pitch.description}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  )
}

export default Dashboard
