import { useState, useEffect, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import Dropdown from '../components/Dropdown'
import Button from '../components/Button'
import './PitchDetail.scss'

const PitchDetail = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [pitch, setPitch] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isContentExpanded, setIsContentExpanded] = useState(false)

  const fetchPitch = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/v1/pitches/${id}`)

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

  useEffect(() => {
    fetchPitch()
  }, [fetchPitch, id])

  const handleDelete = useCallback(async () => {
    if (window.confirm('Вы уверены, что хотите удалить это выступление?')) {
      try {
        const response = await fetch(`/api/v1/pitches/${id}`, {
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
            <Button variant='primary' as={Link} to='/'>
              Вернуться на главную
            </Button>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className='main'>
      <div className='container'>
        <div className='content-header'>
          <Button variant='outline' as={Link} to='/'>
            ← Назад к списку
          </Button>
          <div className='pitch-actions'>
            <Dropdown trigger={<Button variant='primary'>Начать тренировку</Button>}>
              <Link to={`/pitch/${id}/record`} className='dropdown-item'>
                Записать видео
              </Link>
              <Link to={`/pitch/${id}/upload`} className='dropdown-item'>
                Загрузить видео
              </Link>
            </Dropdown>
            <Dropdown
              trigger={
                <Button className='w-[46px]'>
                  <span className='more-dots'>⋯</span>
                </Button>
              }
            >
              <Link to={`/pitch/${id}/edit`} className='dropdown-item'>
                Редактировать
              </Link>
              <button onClick={handleDelete} className='dropdown-item dropdown-item--danger'>
                Удалить
              </button>
            </Dropdown>
          </div>
        </div>

        {pitch && (
          <div className='pitch-detail'>
            <div className='block'>
              <h1 className='pitch-detail-title'>{pitch.title}</h1>
              <span className='pitch-detail-date'>Создано: {formatDate(pitch.created_at)}</span>
            </div>

            {pitch.description && (
              <div className='block'>
                <h3>Описание</h3>
                <p>{pitch.description}</p>
              </div>
            )}

            {pitch.planned_duration_minutes && (
              <div className='block'>
                <h3>Планируемая длительность</h3>
                <p>{pitch.planned_duration_minutes} мин</p>
              </div>
            )}

            {pitch.tags && pitch.tags.length > 0 && (
              <div className='block'>
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

            {pitch.presentation_file_name && (
              <div className='block'>
                <div className='pitch-detail-presentation'>
                  <h3>Презентация</h3>
                  <div
                    className='presentation-card clickable-card'
                    onClick={() => navigate(`/pitch/${id}/presentation-analysis`)}
                  >
                    <div className='presentation-info'>
                      <div className='presentation-file'>
                        <span className='file-icon'>📄</span>
                        <div className='file-details'>
                          <span className='file-name'>{pitch.presentation_file_name}</span>
                          <span className='file-type'>Презентационный файл</span>
                        </div>
                      </div>
                      <div className='presentation-arrow'>
                        <span className='arrow-icon'>→</span>
                      </div>
                    </div>
                    <div className='presentation-counters'>
                      <div className='counter counter--success'>
                        <span className='counter-icon'>✓</span>
                        <span className='counter-number'>10</span>
                      </div>
                      <div className='counter counter--warning'>
                        <span className='counter-icon'>⚠</span>
                        <span className='counter-number'>2</span>
                      </div>
                      <div className='counter counter--error'>
                        <span className='counter-icon'>✕</span>
                        <span className='counter-number'>1</span>
                      </div>
                    </div>
                  </div>
                  <div className='presentation-actions'>
                    <Button
                      variant='outline'
                      onClick={(e) => {
                        e.stopPropagation()
                        window.open(`/api/v1/pitches/${id}/presentation`, '_blank')
                      }}
                    >
                      Скачать
                    </Button>
                  </div>
                </div>
              </div>
            )}

            <div className='block'>
              <div className='pitch-detail-speech'>
                <h3>Текст выступления</h3>
                <div className='speech-card clickable-card' onClick={() => navigate(`/pitch/${id}/speech-analysis`)}>
                  <div className='speech-info'>
                    <div className='speech-preview'>
                      <div
                        className={`pitch-content ${
                          !isContentExpanded ? 'pitch-content--collapsed' : 'pitch-content--expanded'
                        }`}
                      >
                        <div className='pitch-content-text'>
                          {pitch.content.split('\n').map((paragraph, index) => (
                            <p key={index}>{paragraph}</p>
                          ))}
                        </div>
                        {!isContentExpanded && pitch.content.length > 500 && (
                          <div className='pitch-content-gradient'></div>
                        )}
                      </div>
                    </div>
                    <div className='speech-arrow'>
                      <span className='arrow-icon'>→</span>
                    </div>
                  </div>
                  <div className='speech-counters'>
                    <div className='counter counter--success'>
                      <span className='counter-icon'>✓</span>
                      <span className='counter-number'>6</span>
                    </div>
                    <div className='counter counter--warning'>
                      <span className='counter-icon'>⚠</span>
                      <span className='counter-number'>7</span>
                    </div>
                    <div className='counter counter--error'>
                      <span className='counter-icon'>✕</span>
                      <span className='counter-number'>1</span>
                    </div>
                  </div>
                </div>
                {pitch.content.length > 500 && (
                  <Button
                    variant='outline'
                    onClick={(e) => {
                      e.stopPropagation()
                      setIsContentExpanded(!isContentExpanded)
                    }}
                    className='content-toggle-btn'
                  >
                    {isContentExpanded ? '🔼 Свернуть' : '🔽 Показать полностью'}
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}

export default PitchDetail
