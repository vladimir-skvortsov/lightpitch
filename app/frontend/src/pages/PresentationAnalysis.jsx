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
          {/* Overall Score Section */}
          <div className='block overall-score-section'>
            <div className='overall-score-card'>
              <div className='score-display'>
                <div
                  className='score-circle large'
                  style={{ borderColor: getScoreColor((analysis.overall_score || 0) / 100) }}
                >
                  <span className='score-number large'>{analysis.overall_score || 0}</span>
                  <span className='score-label'>из 100</span>
                </div>
              </div>
              <div className='score-details'>
                <h2>Общая оценка презентации</h2>
                <div className='analysis-meta'>
                  <span className='filename'>📄 {analysis.filename || 'Презентация'}</span>
                  <span className='slides-count'>📊 {analysis.total_slides || 0} слайдов</span>
                  {analysis.analysis_method && <span className='analysis-method'>🤖 {analysis.analysis_method}</span>}
                </div>
              </div>
            </div>
          </div>

          {/* Category Scores (if available) */}
          {analysis.category_scores && Object.keys(analysis.category_scores).length > 0 && (
            <div className='block category-scores'>
              <h3>Оценки по категориям</h3>
              <div className='category-grid'>
                {Object.entries(analysis.category_scores).map(([category, score]) => (
                  <div key={category} className='category-card'>
                    <div className='category-score'>
                      <div className='score-circle' style={{ borderColor: getScoreColor(score / 10) }}>
                        <span className='score-number'>{Math.round(score * 10)}</span>
                      </div>
                    </div>
                    <h4 className='category-name'>
                      {category === 'design' && 'Дизайн'}
                      {category === 'structure' && 'Структура'}
                      {category === 'readability' && 'Читаемость'}
                      {category === 'professionalism' && 'Профессионализм'}
                      {!['design', 'structure', 'readability', 'professionalism'].includes(category) && category}
                    </h4>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Good Practices Section */}
          {analysis.good_practices && analysis.good_practices.length > 0 && (
            <div className='block good-practices-section'>
              <h2 className='section-title section-title--success'>✅ Хорошие практики</h2>
              <div className='practices-grid'>
                {analysis.good_practices.map((practice, index) => (
                  <div key={index} className='practice-card practice-card--good'>
                    <div className='practice-header'>
                      <span className='practice-icon'>✓</span>
                      <h4 className='practice-title'>{practice.title}</h4>
                      <span className='practice-category'>{practice.category}</span>
                    </div>
                    <p className='practice-description'>{practice.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Warnings Section */}
          {analysis.warnings && analysis.warnings.length > 0 && (
            <div className='block warnings-section'>
              <h2 className='section-title section-title--warning'>⚠️ Предупреждения</h2>
              <div className='warnings-list'>
                {analysis.warnings.map((warning, index) => (
                  <div key={index} className='warning-card'>
                    <div className='warning-header'>
                      <span className='warning-icon'>⚠</span>
                      <h4 className='warning-title'>{warning.title}</h4>
                      <span className='warning-category'>{warning.category}</span>
                    </div>
                    <p className='warning-description'>{warning.description}</p>
                    {warning.slides && warning.slides.length > 0 && (
                      <div className='affected-slides'>
                        <span>Затронутые слайды: {warning.slides.join(', ')}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Errors Section */}
          {analysis.errors && analysis.errors.length > 0 && (
            <div className='block errors-section'>
              <h2 className='section-title section-title--error'>❌ Критические проблемы</h2>
              <div className='errors-list'>
                {analysis.errors.map((error, index) => (
                  <div key={index} className='error-card'>
                    <div className='error-header'>
                      <span className='error-icon'>✕</span>
                      <h4 className='error-title'>{error.title}</h4>
                      <span className='error-category'>{error.category}</span>
                      {error.severity && (
                        <span className={`severity-badge severity-${error.severity}`}>
                          {error.severity === 'high' ? 'Высокая' : error.severity}
                        </span>
                      )}
                    </div>
                    <p className='error-description'>{error.description}</p>
                    {error.slides && error.slides.length > 0 && (
                      <div className='affected-slides'>
                        <span>Затронутые слайды: {error.slides.join(', ')}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Legacy group-based format support */}
          {analysis.groups && analysis.groups.length > 0 && (
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
          )}

          {analysis.groups &&
            analysis.groups.map((group, groupIndex) => (
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
                            {diagnostic.sublabel && (
                              <span className='diagnostic-sublabel'>• {diagnostic.sublabel}</span>
                            )}
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
