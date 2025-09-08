import { useState, useEffect, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import './TrainingSessions.scss'

const TrainingSessions = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [pitch, setPitch] = useState(null)
  const [sessions, setSessions] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)

      // Fetch pitch details
      const pitchResponse = await fetch(`/api/v1/pitches/${id}`)
      if (!pitchResponse.ok) {
        throw new Error('Выступление не найдено')
      }
      const pitchData = await pitchResponse.json()
      setPitch(pitchData)

      // Fetch training sessions
      const sessionsResponse = await fetch(`/api/v1/pitches/${id}/training-sessions`)
      if (sessionsResponse.ok) {
        const sessionsData = await sessionsResponse.json()
        setSessions(sessionsData)
      }

      // Fetch stats
      const statsResponse = await fetch(`/api/v1/pitches/${id}/training-sessions/stats`)
      if (statsResponse.ok) {
        const statsData = await statsResponse.json()
        setStats(statsData)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatDuration = (seconds) => {
    if (!seconds) return 'Н/Д'
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.floor(seconds % 60)
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
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

  const getScoreColor = (score) => {
    if (!score) return 'neutral'
    if (score >= 0.8) return 'success'
    if (score >= 0.6) return 'warning'
    return 'error'
  }

  if (loading) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='loading'>
            <div className='spinner'></div>
            <p>Загрузка тренировок...</p>
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
            <Button variant='primary' as={Link} to={`/pitch/${id}`}>
              Вернуться к питчу
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
          <Button variant='outline' as={Link} to={`/pitch/${id}`}>
            ← Назад к питчу
          </Button>
          <div className='training-actions'>
            <Button variant='primary' as={Link} to={`/pitch/${id}/upload`}>
              Новая тренировка
            </Button>
          </div>
        </div>

        {pitch && (
          <div className='training-sessions-page'>
            {stats && (
              <div className='block'>
                <h2>Статистика</h2>
                <div className='stats-grid'>
                  <div className='stat-card'>
                    <div className='stat-number'>{stats.total_count}</div>
                    <div className='stat-label'>Всего тренировок</div>
                  </div>
                  <div className='stat-card'>
                    <div className={`stat-number ${getScoreColor(stats.best_score)}`}>
                      {stats.best_score ? `${Math.round(stats.best_score * 100)}%` : 'Н/Д'}
                    </div>
                    <div className='stat-label'>Лучший результат</div>
                  </div>
                  <div className='stat-card'>
                    <div className={`stat-number ${getScoreColor(stats.average_score)}`}>
                      {stats.average_score ? `${Math.round(stats.average_score * 100)}%` : 'Н/Д'}
                    </div>
                    <div className='stat-label'>Средний результат</div>
                  </div>
                  <div className='stat-card'>
                    <div className='stat-number'>{stats.total_duration_minutes}м</div>
                    <div className='stat-label'>Общее время</div>
                  </div>
                </div>
              </div>
            )}

            <div className='block'>
              <h2>История тренировок</h2>
              {sessions.length === 0 ? (
                <div className='empty-state'>
                  <div className='empty-icon'>🎯</div>
                  <h3>Пока нет тренировок</h3>
                  <p>Начните первую тренировку для этого питча</p>
                  <Button variant='primary' as={Link} to={`/pitch/${id}/upload`}>
                    Начать тренировку
                  </Button>
                </div>
              ) : (
                <div className='sessions-list'>
                  {sessions.map((session) => (
                    <div key={session.id} className='session-card'>
                      <div className='session-header'>
                        <div className='session-type'>
                          <span className='type-badge'>{getTrainingTypeLabel(session.training_type)}</span>
                          <span className='session-date'>{formatDate(session.created_at)}</span>
                        </div>
                        <div className='session-score'>
                          {session.overall_score && (
                            <span className={`score ${getScoreColor(session.overall_score)}`}>
                              {Math.round(session.overall_score * 100)}%
                            </span>
                          )}
                        </div>
                      </div>

                      <div className='session-details'>
                        <div className='session-duration'>
                          <span className='detail-label'>Длительность:</span>
                          <span className='detail-value'>{formatDuration(session.duration_seconds)}</span>
                        </div>
                        {session.notes && (
                          <div className='session-notes'>
                            <span className='detail-label'>Заметки:</span>
                            <span className='detail-value'>{session.notes}</span>
                          </div>
                        )}
                      </div>

                      <div className='session-actions'>
                        <Button
                          variant='outline'
                          size='small'
                          onClick={() => navigate(`/pitch/${id}/results?session=${session.id}`)}
                        >
                          Посмотреть результаты
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  )
}

export default TrainingSessions
