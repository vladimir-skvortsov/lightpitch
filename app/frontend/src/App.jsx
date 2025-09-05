import { useState, useEffect } from 'react'
import './App.scss'

const App = () => {
  const [pitches, setPitches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchPitches()
  }, [])

  const fetchPitches = async () => {
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
  }

  const handleAddPitch = () => {
    // TODO: Реализовать в следующей итерации
    alert('Создание выступлений будет реализовано в следующей итерации')
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className='app'>
      {/* Header */}
      <header className='header'>
        <div className='container'>
          <h1 className='logo'>
            <span className='logo-light'>лайт</span>
            <span className='logo-pitch'>питч</span>
          </h1>
          <p className='subtitle'>AI-помощник для презентаций и питчей</p>
        </div>
      </header>

      {/* Main Content */}
      <main className='main'>
        <div className='container'>
          <div className='content-header'>
            <h2>Ваши выступления</h2>
            <button className='btn-primary' onClick={handleAddPitch}>
              Добавить
            </button>
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
                  <button className='btn-primary' onClick={handleAddPitch}>
                    Создать первое выступление
                  </button>
                </div>
              ) : (
                <div className='pitches-grid'>
                  {pitches.map((pitch) => (
                    <div key={pitch.id} className='pitch-card'>
                      <div className='pitch-header'>
                        <h3 className='pitch-title'>{pitch.title}</h3>
                        <span className='pitch-date'>{formatDate(pitch.created_at)}</span>
                      </div>
                      {pitch.description && <p className='pitch-description'>{pitch.description}</p>}
                      {pitch.tags && pitch.tags.length > 0 && (
                        <div className='pitch-tags'>
                          {pitch.tags.map((tag, index) => (
                            <span key={index} className='tag'>
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className='pitch-actions'>
                        <button className='btn-outline'>Редактировать</button>
                        <button className='btn-primary'>Начать тренировку</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
