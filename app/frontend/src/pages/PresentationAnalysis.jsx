import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import Button from '../components/Button'
import './PresentationAnalysis.scss'

const PresentationAnalysis = () => {
  const { id } = useParams()
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)

      const analysisResponse = await fetch(`/api/v1/pitches/${id}/presentation-analysis`)
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

  const getScoreColor = useCallback((score) => {
    if (score >= 0.9) return 'var(--score-excellent)'
    if (score >= 0.75) return 'var(--score-good)'
    if (score >= 0.5) return 'var(--score-average)'
    return 'var(--score-poor)'
  }, [])

  const formatScore = useCallback((score) => {
    return Math.round(score * 100)
  }, [])

  const getStatusIcon = useCallback((status) => {
    switch (status) {
      case 'good':
        return '✓'
      case 'warning':
        return '⚠'
      case 'error':
        return '✕'
      default:
        return '•'
    }
  }, [])

  const scrollToSection = useCallback((groupIndex) => {
    const element = document.getElementById(`group-section-${groupIndex}`)
    if (element) {
      element.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
        inline: 'nearest',
      })
    }
  }, [])

  if (loading) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='loading'>
            <div className='spinner'></div>
            <p>Загружаем анализ презентации...</p>
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

  return (
    <main className='main'>
      <div className='container presentation-analysis'>
        <div className='content-header'>
          <h2 className='analysis-title'>Анализ презентации</h2>
          <Button variant='outline' as={Link} to={`/pitch/${id}`} className='back-button'>
            ← Назад к выступлению
          </Button>
        </div>

        <div className='content-container'>
          <div className='block group-scores'>
            {analysis.groups.map((group, index) => (
              <div
                key={index}
                className='group-score-card'
                onClick={() => scrollToSection(index)}
                role='button'
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    scrollToSection(index)
                  }
                }}
              >
                <div className='group-header'>
                  <div className='group-score'>
                    <div className='score-circle' style={{ borderColor: getScoreColor(group.value) }}>
                      <span className='score-number'>{formatScore(group.value)}</span>
                    </div>
                  </div>
                  <h3 className='group-name'>{group.name}</h3>
                </div>
              </div>
            ))}
          </div>

          {analysis.groups.map((group, groupIndex) => (
            <div key={groupIndex} className='block' id={`group-section-${groupIndex}`}>
              <div className='group-section-header'>
                <div className='group-header'>
                  <div className='score-circle' style={{ borderColor: getScoreColor(group.value) }}>
                    <span className='score-number'>{formatScore(group.value)}</span>
                  </div>
                  <h3 className='group-name'>{group.name}</h3>
                </div>
              </div>

              {/* Metrics */}
              {group.metrics && group.metrics.length > 0 && (
                <div className='metrics-section'>
                  <h4>Метрики</h4>
                  <div className='metrics-list'>
                    {group.metrics.map((metric, metricIndex) => (
                      <div key={metricIndex} className='metric-item'>
                        <span className='metric-label'>{metric.label}</span>
                        <span className='metric-value'>{metric.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Diagnostics */}
              {group.diagnostics && group.diagnostics.length > 0 && (
                <div className='diagnostics-section'>
                  <h4>Диагностика</h4>
                  <div className='diagnostics-list'>
                    {group.diagnostics.map((diagnostic, diagIndex) => (
                      <div key={diagIndex} className={`diagnostic-item diagnostic-item--${diagnostic.status}`}>
                        <div className='diagnostic-header'>
                          <span className='diagnostic-icon'>{getStatusIcon(diagnostic.status)}</span>
                          <span className='diagnostic-label'>{diagnostic.label}</span>
                          {diagnostic.sublabel && <span className='diagnostic-sublabel'>• {diagnostic.sublabel}</span>}
                        </div>
                        {diagnostic.comment && <p className='diagnostic-comment'>{diagnostic.comment}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Feedback */}
          {analysis.feedback && (
            <div className='block'>
              <h2 className='section-title'>💬 Общая оценка</h2>
              <div className='section-content'>
                <p className='feedback-text'>{analysis.feedback}</p>
              </div>
            </div>
          )}

          {/* Strengths */}
          {analysis.strengths && analysis.strengths.length > 0 && (
            <div className='block'>
              <h2 className='section-title section-title--success'>💪 Сильные стороны</h2>
              <div className='section-content'>
                <ul className='strengths-list'>
                  {analysis.strengths.map((strength, index) => (
                    <li key={index} className='strength-item'>
                      {strength}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Areas for improvement */}
          {analysis.areas_for_improvement && analysis.areas_for_improvement.length > 0 && (
            <div className='block'>
              <h2 className='section-title section-title--warning'>🎯 Области для улучшения</h2>
              <div className='section-content'>
                <ul className='improvements-list'>
                  {analysis.areas_for_improvement.map((area, index) => (
                    <li key={index} className='improvement-item'>
                      {area}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Recommendations */}
          {analysis.recommendations && analysis.recommendations.length > 0 && (
            <div className='block'>
              <h2 className='section-title section-title--info'>💡 Рекомендации</h2>
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
          )}
        </div>
      </div>
    </main>
  )
}

export default PresentationAnalysis
