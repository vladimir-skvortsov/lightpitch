import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import Button from '../components/Button'
import './SpeechAnalysis.scss'

const SpeechAnalysis = () => {
  const { id } = useParams()
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [sourceText, setSourceText] = useState('')
  const [processing, setProcessing] = useState(false)
  const [editedText, setEditedText] = useState('')
  const [selectedStyle, setSelectedStyle] = useState(null) // 'casual' | 'professional' | 'scientific' | null

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)

      const analysisResponse = await fetch(`/api/v1/pitches/${id}/text`)
      if (!analysisResponse.ok) {
        throw new Error('Analysis not available')
      }
      const analysisData = await analysisResponse.json()
      setAnalysis(analysisData)

      // Fetch original pitch to get the source text for editing
      const pitchResponse = await fetch(`/api/v1/pitches/${id}`)
      if (pitchResponse.ok) {
        const pitchData = await pitchResponse.json()
        setSourceText(pitchData?.content || '')
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

  const getScoreColor = useCallback((score) => {
    if (score >= 0.9) return 'var(--score-excellent)'
    if (score >= 0.75) return 'var(--score-good)'
    if (score >= 0.5) return 'var(--score-average)'
    return 'var(--score-poor)'
  }, [])

  const formatScore = useCallback((score) => {
    return Math.round(score * 100)
  }, [])

  const handleToggleStyle = useCallback((styleValue) => {
    setSelectedStyle((prev) => (prev === styleValue ? null : styleValue))
  }, [])

  const renderMarkdownContent = useCallback((md) => {
    const lines = (md || '').split('\n')
    const elements = []
    let pendingList = []

    const flushList = (keyBase) => {
      if (pendingList.length > 0) {
        elements.push(
          <ul key={`${keyBase}-ul`} className='markdown-list'>
            {pendingList.map((item, idx) => (
              <li key={`${keyBase}-li-${idx}`}>{item}</li>
            ))}
          </ul>
        )
        pendingList = []
      }
    }

    lines.forEach((line, idx) => {
      const keyBase = `md-${idx}`
      const trimmed = line.trim()

      const listMatch = /^[-*]\s+(.+)/.exec(trimmed)
      if (listMatch) {
        pendingList.push(listMatch[1])
        return
      }

      flushList(keyBase)

      if (/^###\s+/.test(trimmed)) {
        elements.push(<h3 key={`${keyBase}-h3`}>{trimmed.replace(/^###\s+/, '')}</h3>)
      } else if (/^##\s+/.test(trimmed)) {
        elements.push(<h2 key={`${keyBase}-h2`}>{trimmed.replace(/^##\s+/, '')}</h2>)
      } else if (/^#\s+/.test(trimmed)) {
        elements.push(<h1 key={`${keyBase}-h1`}>{trimmed.replace(/^#\s+/, '')}</h1>)
      } else if (trimmed === '') {
        elements.push(<br key={`${keyBase}-br`} />)
      } else {
        elements.push(<p key={`${keyBase}-p`}>{line}</p>)
      }
    })

    flushList('end')
    return elements
  }, [])

  const handleEditText = useCallback(async () => {
    if (!sourceText || processing) return
    try {
      setProcessing(true)
      setEditedText('')

      const analysis_types = [
        'remove_parasites',
        'remove_bureaucracy',
        'remove_passive',
        'structure_blocks',
      ]
      if (selectedStyle) {
        analysis_types.push('style_transform')
      }

      const resp = await fetch('/api/v1/score/text', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: sourceText,
          analysis_types,
          style: selectedStyle,
          language: 'ru',
        }),
      })

      if (!resp.ok) {
        throw new Error('Failed to edit text')
      }
      const data = await resp.json()
      setEditedText(data?.final_edited_text || '')
    } catch (e) {
      setError(e.message)
    } finally {
      setProcessing(false)
    }
  }, [sourceText, selectedStyle, processing])

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

  return (
    <main className='main'>
      <div className='container speech-analysis'>
        <div className='content-header'>
          <h2 className='analysis-title'>Анализ текста</h2>
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

          {/* Text editing controls */}
          <div className='block'>
            <h2 className='section-title'>🛠 Редактирование текста</h2>
            <div className='section-content'>
              <div className='style-checkboxes' style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                <label className='checkbox-item' style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input
                    type='checkbox'
                    checked={selectedStyle === 'casual'}
                    onChange={() => handleToggleStyle('casual')}
                  />
                  <span>Неформальный</span>
                </label>
                <label className='checkbox-item' style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input
                    type='checkbox'
                    checked={selectedStyle === 'professional'}
                    onChange={() => handleToggleStyle('professional')}
                  />
                  <span>Профессиональный</span>
                </label>
                <label className='checkbox-item' style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input
                    type='checkbox'
                    checked={selectedStyle === 'scientific'}
                    onChange={() => handleToggleStyle('scientific')}
                  />
                  <span>Научный</span>
                </label>
              </div>

              <div className='edit-controls'>
                {processing && (
                  <div className='loading edit-spinner'>
                    <div className='spinner'></div>
                    <span>Редактируем текст…</span>
                  </div>
                )}
                <Button variant='primary' onClick={handleEditText} disabled={processing || !sourceText}>
                  Отредактировать текст
                </Button>
              </div>
            </div>
          </div>

          {/* Edited text result */}
          {editedText && (
            <div className='block'>
              <h2 className='section-title'>📝 Итоговый текст</h2>
              <div className='section-content'>
                <div className='pitch-content pitch-content--expanded'>
                  <div className='pitch-content-text'>
                    {renderMarkdownContent(editedText)}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}

export default SpeechAnalysis
