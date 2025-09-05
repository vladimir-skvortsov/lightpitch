import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Button from '../components/Button'
import './Form.scss'

const EditPitch = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    content: '',
    tags: [],
  })
  const [tagInput, setTagInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const fetchPitch = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch(`http://localhost:8000/api/v1/pitches/${id}`)

      if (!response.ok) {
        throw new Error('Выступление не найдено')
      }

      const pitch = await response.json()
      setFormData({
        title: pitch.title || '',
        description: pitch.description || '',
        content: pitch.content || '',
        tags: pitch.tags || [],
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchPitch()
  }, [fetchPitch, id])

  const handleChange = useCallback(
    (e) => {
      const { name, value } = e.target
      setFormData((prev) => ({
        ...prev,
        [name]: value,
      }))
    },
    [setFormData]
  )

  const handleAddTag = useCallback(
    (e) => {
      e.preventDefault()
      if (tagInput.trim() && !formData.tags.includes(tagInput.trim())) {
        setFormData((prev) => ({
          ...prev,
          tags: [...prev.tags, tagInput.trim()],
        }))
        setTagInput('')
      }
    },
    [formData.tags, tagInput]
  )

  const handleRemoveTag = useCallback(
    (tagToRemove) => {
      setFormData((prev) => ({
        ...prev,
        tags: prev.tags.filter((tag) => tag !== tagToRemove),
      }))
    },
    [setFormData]
  )

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault()

      if (!formData.title.trim() || !formData.content.trim()) {
        setError('Название и содержание выступления обязательны')
        return
      }

      try {
        setSaving(true)
        setError(null)

        const response = await fetch(`http://localhost:8000/api/v1/pitches/${id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            title: formData.title.trim(),
            description: formData.description.trim() || null,
            content: formData.content.trim(),
            tags: formData.tags.length > 0 ? formData.tags : null,
          }),
        })

        if (!response.ok) {
          throw new Error('Ошибка при обновлении выступления')
        }

        navigate(`/pitch/${id}`)
      } catch (err) {
        setError(err.message)
      } finally {
        setSaving(false)
      }
    },
    [formData.title, formData.content, formData.description, formData.tags, id, navigate]
  )

  if (loading) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='loading'>
            <div className='spinner'></div>
            <p>Загрузка выступления...</p>
          </div>
        </div>
      </main>
    )
  }

  if (error && !formData.title) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='error'>
            <p>⚠️ {error}</p>
            <Button variant='primary' as={Link} to='/'>
              Вернуться на главную
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
          <h2>Редактировать выступление</h2>
          <div className='pitch-actions'>
            <Button variant='outline' as={Link} to={`/pitch/${id}`}>
              ← Назад
            </Button>
          </div>
        </div>

        {error && (
          <div className='error'>
            <p>⚠️ {error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className='pitch-form'>
          <div className='form-group'>
            <label htmlFor='title'>Название выступления *</label>
            <input
              type='text'
              id='title'
              name='title'
              value={formData.title}
              onChange={handleChange}
              placeholder='Введите название выступления'
              required
              disabled={saving}
            />
          </div>

          <div className='form-group'>
            <label htmlFor='description'>Описание</label>
            <textarea
              id='description'
              name='description'
              value={formData.description}
              onChange={handleChange}
              placeholder='Краткое описание выступления (необязательно)'
              rows={3}
              disabled={saving}
            />
          </div>

          <div className='form-group'>
            <label htmlFor='content'>Текст выступления *</label>
            <textarea
              id='content'
              name='content'
              value={formData.content}
              onChange={handleChange}
              placeholder='Введите полный текст вашего выступления...'
              rows={12}
              required
              disabled={saving}
            />
          </div>

          <div className='form-group'>
            <label>Теги</label>
            <div className='tag-input-group'>
              <input
                type='text'
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                placeholder='Добавить тег'
                disabled={saving}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleAddTag(e)
                  }
                }}
              />
              <Button type='button' onClick={handleAddTag} variant='outline' disabled={saving || !tagInput.trim()}>
                Добавить
              </Button>
            </div>
            {formData.tags.length > 0 && (
              <div className='pitch-tags'>
                {formData.tags.map((tag, index) => (
                  <span key={index} className='tag tag-removable'>
                    {tag}
                    <button type='button' onClick={() => handleRemoveTag(tag)} className='tag-remove' disabled={saving}>
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className='form-actions'>
            <Button variant='secondary' as={Link} to={`/pitch/${id}`}>
              Отмена
            </Button>
            <Button
              type='submit'
              variant='primary'
              disabled={saving || !formData.title.trim() || !formData.content.trim()}
            >
              {saving ? 'Сохранение...' : 'Сохранить изменения'}
            </Button>
          </div>
        </form>
      </div>
    </main>
  )
}

export default EditPitch
