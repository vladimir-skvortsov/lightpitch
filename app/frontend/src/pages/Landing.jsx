import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import Button from '../components/Button'
import './Landing.scss'

const Landing = () => {
  const { isAuthenticated } = useAuth()

  const features = [
    {
      icon: '🎯',
      title: 'Анализ выступлений',
      description: 'ИИ анализирует вашу речь, жесты и подачу материала в режиме реального времени',
    },
    {
      icon: '📊',
      title: 'Детальная аналитика',
      description: 'Получайте подробные отчеты с оценками и рекомендациями для улучшения',
    },
    {
      icon: '🎓',
      title: 'Персональные тренировки',
      description: 'Создавайте тренировочные сессии и отслеживайте свой прогресс',
    },
    {
      icon: '❓',
      title: 'Гипотетические вопросы',
      description: 'ИИ генерирует релевантные вопросы для подготовки к Q&A сессии',
    },
    {
      icon: '📝',
      title: 'Анализ текста',
      description: 'Улучшайте структуру и стиль вашего выступления с помощью ИИ',
    },
    {
      icon: '📄',
      title: 'Анализ презентаций',
      description: 'Оценка дизайна, структуры и содержания ваших слайдов',
    },
  ]

  const testimonials = [
    {
      name: 'Анна Петрова',
      role: 'Стартап-основатель',
      text: 'Лайтпитч помог мне подготовиться к важному питчу перед инвесторами. Результат превзошел ожидания!',
      avatar: '👩‍💼',
    },
    {
      name: 'Михаил Сидоров',
      role: 'Менеджер продукта',
      text: 'Отличный инструмент для практики презентаций. ИИ дает очень точные и полезные рекомендации.',
      avatar: '👨‍💻',
    },
    {
      name: 'Елена Козлова',
      role: 'Коммерческий директор',
      text: 'Использую для подготовки к важным встречам с клиентами. Уверенность в выступлениях значительно выросла.',
      avatar: '👩‍💼',
    },
  ]

  return (
    <main className='landing-page'>
      {/* Hero Section */}
      <section className='hero'>
        <div className='container'>
          <div className='hero-content'>
            <h1 className='hero-title'>
              Совершенствуйте свои <span className='highlight'>питчи</span> с помощью ИИ
            </h1>
            <p className='hero-description'>
              Лайтпитч — это инновационная платформа для анализа и улучшения ваших презентаций. Получайте персональные
              рекомендации, тренируйтесь и достигайте успеха в выступлениях.
            </p>
            <div className='hero-actions'>
              {isAuthenticated() ? (
                <Button variant='primary' size='large' as={Link} to='/dashboard'>
                  Перейти к питчам
                </Button>
              ) : (
                <>
                  <Button variant='primary' size='large' as={Link} to='/auth/register'>
                    Начать бесплатно
                  </Button>
                  <Button variant='default' size='large' as={Link} to='/auth/login'>
                    Войти
                  </Button>
                </>
              )}
            </div>
          </div>
          <div className='hero-visual'>
            <div className='hero-card'>
              <div className='card-header'>
                <div className='status-indicator success'></div>
                <span>Анализ завершен</span>
              </div>
              <div className='card-content'>
                <div className='score-circle'>
                  <span className='score'>87%</span>
                </div>
                <div className='metrics'>
                  <div className='metric'>
                    <span className='metric-label'>Речь</span>
                    <div className='metric-bar'>
                      <div className='metric-fill' style={{ width: '90%' }}></div>
                    </div>
                  </div>
                  <div className='metric'>
                    <span className='metric-label'>Подача</span>
                    <div className='metric-bar'>
                      <div className='metric-fill' style={{ width: '85%' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className='features'>
        <div className='container'>
          <div className='section-header'>
            <h2>Возможности платформы</h2>
            <p>Все инструменты для создания идеального питча в одном месте</p>
          </div>
          <div className='features-grid'>
            {features.map((feature, index) => (
              <div key={index} className='feature-card'>
                <div className='feature-icon'>{feature.icon}</div>
                <h3 className='feature-title'>{feature.title}</h3>
                <p className='feature-description'>{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works Section */}
      <section className='how-it-works'>
        <div className='container'>
          <div className='section-header'>
            <h2>Как это работает</h2>
            <p>Простой процесс от создания до совершенства</p>
          </div>
          <div className='steps'>
            <div className='step'>
              <div className='step-number'>1</div>
              <div className='step-content'>
                <h3>Создайте питч</h3>
                <p>Загрузите текст выступления и презентацию</p>
              </div>
            </div>
            <div className='step'>
              <div className='step-number'>2</div>
              <div className='step-content'>
                <h3>Запишите видео</h3>
                <p>Проведите тренировочное выступление</p>
              </div>
            </div>
            <div className='step'>
              <div className='step-number'>3</div>
              <div className='step-content'>
                <h3>Получите анализ</h3>
                <p>ИИ оценит все аспекты вашего выступления</p>
              </div>
            </div>
            <div className='step'>
              <div className='step-number'>4</div>
              <div className='step-content'>
                <h3>Совершенствуйтесь</h3>
                <p>Применяйте рекомендации и улучшайте результаты</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className='testimonials'>
        <div className='container'>
          <div className='section-header'>
            <h2>Отзывы пользователей</h2>
            <p>Что говорят о нас профессионалы</p>
          </div>
          <div className='testimonials-grid'>
            {testimonials.map((testimonial, index) => (
              <div key={index} className='testimonial-card'>
                <div className='testimonial-content'>
                  <p>"{testimonial.text}"</p>
                </div>
                <div className='testimonial-author'>
                  <div className='author-avatar'>{testimonial.avatar}</div>
                  <div className='author-info'>
                    <h4>{testimonial.name}</h4>
                    <span>{testimonial.role}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className='cta'>
        <div className='container'>
          <div className='cta-content'>
            <h2>Готовы улучшить свои выступления?</h2>
            <p>Присоединяйтесь к тысячам пользователей, которые уже достигли успеха с Лайтпитч</p>
            {!isAuthenticated() && (
              <div className='cta-actions'>
                <Button variant='primary' size='large' as={Link} to='/auth/register'>
                  Начать бесплатно
                </Button>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  )
}

export default Landing
