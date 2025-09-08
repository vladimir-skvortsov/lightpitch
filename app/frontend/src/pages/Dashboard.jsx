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
                Создать питч
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
              <div className='pitches-section'>
                <h2>Ваши питчи ({pitches.length})</h2>
                <div className='pitches-grid'>
                  {pitches.map((pitch) => (
                    <div key={pitch.id} className='pitch-card'>
                      <div className='pitch-card-header'>
                        <h3 className='pitch-title'>{pitch.title}</h3>
                        <span className='pitch-date'>{formatDate(pitch.created_at)}</span>
                      </div>

                      <div className='pitch-description'>
                        <p>{pitch.description || 'Описание отсутствует'}</p>
                      </div>

                      <div className='pitch-meta'>
                        <div className='pitch-duration'>
                          <span className='meta-label'>Длительность:</span>
                          <span className='meta-value'>{pitch.planned_duration_minutes} мин</span>
                        </div>

                        {pitch.tags && pitch.tags.length > 0 && (
                          <div className='pitch-tags'>
                            {pitch.tags.slice(0, 3).map((tag, index) => (
                              <span key={index} className='tag'>
                                {tag}
                              </span>
                            ))}
                            {pitch.tags.length > 3 && <span className='tag-more'>+{pitch.tags.length - 3}</span>}
                          </div>
                        )}
                      </div>

                      <div className='pitch-actions'>
                        <Button variant='primary' as={Link} to={`/pitch/${pitch.id}`} size='small'>
                          Открыть
                        </Button>
                        <Button variant='outline' as={Link} to={`/pitch/${pitch.id}/edit`} size='small'>
                          Редактировать
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  )
}

export default Dashboard
