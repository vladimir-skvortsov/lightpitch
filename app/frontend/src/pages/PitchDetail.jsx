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
  const [trainingStats, setTrainingStats] = useState(null)
  const [questionsStats, setQuestionsStats] = useState(null)

  const fetchPitch = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/v1/pitches/${id}`)

      if (!response.ok) {
        throw new Error('Выступление не найдено')
      }

      const data = await response.json()
      setPitch(data)

      // Fetch training sessions stats
      try {
        const trainingResponse = await fetch(`/api/v1/pitches/${id}/training-sessions/stats`)
        if (trainingResponse.ok) {
          const trainingData = await trainingResponse.json()
          setTrainingStats(trainingData)
        }
      } catch (err) {
        console.warn('Failed to fetch training stats:', err)
      }

      // Fetch hypothetical questions stats
      try {
        const questionsResponse = await fetch(`/api/v1/pitches/${id}/hypothetical-questions/stats`)
        if (questionsResponse.ok) {
          const questionsData = await questionsResponse.json()
          setQuestionsStats(questionsData)
        }
      } catch (err) {
        console.warn('Failed to fetch questions stats:', err)
      }
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

  const formatShortDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getTrainingTypeLabel = (type) => {
    switch (type) {
      case 'video_upload':
        return 'Загрузка видео'
      case 'video_record':
        return 'Запись видео'
      case 'audio_only':
        return 'Только аудио'
      default:
        return type
    }
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
              Вернуться к питчам
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
            ← Назад к питчам
          </Button>
          <div className='pitch-actions'>
            <Dropdown trigger={<Button variant='primary'>Начать тренировку</Button>}>
              <Link to={`/pitch/${id}/upload`} className='dropdown-item'>
                Загрузить видео
              </Link>
              <Link to={`/pitch/${id}/record`} className='dropdown-item'>
                Записать видео
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

            {/* Training Sessions Widget */}
            <div className='block'>
              <div className='pitch-detail-training'>
                <h3>Мои тренировки</h3>
                <div
                  className='training-card clickable-card'
                  onClick={() => navigate(`/pitch/${id}/training-sessions`)}
                >
                  <div className='training-info'>
                    <div className='training-overview'>
                      <div className='training-icon'>
                        <span className='icon'>🎯</span>
                        <div className='training-details'>
                          <span className='training-title'>
                            {trainingStats?.total_count > 0
                              ? `${trainingStats.total_count} тренировок`
                              : 'Нет тренировок'}
                          </span>
                          <span className='training-subtitle'>
                            {trainingStats?.latest_session
                              ? `Последняя: ${formatShortDate(trainingStats.latest_session.created_at)}`
                              : 'Начните первую тренировку'}
                          </span>
                        </div>
                      </div>
                      <div className='training-arrow'>
                        <span className='arrow-icon'>→</span>
                      </div>
                    </div>
                  </div>
                  <div className='training-counters'>
                    <div className='counter counter--info'>
                      <span className='counter-icon'>📊</span>
                      <span className='counter-number'>{trainingStats?.total_count || 0}</span>
                    </div>
                    {trainingStats?.best_score && (
                      <div className='counter counter--success'>
                        <span className='counter-icon'>🏆</span>
                        <span className='counter-number'>{Math.round(trainingStats.best_score * 100)}%</span>
                      </div>
                    )}
                    {trainingStats?.latest_session?.training_type && (
                      <div className='counter counter--neutral'>
                        <span className='counter-icon'>📹</span>
                        <span className='counter-text'>
                          {getTrainingTypeLabel(trainingStats.latest_session.training_type)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Hypothetical Questions Widget */}
            <div className='block'>
              <div className='pitch-detail-questions'>
                <h3>Гипотетические вопросы</h3>
                <div
                  className='questions-card clickable-card'
                  onClick={() => navigate(`/pitch/${id}/hypothetical-questions`)}
                >
                  <div className='questions-info'>
                    <div className='questions-overview'>
                      <div className='questions-icon'>
                        <span className='icon'>❓</span>
                        <div className='questions-details'>
                          <span className='questions-title'>
                            {questionsStats?.total_count > 0
                              ? `${questionsStats.total_count} вопросов`
                              : 'Нет вопросов'}
                          </span>
                          <span className='questions-subtitle'>
                            {questionsStats?.latest_question
                              ? `Последний: ${formatShortDate(questionsStats.latest_question.created_at)}`
                              : 'Сгенерируйте вопросы для подготовки'}
                          </span>
                        </div>
                      </div>
                      <div className='questions-arrow'>
                        <span className='arrow-icon'>→</span>
                      </div>
                    </div>
                  </div>
                  <div className='questions-counters'>
                    <div className='counter counter--info'>
                      <span className='counter-icon'>📝</span>
                      <span className='counter-number'>{questionsStats?.total_count || 0}</span>
                    </div>
                    {questionsStats?.by_difficulty?.easy && (
                      <div className='counter counter--success'>
                        <span className='counter-icon'>😊</span>
                        <span className='counter-number'>{questionsStats.by_difficulty.easy}</span>
                      </div>
                    )}
                    {questionsStats?.by_difficulty?.medium && (
                      <div className='counter counter--warning'>
                        <span className='counter-icon'>😐</span>
                        <span className='counter-number'>{questionsStats.by_difficulty.medium}</span>
                      </div>
                    )}
                    {questionsStats?.by_difficulty?.hard && (
                      <div className='counter counter--error'>
                        <span className='counter-icon'>😰</span>
                        <span className='counter-number'>{questionsStats.by_difficulty.hard}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

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
