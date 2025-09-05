import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import './Home.scss'

const Home = () => {
  const [pitches, setPitches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchPitches = useCallback(async () => {
    try {
      setLoading(true)

      const response = await fetch('http://localhost:8000/api/v1/pitches')

      if (!response.ok) {
        throw new Error('Ошибка загрузки выступлений')
      }
      const data = await response.json()

      setPitches(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPitches()
  }, [fetchPitches])

  const formatDate = useCallback((dateString) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }, [])

  return (
    <main className='main'>
      <div className='container'>
        <div className='content-header'>
          <h2>Ваши выступления</h2>
          <Link to='/create' className='btn-primary'>
            <button>Добавить</button>
          </Link>
        </div>

        {/* Loading State */}
        {loading && (
          <div className='loading'>
            <div className='spinner'></div>
            <p>Загрузка выступлений...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className='error'>
            <p>⚠️ {error}</p>
            <button className='btn-secondary' onClick={fetchPitches}>
              Попробовать снова
            </button>
          </div>
        )}

        {/* Pitches List */}
        {!loading && !error && (
          <>
            {pitches.length === 0 ? (
              <div className='empty-state'>
                <div className='empty-icon'>🎤</div>
                <h3>У вас пока нет выступлений</h3>
                <p>Создайте своё первое выступление, чтобы начать тренировку с AI</p>
                <Link to='/create'>
                  <button>Создать первое выступление</button>
                </Link>
              </div>
            ) : (
              <div className='pitches-grid'>
                {pitches.map((pitch) => (
                  <Link to={`/pitch/${pitch.id}`} key={pitch.id}>
                    <div className='pitch-card'>
                      <h3 className='pitch-title'>{pitch.title}</h3>
                      <div className='pitch-date'>{formatDate(pitch.created_at)}</div>
                      <p className={`pitch-description ${!pitch.description ? 'pitch-description--placeholder' : ''}`}>
                        {pitch.description}
                      </p>
                      {pitch.tags && pitch.tags.length > 0 && (
                        <div className='pitch-tags'>
                          {pitch.tags.map((tag, index) => (
                            <span key={index} className='tag'>
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </main>
  )
}

export default Home
