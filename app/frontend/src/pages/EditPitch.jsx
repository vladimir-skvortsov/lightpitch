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
    planned_duration_minutes: '',
    tags: [],
  })
  const [tagInput, setTagInput] = useState('')
  const [presentationFile, setPresentationFile] = useState(null)
  const [currentPresentationName, setCurrentPresentationName] = useState('')
  const [extractingText, setExtractingText] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const fetchPitch = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/v1/pitches/${id}`)

      if (!response.ok) {
        throw new Error('Выступление не найдено')
      }

      const pitch = await response.json()
      setFormData({
        title: pitch.title || '',
        description: pitch.description || '',
        content: pitch.content || '',
        planned_duration_minutes: pitch.planned_duration_minutes || '',
        tags: pitch.tags || [],
      })
      setCurrentPresentationName(pitch.presentation_file_name || '')
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

  const handleTextFileUpload = useCallback(
    async (e) => {
      const file = e.target.files[0]
      if (file) {
        // Check file type
        const allowedTypes = [
          'text/plain',
          'application/msword',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        ]
        const allowedExtensions = ['.txt', '.doc', '.docx']
        const fileExtension = file.name.toLowerCase().split('.').pop()

        if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(`.${fileExtension}`)) {
          setError('Поддерживаются только файлы TXT, DOC и DOCX')
          e.target.value = ''
          return
        }

        // Check file size (10MB limit)
        const maxSize = 10 * 1024 * 1024
        if (file.size > maxSize) {
          setError('Размер файла не должен превышать 10MB')
          e.target.value = ''
          return
        }

        try {
          setExtractingText(true)
          setError(null)

          const formData = new FormData()
          formData.append('file', file)

          const response = await fetch('/api/v1/extract-text', {
            method: 'POST',
            body: formData,
          })

          if (!response.ok) {
            const errorData = await response.json()
            throw new Error(errorData.detail || 'Ошибка при обработке файла')
          }

          const data = await response.json()

          // Заполняем textarea с текстом выступления
          setFormData((prev) => ({
            ...prev,
            content: data.text,
          }))

          // Показываем информацию о файле
          console.log(`Извлечено ${data.word_count} слов из файла ${data.filename}`)
        } catch (err) {
          setError(err.message)
          e.target.value = ''
        } finally {
          setExtractingText(false)
        }
      }
    },
    [setFormData]
  )

  const handlePresentationUpload = useCallback((e) => {
    const file = e.target.files[0]
    if (file) {
      // Check file type
      const allowedTypes = [
        'application/pdf',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      ]
      if (!allowedTypes.includes(file.type)) {
        setError('Поддерживаются только файлы PDF, PPT и PPTX')
        e.target.value = ''
        return
      }

      // Check file size (50MB limit)
      const maxSize = 50 * 1024 * 1024
      if (file.size > maxSize) {
        setError('Размер файла не должен превышать 50MB')
        e.target.value = ''
        return
      }

      setPresentationFile(file)
      setError(null)
    }
  }, [])

  const handleRemovePresentation = useCallback(async () => {
    if (currentPresentationName) {
      try {
        const response = await fetch(`/api/v1/pitches/${id}/presentation`, {
          method: 'DELETE',
        })

        if (response.ok) {
          setCurrentPresentationName('')
        } else {
          console.warn('Failed to delete presentation file')
        }
      } catch (err) {
        console.warn('Error deleting presentation:', err)
      }
    }
    setPresentationFile(null)
  }, [id, currentPresentationName])

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault()

      if (!formData.title.trim() || !formData.content.trim() || !formData.planned_duration_minutes) {
        setError('Название, содержание выступления и планируемая длительность обязательны')
        return
      }

      const durationMinutes = parseInt(formData.planned_duration_minutes, 10)
      if (isNaN(durationMinutes) || durationMinutes <= 0 || durationMinutes > 480) {
        setError('Длительность должна быть от 1 до 480 минут')
        return
      }

      try {
        setSaving(true)
        setError(null)

        const response = await fetch(`/api/v1/pitches/${id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            title: formData.title.trim(),
            description: formData.description.trim() || null,
            content: formData.content.trim(),
            planned_duration_minutes: durationMinutes,
            tags: formData.tags.length > 0 ? formData.tags : null,
          }),
        })

        if (!response.ok) {
          throw new Error('Ошибка при обновлении выступления')
        }

        // Upload presentation file if provided
        if (presentationFile) {
          try {
            const formData = new FormData()
            formData.append('file', presentationFile)

            const uploadResponse = await fetch(`/api/v1/pitches/${id}/presentation`, {
              method: 'POST',
              body: formData,
            })

            if (!uploadResponse.ok) {
              console.warn('Failed to upload presentation file')
            }
          } catch (uploadErr) {
            console.warn('Error uploading presentation:', uploadErr)
          }
        }

        navigate(`/pitch/${id}`)
      } catch (err) {
        setError(err.message)
      } finally {
        setSaving(false)
      }
    },
    [formData.title, formData.content, formData.description, formData.planned_duration_minutes, formData.tags, presentationFile, id, navigate]
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
            <label htmlFor='planned_duration_minutes'>Планируемая длительность (минуты) *</label>
            <input
              type='number'
              id='planned_duration_minutes'
              name='planned_duration_minutes'
              value={formData.planned_duration_minutes}
              onChange={handleChange}
              placeholder='Введите длительность в минутах'
              min='1'
              max='480'
              required
              disabled={saving}
            />
            <p className='form-help'>Укажите планируемую длительность выступления от 1 до 480 минут</p>
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

            <div className='text-input-options'>
              <div className='text-input-manual'>
                <textarea
                  id='content'
                  name='content'
                  value={formData.content}
                  onChange={handleChange}
                  placeholder='Введите полный текст вашего выступления или загрузите файл...'
                  rows={12}
                  required
                  disabled={saving || extractingText}
                />
              </div>

              <div className='text-input-file'>
                <label htmlFor='textFile' className='text-file-label'>
                  <span className='text-file-icon'>📄</span>
                  <span className='text-file-text'>
                    {extractingText ? 'Обрабатываем файл...' : 'Загрузить из файла'}
                  </span>
                </label>
                <input
                  type='file'
                  id='textFile'
                  name='textFile'
                  accept='.txt,.doc,.docx,text/plain,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                  onChange={handleTextFileUpload}
                  disabled={saving || extractingText}
                  className='file-input-hidden'
                />
                <p className='form-help'>TXT, DOC, DOCX (максимум 10MB)</p>
              </div>
            </div>
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

          <div className='form-group'>
            <label htmlFor='presentation'>Презентация (необязательно)</label>

            {currentPresentationName && !presentationFile && (
              <div className='current-file'>
                <div className='file-info'>
                  <span>📄 {currentPresentationName}</span>
                  <button type='button' onClick={handleRemovePresentation} className='file-remove' disabled={saving}>
                    ×
                  </button>
                </div>
                <p className='form-help'>Текущая презентация</p>
              </div>
            )}

            <input
              type='file'
              id='presentation'
              name='presentation'
              accept='.pdf,.ppt,.pptx,application/pdf,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation'
              onChange={handlePresentationUpload}
              disabled={saving}
              className='file-input'
            />

            {presentationFile && (
              <div className='file-info'>
                <span>📄 {presentationFile.name}</span>
                <button
                  type='button'
                  onClick={() => setPresentationFile(null)}
                  className='file-remove'
                  disabled={saving}
                >
                  ×
                </button>
              </div>
            )}

            <p className='form-help'>
              {presentationFile
                ? 'Новый файл заменит текущую презентацию'
                : 'Поддерживаются файлы PDF, PPT, PPTX (максимум 50MB)'}
            </p>
          </div>

          <div className='form-actions'>
            <Button variant='secondary' as={Link} to={`/pitch/${id}`}>
              Отмена
            </Button>
            <Button
              type='submit'
              variant='primary'
              disabled={saving || !formData.title.trim() || !formData.content.trim() || !formData.planned_duration_minutes}
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
