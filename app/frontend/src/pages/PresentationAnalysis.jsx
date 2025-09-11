import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import Button from '../components/Button'
import './PresentationAnalysis.scss'

const PresentationAnalysis = () => {
  const { id } = useParams()
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [improvedPresentation, setImprovedPresentation] = useState(null)

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

  const generateImprovedPresentation = useCallback(async () => {
    try {
      setGenerating(true)
      setError(null)

      const response = await fetch(`/api/v1/pitches/${id}/generate-improved-presentation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Ошибка генерации презентации')
      }

      const result = await response.json()
      setImprovedPresentation(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }, [id])


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
           <div className='header-actions'>
             {!improvedPresentation && (
               <Button 
                 variant='primary' 
                 onClick={generateImprovedPresentation}
                 disabled={generating}
                 className='generate-button'
               >
                 {generating ? 'Генерируем...' : '✨ Сгенерировать улучшенную версию'}
               </Button>
             )}
             <Button variant='outline' as={Link} to={`/pitch/${id}`} className='back-button'>
               ← Назад к выступлению
             </Button>
           </div>
        </div>


        {/* Generated Presentation Display */}
        {improvedPresentation && (
          <div className='block generated-presentation-section'>
             <h2 className='section-title'>📋 Содержание улучшенной презентации</h2>
            <div className='presentation-slides'>
              {improvedPresentation.slides.map((slide, index) => (
                <div key={index} className='slide-card'>
                  <div className='slide-header'>
                    <div className='slide-number'>{slide.slide_number}</div>
                    <h3 className='slide-title'>{slide.title}</h3>
                  </div>
                  <div className='slide-content'>
                    {slide.content.length > 0 && (
                      <div className='content-section'>
                        <h4>ОСНОВНОЕ СОДЕРЖИМОЕ:</h4>
                        {slide.content.map((content, idx) => (
                          <p key={idx} className='content-item'>{content}</p>
                        ))}
                      </div>
                    )}
                    {slide.bullet_points.length > 0 && (
                      <div className='bullets-section'>
                        <h4>КЛЮЧЕВЫЕ ПУНКТЫ:</h4>
                        <ul className='bullet-list'>
                          {slide.bullet_points.map((bullet, idx) => (
                            <li key={idx} className='bullet-item'>{bullet}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {slide.speaker_notes && (
                      <div className='speaker-notes-section'>
                        <h4>ЗАМЕТКИ ДОКЛАДЧИКА:</h4>
                        <p className='speaker-notes'>{slide.speaker_notes}</p>
                      </div>
                    )}
                    {slide.improvements_applied.length > 0 && (
                      <div className='improvements-section'>
                        <h4>ПРИМЕНЕННЫЕ УЛУЧШЕНИЯ:</h4>
                        <ul className='bullet-list'>
                          {slide.improvements_applied.map((improvement, idx) => (
                            <li key={idx} className='bullet-item'>✓ {improvement}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {slide.suggested_visuals && slide.suggested_visuals.length > 0 && (
                      <div className='visual-suggestions-section'>
                        <h4>РЕКОМЕНДУЕМЫЕ ВИЗУАЛЬНЫЕ ЭЛЕМЕНТЫ:</h4>
                        <div className='visual-elements-grid'>
                          {slide.suggested_visuals.map((visual, idx) => (
                            <div key={idx} className='visual-element-card'>
                              <div className='visual-element-header'>
                                <div className={`visual-element-icon visual-element-icon--${visual.element_type}`}>
                                  {visual.element_type === 'chart' && '📊'}
                                  {visual.element_type === 'graph' && '📈'}
                                  {visual.element_type === 'diagram' && '🔗'}
                                  {visual.element_type === 'image' && '🖼️'}
                                  {visual.element_type === 'table' && '📋'}
                                  {visual.element_type === 'icon' && '🔸'}
                                  {visual.element_type === 'infografic' && '📰'}
                                  {visual.element_type === 'timeline' && '⏱️'}
                                  {visual.element_type === 'flowchart' && '🔄'}
                                </div>
                                <div className='visual-element-info'>
                                  <h5 className='visual-element-title'>{visual.title}</h5>
                                  <span className={`visual-element-type visual-element-type--${visual.element_type}`}>
                                    {visual.element_type === 'chart' && 'Диаграмма'}
                                    {visual.element_type === 'graph' && 'График'}
                                    {visual.element_type === 'diagram' && 'Схема'}
                                    {visual.element_type === 'image' && 'Изображение'}
                                    {visual.element_type === 'table' && 'Таблица'}
                                    {visual.element_type === 'icon' && 'Иконка'}
                                    {visual.element_type === 'infografic' && 'Инфографика'}
                                    {visual.element_type === 'timeline' && 'Временная шкала'}
                                    {visual.element_type === 'flowchart' && 'Блок-схема'}
                                  </span>
                                </div>
                              </div>
                              <p className='visual-element-description'>{visual.description}</p>
                              <div className='visual-element-purpose'>
                                <strong>Цель:</strong> {visual.purpose}
                              </div>
                              {visual.data_suggestion && visual.data_suggestion.length > 0 && (
                                <div className='visual-element-data'>
                                  <strong>Рекомендуемые данные:</strong>
                                  <ul className='bullet-list'>
                                    {visual.data_suggestion.map((data, dataIdx) => (
                                      <li key={dataIdx} className='bullet-item'>{data}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {visual.chart_type && (
                                <div className='visual-element-chart-type'>
                                  <strong>Тип диаграммы:</strong> {visual.chart_type}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

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
                      {category === 'content' && 'Контент'}
                      {category === 'professionalism' && 'Профессионализм'}
                      {!['design', 'structure', 'content', 'professionalism'].includes(category) && category}
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
