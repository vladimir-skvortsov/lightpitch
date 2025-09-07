import { useParams, Link, useLocation } from 'react-router-dom'
import Button from '../components/Button'
import './PitchResults.scss'

const PitchResults = () => {
  const { id } = useParams()
  const location = useLocation()

  // Получаем результаты из state или используем hardcoded данные
  const analysisResult = location.state?.analysisResult || {
    overall_score: 8.2,
    confidence: 7.8,
    clarity: 8.5,
    pace: 7.2,
    engagement: 8.8,
    body_language: 7.9,
    eye_contact: 8.1,
    voice_tone: 8.3,
    duration: '2:34',
    word_count: 287,
    feedback: [
      {
        type: 'positive',
        message: 'Отличная четкость речи и хорошая интонация',
      },
      {
        type: 'improvement',
        message: 'Рекомендуется немного замедлить темп речи для лучшего восприятия',
      },
      {
        type: 'positive',
        message: 'Хороший зрительный контакт с аудиторией',
      },
      {
        type: 'improvement',
        message: 'Добавьте больше жестов для усиления эмоциональной составляющей',
      },
    ],
    strengths: [
      'Четкая артикуляция',
      'Хорошая структура выступления',
      'Уверенная подача материала',
      'Профессиональная манера речи',
    ],
    areas_for_improvement: [
      'Темп речи',
      'Язык тела и жестикуляция',
      'Паузы для акцентирования',
      'Эмоциональная вовлеченность',
    ],
  }

  const getScoreColor = (score) => {
    if (score >= 8) return 'score-excellent'
    if (score >= 6) return 'score-good'
    if (score >= 4) return 'score-fair'
    return 'score-poor'
  }

  const getScoreLabel = (score) => {
    if (score >= 8) return 'Отлично'
    if (score >= 6) return 'Хорошо'
    if (score >= 4) return 'Удовлетворительно'
    return 'Требует улучшения'
  }

  return (
    <main className='main'>
      <div className='container pitch-results'>
        <div className='results-container'>
          <div className='results-header'>
            <Button variant='outline' as={Link} to={`/pitch/${id}`}>
              ← Назад к выступлению
            </Button>
            <h2>Результаты анализа</h2>
          </div>

          {/* Общий балл */}
          <div className='overall-score-section'>
            <div className='score-circle'>
              <div className={`score-value ${getScoreColor(analysisResult.overall_score)}`}>
                {analysisResult.overall_score}
              </div>
              <div className='score-label'>Общий балл</div>
            </div>
            <div className='score-summary'>
              <h3>{getScoreLabel(analysisResult.overall_score)}</h3>
              <p>Продолжительность: {analysisResult.duration}</p>
              <p>Количество слов: {analysisResult.word_count}</p>
            </div>
          </div>

          {/* Детальные метрики */}
          <div className='metrics-section'>
            <h3>Детальный анализ</h3>
            <div className='metrics-grid'>
              <div className='metric-item'>
                <span className='metric-name'>Уверенность</span>
                <div className='metric-bar'>
                  <div className='metric-fill' style={{ width: `${(analysisResult.confidence / 10) * 100}%` }}></div>
                </div>
                <span className='metric-value'>{analysisResult.confidence}</span>
              </div>

              <div className='metric-item'>
                <span className='metric-name'>Четкость речи</span>
                <div className='metric-bar'>
                  <div className='metric-fill' style={{ width: `${(analysisResult.clarity / 10) * 100}%` }}></div>
                </div>
                <span className='metric-value'>{analysisResult.clarity}</span>
              </div>

              <div className='metric-item'>
                <span className='metric-name'>Темп речи</span>
                <div className='metric-bar'>
                  <div className='metric-fill' style={{ width: `${(analysisResult.pace / 10) * 100}%` }}></div>
                </div>
                <span className='metric-value'>{analysisResult.pace}</span>
              </div>

              <div className='metric-item'>
                <span className='metric-name'>Вовлеченность</span>
                <div className='metric-bar'>
                  <div className='metric-fill' style={{ width: `${(analysisResult.engagement / 10) * 100}%` }}></div>
                </div>
                <span className='metric-value'>{analysisResult.engagement}</span>
              </div>

              <div className='metric-item'>
                <span className='metric-name'>Язык тела</span>
                <div className='metric-bar'>
                  <div className='metric-fill' style={{ width: `${(analysisResult.body_language / 10) * 100}%` }}></div>
                </div>
                <span className='metric-value'>{analysisResult.body_language}</span>
              </div>

              <div className='metric-item'>
                <span className='metric-name'>Зрительный контакт</span>
                <div className='metric-bar'>
                  <div className='metric-fill' style={{ width: `${(analysisResult.eye_contact / 10) * 100}%` }}></div>
                </div>
                <span className='metric-value'>{analysisResult.eye_contact}</span>
              </div>
            </div>
          </div>

          {/* Обратная связь */}
          <div className='feedback-section'>
            <h3>Обратная связь</h3>
            <div className='feedback-list'>
              {analysisResult.feedback.map((item, index) => (
                <div key={index} className={`feedback-item feedback-${item.type}`}>
                  <div className='feedback-icon'>{item.type === 'positive' ? '✅' : '💡'}</div>
                  <p>{item.message}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Сильные стороны и области для улучшения */}
          <div className='strengths-improvements'>
            <div className='strengths-section'>
              <h3>🎯 Сильные стороны</h3>
              <ul>
                {analysisResult.strengths.map((strength, index) => (
                  <li key={index}>{strength}</li>
                ))}
              </ul>
            </div>

            <div className='improvements-section'>
              <h3>📈 Области для улучшения</h3>
              <ul>
                {analysisResult.areas_for_improvement.map((area, index) => (
                  <li key={index}>{area}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* Действия */}
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
    </main>
  )
}

export default PitchResults
