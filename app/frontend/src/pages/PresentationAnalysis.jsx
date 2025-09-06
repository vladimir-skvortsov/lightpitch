import { useState, useEffect, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import './PresentationAnalysis.scss'

const PresentationAnalysis = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [pitch, setPitch] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchPitchAndAnalysis = useCallback(async () => {
    try {
      setLoading(true)

      // Fetch pitch data
      const pitchResponse = await fetch(`/api/v1/pitches/${id}`)
      if (!pitchResponse.ok) {
        throw new Error('Выступление не найдено')
      }
      const pitchData = await pitchResponse.json()
      setPitch(pitchData)

      // Fetch presentation analysis (hardcoded for now)
      const analysisResponse = await fetch(`/api/v1/pitches/${id}/presentation-analysis`)
      if (analysisResponse.ok) {
        const analysisData = await analysisResponse.json()
        setAnalysis(analysisData)
      } else {
        // Use hardcoded data if API doesn't exist yet
        setAnalysis({
          overall_score: 85,
          good_practices: [
            {
              title: 'Консистентный дизайн',
              description: 'Единообразное использование цветов, шрифтов и стилей на всех слайдах',
              category: 'Дизайн',
            },
            {
              title: 'Четкая структура',
              description: 'Логичная последовательность слайдов с ясной навигацией',
              category: 'Структура',
            },
            {
              title: 'Качественные изображения',
              description: 'Высокое разрешение и релевантность визуального контента',
              category: 'Контент',
            },
            {
              title: 'Читаемые шрифты',
              description: 'Подходящий размер и контрастность текста',
              category: 'Типографика',
            },
            {
              title: 'Логотип компании',
              description: 'Правильное размещение и использование брендинга',
              category: 'Брендинг',
            },
            {
              title: 'Контактная информация',
              description: 'Четко указаны контакты на финальном слайде',
              category: 'Контент',
            },
            {
              title: 'Соотношение 16:9',
              description: 'Правильный формат слайдов для современных экранов',
              category: 'Формат',
            },
            {
              title: 'Минимализм в дизайне',
              description: 'Отсутствие визуального беспорядка и лишних элементов',
              category: 'Дизайн',
            },
            {
              title: 'Заголовки слайдов',
              description: 'Каждый слайд имеет четкий и информативный заголовок',
              category: 'Структура',
            },
            {
              title: 'Корпоративные цвета',
              description: 'Использование цветовой палитры бренда',
              category: 'Брендинг',
            },
            {
              title: 'Нумерация слайдов',
              description: 'Присутствует нумерация для удобной навигации',
              category: 'Навигация',
            },
            {
              title: 'Качественная анимация',
              description: 'Плавные и уместные переходы между слайдами',
              category: 'Анимация',
            },
          ],
          warnings: [
            {
              title: 'Слишком много текста',
              description: 'На слайдах 3, 7 и 12 превышен рекомендуемый объем текста (более 50 слов)',
              category: 'Контент',
              slides: [3, 7, 12],
            },
            {
              title: 'Мелкий шрифт',
              description: 'Размер шрифта на слайдах 5 и 9 может быть плохо читаемым с дальнего расстояния',
              category: 'Типографика',
              slides: [5, 9],
            },
            {
              title: 'Перегруженные диаграммы',
              description: 'Слайд 8 содержит слишком много данных в одной диаграмме',
              category: 'Визуализация',
              slides: [8],
            },
          ],
          errors: [
            {
              title: 'Низкое качество изображения',
              description: 'Изображение на слайде 6 имеет разрешение ниже рекомендуемого (менее 150 DPI)',
              category: 'Качество',
              slides: [6],
              severity: 'high',
            },
          ],
          recommendations: [
            'Сократите количество текста на перегруженных слайдах',
            'Увеличьте размер шрифта до минимум 24pt для основного текста',
            'Замените изображение низкого качества на слайде 6',
            'Разделите сложную диаграмму на несколько более простых',
          ],
        })
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchPitchAndAnalysis()
  }, [fetchPitchAndAnalysis])

  const getScoreColor = (score) => {
    if (score >= 90) return '#16a34a'
    if (score >= 70) return '#ca8a04'
    return '#dc2626'
  }

  const getScoreLabel = (score) => {
    if (score >= 90) return 'Отлично'
    if (score >= 70) return 'Хорошо'
    if (score >= 50) return 'Удовлетворительно'
    return 'Требует доработки'
  }

  if (loading) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='loading'>
            <div className='spinner'></div>
            <p>Анализ презентации...</p>
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

  if (!analysis) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='error'>
            <p>⚠️ Анализ презентации недоступен</p>
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
      <div className='container'>
        <div className='content-header'>
          <Button variant='outline' as={Link} to={`/pitch/${id}`}>
            ← Назад к выступлению
          </Button>
        </div>

        <div className='analysis-header'>
          <div className='analysis-title'>
            <h1>Анализ презентации</h1>
            {pitch && <p className='analysis-subtitle'>{pitch.title}</p>}
          </div>
          <div className='analysis-score'>
            <div className='score-circle' style={{ borderColor: getScoreColor(analysis.overall_score) }}>
              <span className='score-number' style={{ color: getScoreColor(analysis.overall_score) }}>
                {analysis.overall_score}
              </span>
              <span className='score-label'>из 100</span>
            </div>
            <div className='score-description'>
              <span className='score-status' style={{ color: getScoreColor(analysis.overall_score) }}>
                {getScoreLabel(analysis.overall_score)}
              </span>
              <span className='score-text'>Общая оценка презентации</span>
            </div>
          </div>
        </div>

        <div className='analysis-summary'>
          <div className='summary-item summary-item--success'>
            <div className='summary-icon'>✓</div>
            <div className='summary-count'>{analysis.good_practices.length}</div>
            <div className='summary-label'>Хорошие практики</div>
          </div>
          <div className='summary-item summary-item--warning'>
            <div className='summary-icon'>⚠</div>
            <div className='summary-count'>{analysis.warnings.length}</div>
            <div className='summary-label'>Предупреждения</div>
          </div>
          <div className='summary-item summary-item--error'>
            <div className='summary-icon'>✕</div>
            <div className='summary-count'>{analysis.errors.length}</div>
            <div className='summary-label'>Ошибки</div>
          </div>
        </div>

        <div className='analysis-sections'>
          {analysis.good_practices.length > 0 && (
            <div className='analysis-section analysis-section--success'>
              <h2 className='section-title'>
                <span className='section-icon'>✓</span>
                Хорошие практики
              </h2>
              <div className='section-items'>
                {analysis.good_practices.map((item, index) => (
                  <div key={index} className='analysis-item'>
                    <div className='item-header'>
                      <h3 className='item-title'>{item.title}</h3>
                      <span className='item-category'>{item.category}</span>
                    </div>
                    <p className='item-description'>{item.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis.warnings.length > 0 && (
            <div className='analysis-section analysis-section--warning'>
              <h2 className='section-title'>
                <span className='section-icon'>⚠</span>
                Предупреждения
              </h2>
              <div className='section-items'>
                {analysis.warnings.map((item, index) => (
                  <div key={index} className='analysis-item'>
                    <div className='item-header'>
                      <h3 className='item-title'>{item.title}</h3>
                      <div className='item-meta'>
                        <span className='item-category'>{item.category}</span>
                        {item.slides && <span className='item-slides'>Слайды: {item.slides.join(', ')}</span>}
                      </div>
                    </div>
                    <p className='item-description'>{item.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis.errors.length > 0 && (
            <div className='analysis-section analysis-section--error'>
              <h2 className='section-title'>
                <span className='section-icon'>✕</span>
                Ошибки
              </h2>
              <div className='section-items'>
                {analysis.errors.map((item, index) => (
                  <div key={index} className='analysis-item'>
                    <div className='item-header'>
                      <h3 className='item-title'>{item.title}</h3>
                      <div className='item-meta'>
                        <span className='item-category'>{item.category}</span>
                        {item.slides && <span className='item-slides'>Слайды: {item.slides.join(', ')}</span>}
                        {item.severity && (
                          <span className={`item-severity item-severity--${item.severity}`}>
                            {item.severity === 'high' ? 'Высокая' : 'Низкая'} важность
                          </span>
                        )}
                      </div>
                    </div>
                    <p className='item-description'>{item.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis.recommendations && analysis.recommendations.length > 0 && (
            <div className='analysis-section analysis-section--recommendations'>
              <h2 className='section-title'>
                <span className='section-icon'>💡</span>
                Рекомендации
              </h2>
              <div className='recommendations-list'>
                {analysis.recommendations.map((recommendation, index) => (
                  <div key={index} className='recommendation-item'>
                    <span className='recommendation-number'>{index + 1}</span>
                    <span className='recommendation-text'>{recommendation}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}

export default PresentationAnalysis
