import { useParams, Link, useLocation } from 'react-router-dom'
import { useCallback } from 'react'
import Button from '../components/Button'
import './PitchResults.scss'

const PitchResults = () => {
  const { id } = useParams()
  const location = useLocation()

  // Get results from state or use hardcoded data in new format
  const analysis = location.state?.analysisResult || {
    groups: [
      {
        name: 'Речь и артикуляция',
        value: 0.82,
        metrics: [
          { label: 'Четкость речи', value: 8.5 },
          { label: 'Скорость речи (слов/мин)', value: 145 },
          { label: 'Громкость голоса', value: 8.1 },
        ],
        diagnostics: [
          {
            label: 'Четкая артикуляция',
            status: 'good',
            comment: 'Отличная четкость речи и хорошая интонация',
          },
          {
            label: 'Темп речи',
            status: 'warning',
            comment: 'Рекомендуется немного замедлить темп речи для лучшего восприятия',
          },
          {
            label: 'Профессиональная манера',
            status: 'good',
            comment: 'Профессиональная манера речи и уверенная подача',
          },
        ],
      },
      {
        name: 'Подача и презентация',
        value: 0.79,
        metrics: [
          { label: 'Уверенность', value: 8.2 },
          { label: 'Зрительный контакт', value: 8.1 },
          { label: 'Язык тела', value: 7.3 },
        ],
        diagnostics: [
          {
            label: 'Зрительный контакт',
            status: 'good',
            comment: 'Хороший зрительный контакт с аудиторией',
          },
          {
            label: 'Жестикуляция',
            status: 'warning',
            comment: 'Добавьте больше жестов для усиления эмоциональной составляющей',
          },
          {
            label: 'Уверенность',
            status: 'good',
            comment: 'Уверенная подача материала',
          },
        ],
      },
      {
        name: 'Вовлеченность аудитории',
        value: 0.75,
        metrics: [
          { label: 'Эмоциональность', value: 7.8 },
          { label: 'Интерактивность', value: 6.9 },
          { label: 'Использование пауз', value: 7.5 },
        ],
        diagnostics: [
          {
            label: 'Структура выступления',
            status: 'good',
            comment: 'Хорошая структура выступления и логичное изложение',
          },
          {
            label: 'Эмоциональная вовлеченность',
            status: 'warning',
            comment: 'Увеличьте эмоциональную вовлеченность для лучшего контакта с аудиторией',
          },
          {
            label: 'Паузы',
            status: 'warning',
            comment: 'Используйте больше пауз для акцентирования важных моментов',
          },
        ],
      },
      {
        name: 'Технические аспекты',
        value: 0.88,
        metrics: [
          { label: 'Продолжительность (мин)', value: 2.4 },
          { label: 'Количество слов', value: 287 },
          { label: 'Качество звука', value: 8.7 },
        ],
        diagnostics: [
          {
            label: 'Качество записи',
            status: 'good',
            comment: 'Хорошее качество звука и видео',
          },
          {
            label: 'Продолжительность',
            status: 'good',
            comment: 'Оптимальная продолжительность выступления',
          },
          {
            label: 'Техническое исполнение',
            status: 'good',
            comment: 'Отличное техническое качество записи',
          },
        ],
      },
    ],
    recommendations: [
      'Немного замедлите темп речи для лучшего восприятия',
      'Добавьте больше жестов для усиления эмоциональной составляющей',
      'Используйте больше пауз для акцентирования важных моментов',
      'Увеличьте эмоциональную вовлеченность с аудиторией',
      'Поддерживайте зрительный контакт на протяжении всего выступления',
    ],
    feedback:
      'Ваше выступление демонстрирует высокий профессиональный уровень с четкой артикуляцией и уверенной подачей. Основные области для улучшения: темп речи и эмоциональная вовлеченность.',
    strengths: [
      'Четкая артикуляция и профессиональная речь',
      'Хорошая структура и логика выступления',
      'Уверенная подача материала',
      'Качественный зрительный контакт с аудиторией',
      'Отличное техническое исполнение',
    ],
    areas_for_improvement: [
      'Оптимизация темпа речи',
      'Развитие языка тела и жестикуляции',
      'Использование пауз для акцентирования',
      'Повышение эмоциональной вовлеченности',
    ],
  }

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

  return (
    <main className='main'>
      <div className='container pitch-results'>
        <div className='content-header'>
          <h2 className='analysis-title'>Результаты анализа</h2>
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

          {/* Actions */}
          <div className='block'>
            <div className='results-actions'>
              <Button variant='outline' as={Link} to={`/pitch/${id}/record`}>
                🔄 Записать ещё раз
              </Button>
              <Button variant='primary' as={Link} to={`/pitch/${id}`}>
                📝 Вернуться к выступлению
              </Button>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

export default PitchResults
