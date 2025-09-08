import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import Button from '../components/Button'
import Dropdown from '../components/Dropdown'
import './HypotheticalQuestions.scss'

const HypotheticalQuestions = () => {
  const { id } = useParams()
  const [pitch, setPitch] = useState(null)
  const [questions, setQuestions] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedQuestions, setExpandedQuestions] = useState(new Set())
  const [generatingQuestions, setGeneratingQuestions] = useState(false)

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

      // Fetch hypothetical questions
      const questionsResponse = await fetch(`/api/v1/pitches/${id}/hypothetical-questions`)
      if (questionsResponse.ok) {
        const questionsData = await questionsResponse.json()
        setQuestions(questionsData)
      }

      // Fetch stats
      const statsResponse = await fetch(`/api/v1/pitches/${id}/hypothetical-questions/stats`)
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

  const generateQuestions = async (count = 5) => {
    try {
      setGeneratingQuestions(true)
      const response = await fetch(`/api/v1/pitches/${id}/hypothetical-questions/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ count }),
      })

      if (response.ok) {
        await fetchData() // Refresh the data
      } else {
        throw new Error('Ошибка при генерации вопросов')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setGeneratingQuestions(false)
    }
  }

  const toggleQuestionExpansion = (questionId) => {
    const newExpanded = new Set(expandedQuestions)
    if (newExpanded.has(questionId)) {
      newExpanded.delete(questionId)
    } else {
      newExpanded.add(questionId)
    }
    setExpandedQuestions(newExpanded)
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getCategoryLabel = (category) => {
    const labels = {
      business: 'Бизнес',
      technical: 'Техническое',
      personal: 'Личное',
      strategy: 'Стратегия',
      finance: 'Финансы',
      product: 'Продукт',
      market: 'Рынок',
      team: 'Команда',
    }
    return labels[category] || category
  }

  const getDifficultyLabel = (difficulty) => {
    const labels = {
      easy: 'Легкий',
      medium: 'Средний',
      hard: 'Сложный',
    }
    return labels[difficulty] || difficulty
  }

  const getDifficultyColor = (difficulty) => {
    switch (difficulty) {
      case 'easy':
        return 'success'
      case 'medium':
        return 'warning'
      case 'hard':
        return 'error'
      default:
        return 'neutral'
    }
  }

  if (loading) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='loading'>
            <div className='spinner'></div>
            <p>Загрузка вопросов...</p>
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
          <div className='questions-actions'>
            <Dropdown
              trigger={
                <Button variant='primary' disabled={generatingQuestions}>
                  {generatingQuestions ? 'Генерация...' : 'Сгенерировать вопросы'}
                </Button>
              }
            >
              <button className='dropdown-item' onClick={() => generateQuestions(3)} disabled={generatingQuestions}>
                3 вопроса
              </button>
              <button className='dropdown-item' onClick={() => generateQuestions(5)} disabled={generatingQuestions}>
                5 вопросов
              </button>
              <button className='dropdown-item' onClick={() => generateQuestions(10)} disabled={generatingQuestions}>
                10 вопросов
              </button>
            </Dropdown>
          </div>
        </div>

        {pitch && (
          <div className='hypothetical-questions-page'>
            <div className='block'>
              <h1>Гипотетические вопросы: {pitch.title}</h1>
              <p className='pitch-description'>{pitch.description}</p>
            </div>

            {stats && (
              <div className='block'>
                <h2>Статистика</h2>
                <div className='stats-grid'>
                  <div className='stat-card'>
                    <div className='stat-number'>{stats.total_count}</div>
                    <div className='stat-label'>Всего вопросов</div>
                  </div>
                  <div className='stat-card'>
                    <div className='stat-number'>{Object.keys(stats.by_category || {}).length}</div>
                    <div className='stat-label'>Категорий</div>
                  </div>
                  <div className='stat-card'>
                    <div className='stat-details'>
                      {Object.entries(stats.by_difficulty || {}).map(([difficulty, count]) => (
                        <div key={difficulty} className='difficulty-stat'>
                          <span className={`difficulty-badge ${difficulty}`}>{getDifficultyLabel(difficulty)}</span>
                          <span className='difficulty-count'>{count}</span>
                        </div>
                      ))}
                    </div>
                    <div className='stat-label'>По сложности</div>
                  </div>
                  <div className='stat-card'>
                    <div className='stat-details'>
                      {Object.entries(stats.by_category || {})
                        .slice(0, 3)
                        .map(([category, count]) => (
                          <div key={category} className='category-stat'>
                            <span className='category-name'>{getCategoryLabel(category)}</span>
                            <span className='category-count'>{count}</span>
                          </div>
                        ))}
                    </div>
                    <div className='stat-label'>Топ категории</div>
                  </div>
                </div>
              </div>
            )}

            <div className='block'>
              <h2>Вопросы для подготовки</h2>
              {questions.length === 0 ? (
                <div className='empty-state'>
                  <div className='empty-icon'>❓</div>
                  <h3>Пока нет вопросов</h3>
                  <p>Сгенерируйте гипотетические вопросы для подготовки к выступлению</p>
                  <Button variant='primary' onClick={() => generateQuestions(5)} disabled={generatingQuestions}>
                    {generatingQuestions ? 'Генерация...' : 'Сгенерировать вопросы'}
                  </Button>
                </div>
              ) : (
                <div className='questions-list'>
                  {questions.map((question) => (
                    <div key={question.id} className='question-card'>
                      <div className='question-header'>
                        <div className='question-meta'>
                          <span className='category-badge'>{getCategoryLabel(question.category)}</span>
                          <span className={`difficulty-badge ${question.difficulty}`}>
                            {getDifficultyLabel(question.difficulty)}
                          </span>
                          <span className='question-date'>{formatDate(question.created_at)}</span>
                        </div>
                      </div>

                      <div className='question-content'>
                        <h3 className='question-text'>{question.question_text}</h3>

                        {question.context && (
                          <div className='question-context'>
                            <strong>Контекст:</strong> {question.context}
                          </div>
                        )}

                        <div className='question-actions'>
                          <Button variant='outline' size='small' onClick={() => toggleQuestionExpansion(question.id)}>
                            {expandedQuestions.has(question.id) ? '🔼 Свернуть' : '🔽 Показать детали'}
                          </Button>
                        </div>

                        {expandedQuestions.has(question.id) && (
                          <div className='question-expanded'>
                            {question.suggested_answer && (
                              <div className='suggested-answer'>
                                <h4>Предлагаемый ответ:</h4>
                                <p>{question.suggested_answer}</p>
                              </div>
                            )}

                            {question.preparation_tips && question.preparation_tips.length > 0 && (
                              <div className='preparation-tips'>
                                <h4>Советы по подготовке:</h4>
                                <ul>
                                  {question.preparation_tips.map((tip, index) => (
                                    <li key={index}>{tip}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
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

export default HypotheticalQuestions
