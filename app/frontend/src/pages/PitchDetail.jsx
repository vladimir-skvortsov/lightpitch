import { useState, useEffect, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import './PitchDetail.scss'

const PitchDetail = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [pitch, setPitch] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchPitch()
  }, [fetchPitch, id])

  const fetchPitch = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch(`http://localhost:8000/api/v1/pitches/${id}`)

      if (!response.ok) {
        throw new Error('Выступление не найдено')
      }

      const data = await response.json()
      setPitch(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [id])

  const handleDelete = useCallback(async () => {
    if (window.confirm('Вы уверены, что хотите удалить это выступление?')) {
      try {
        const response = await fetch(`http://localhost:8000/api/v1/pitches/${id}`, {
          method: 'DELETE',
        })

        if (response.ok) {
          navigate('/')
        } else {
          throw new Error('Ошибка при удалении выступления')
        }
      } catch (err) {
        setError(err.message)
      }
    }
  }, [id, navigate])

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='loading'>
            <div className='spinner'></div>
            <p>Загрузка выступления...</p>
          </div>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='error'>
            <p>⚠️ {error}</p>
            <Link to='/' className='btn-primary'>
              Вернуться на главную
            </Link>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className='main'>
      <div className='container'>
        <div className='content-header'>
          <Link to='/' className='btn-outline'>
            ← Назад к списку
          </Link>
          <div className='pitch-actions'>
            <Link to={`/pitch/${id}/edit`} className='btn-outline'>
              Редактировать
            </Link>
            <button onClick={handleDelete} className='btn-danger'>
              Удалить
            </button>
          </div>
        </div>

        {pitch && (
          <div className='pitch-detail'>
            <div className='pitch-detail-header'>
              <h1 className='pitch-detail-title'>{pitch.title}</h1>
              <span className='pitch-detail-date'>Создано: {formatDate(pitch.created_at)}</span>
              {pitch.updated_at !== pitch.created_at && (
                <span className='pitch-detail-date'>Обновлено: {formatDate(pitch.updated_at)}</span>
              )}
            </div>

            {pitch.description && (
              <div className='pitch-detail-description'>
                <h3>Описание</h3>
                <p>{pitch.description}</p>
              </div>
            )}

            {pitch.tags && pitch.tags.length > 0 && (
              <div className='pitch-detail-tags'>
                <h3>Теги</h3>
                <div className='pitch-tags'>
                  {pitch.tags.map((tag, index) => (
                    <span key={index} className='tag'>
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className='pitch-detail-content'>
              <h3>Содержание выступления</h3>
              <div className='pitch-content'>
                {pitch.content.split('\n').map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </div>
            </div>

            <div className='pitch-detail-actions'>
              <button className='btn-primary btn-large'>🎤 Начать тренировку</button>
              <button className='btn-secondary'>📊 Анализ выступления</button>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}

export default PitchDetail
