import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import Button from '../components/Button'
import './SpeechAnalysis.scss'

const SpeechAnalysis = () => {
  const { id } = useParams()
  const [pitch, setPitch] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)

      const pitchResponse = await fetch(`/api/v1/pitches/${id}`)
      if (!pitchResponse.ok) {
        throw new Error('Pitch not found')
      }
      const pitchData = await pitchResponse.json()
      setPitch(pitchData)

      const analysisResponse = await fetch(`/api/v1/pitches/${id}/text`)
      if (!analysisResponse.ok) {
        throw new Error('Analysis not available')
      }
      const analysisData = await analysisResponse.json()
      setAnalysis(analysisData)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  if (loading) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='loading'>
            <div className='spinner'></div>
            <p>Загружаем анализ речи...</p>
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
              Вернуться к выступлению
            </Button>
          </div>
        </div>
      </main>
    )
  }

  const getScoreColor = (score) => {
    if (score >= 80) return 'var(--score-excellent)'
    if (score >= 60) return 'var(--score-good)'
    if (score >= 40) return 'var(--score-average)'
    return 'var(--score-poor)'
  }

  return (
    <main className='main'>
      <div className='container'>
        <div className='speech-analysis'>
          <div className='analysis-header'>
            <Button variant='outline' as={Link} to={`/pitch/${id}`} className='back-button'>
              ← Назад к выступлению
            </Button>
            <div className='header-content'>
              <h1 className='analysis-title'>Анализ текста выступления</h1>
              <p className='pitch-title'>{pitch?.title}</p>
            </div>
          </div>

          {analysis && (
            <>
              <div className='analysis-overview'>
                <div className='score-section'>
                  <div className='score-circle' style={{ borderColor: getScoreColor(analysis.overall_score) }}>
                    <div className='score-number'>{analysis.overall_score}</div>
                    <div className='score-label'>из 100</div>
                  </div>
                  <div className='score-description'>
                    <h3>Общая оценка речи</h3>
                    <p>Анализ структуры, стиля и содержания вашего выступления</p>
                  </div>
                </div>

                <div className='summary-cards'>
                  <div className='summary-card summary-card--success'>
                    <div className='card-header'>
                      <span className='card-icon'>✓</span>
                      <span className='card-title'>Хорошие практики</span>
                    </div>
                    <div className='card-count'>{analysis.good_practices.length}</div>
                  </div>

                  <div className='summary-card summary-card--warning'>
                    <div className='card-header'>
                      <span className='card-icon'>⚠</span>
                      <span className='card-title'>Предупреждения</span>
                    </div>
                    <div className='card-count'>{analysis.warnings.length}</div>
                  </div>

                  <div className='summary-card summary-card--error'>
                    <div className='card-header'>
                      <span className='card-icon'>✕</span>
                      <span className='card-title'>Ошибки</span>
                    </div>
                    <div className='card-count'>{analysis.errors.length}</div>
                  </div>
                </div>
              </div>

              <div className='analysis-sections'>
                {/* Good Practices */}
                <div className='analysis-section'>
                  <h2 className='section-title section-title--success'>
                    <span className='section-icon'>✓</span>
                    Хорошие практики ({analysis.good_practices.length})
                  </h2>
                  <div className='section-content'>
                    {analysis.good_practices.map((item, index) => (
                      <div key={index} className='analysis-item analysis-item--success'>
                        <div className='item-header'>
                          <span className='item-icon'>✓</span>
                          <h3 className='item-title'>{item.title}</h3>
                        </div>
                        <p className='item-description'>{item.description}</p>
                        <div className='item-meta'>
                          <span className='item-category'>{item.category}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Warnings */}
                <div className='analysis-section'>
                  <h2 className='section-title section-title--warning'>
                    <span className='section-icon'>⚠</span>
                    Предупреждения ({analysis.warnings.length})
                  </h2>
                  <div className='section-content'>
                    {analysis.warnings.map((item, index) => (
                      <div key={index} className='analysis-item analysis-item--warning'>
                        <div className='item-header'>
                          <span className='item-icon'>⚠</span>
                          <h3 className='item-title'>{item.title}</h3>
                        </div>
                        <p className='item-description'>{item.description}</p>
                        <div className='item-meta'>
                          <span className='item-category'>{item.category}</span>
                          {item.position && <span className='item-position'>Позиция: {item.position}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Errors */}
                <div className='analysis-section'>
                  <h2 className='section-title section-title--error'>
                    <span className='section-icon'>✕</span>
                    Ошибки ({analysis.errors.length})
                  </h2>
                  <div className='section-content'>
                    {analysis.errors.map((item, index) => (
                      <div key={index} className='analysis-item analysis-item--error'>
                        <div className='item-header'>
                          <span className='item-icon'>✕</span>
                          <h3 className='item-title'>{item.title}</h3>
                        </div>
                        <p className='item-description'>{item.description}</p>
                        <div className='item-meta'>
                          <span className='item-category'>{item.category}</span>
                          {item.position && <span className='item-position'>Позиция: {item.position}</span>}
                          {item.severity && (
                            <span className={`item-severity item-severity--${item.severity}`}>
                              {item.severity === 'high' ? 'Высокая' : item.severity === 'medium' ? 'Средняя' : 'Низкая'}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recommendations */}
                <div className='analysis-section'>
                  <h2 className='section-title section-title--info'>
                    <span className='section-icon'>💡</span>
                    Рекомендации
                  </h2>
                  <div className='section-content'>
                    <ul className='recommendations-list'>
                      {analysis.recommendations.map((recommendation, index) => (
                        <li key={index} className='recommendation-item'>
                          {recommendation}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </main>
  )
}

export default SpeechAnalysis
