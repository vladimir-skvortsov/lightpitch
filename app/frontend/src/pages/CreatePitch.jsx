import { useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Button from '../components/Button'
import './Form.scss'
import './CreatePitch.scss'

const CreatePitch = () => {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    content: '',
    tags: [],
  })
  const [tagInput, setTagInput] = useState('')
  const [presentationFile, setPresentationFile] = useState(null)
  const [extractingText, setExtractingText] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

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
    [formData.tags, setFormData, tagInput]
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

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault()

      if (!formData.title.trim() || !formData.content.trim()) {
        setError('Название и содержание выступления обязательны')
        return
      }

      try {
        setLoading(true)
        setError(null)

        let description = formData.description.trim()

        const response = await fetch('/api/v1/pitches/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            title: formData.title.trim(),
            description: description || null,
            content: formData.content.trim(),
            tags: formData.tags.length > 0 ? formData.tags : null,
          }),
        })

        if (!response.ok) {
          throw new Error('Ошибка при создании выступления')
        }

        const newPitch = await response.json()

        if (presentationFile) {
          try {
            const formData = new FormData()
            formData.append('file', presentationFile)

            const uploadResponse = await fetch(`/api/v1/pitches/${newPitch.id}/presentation`, {
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

        navigate(`/pitch/${newPitch.id}`)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    },
    [formData.title, formData.content, formData.description, formData.tags, presentationFile, navigate]
  )

  return (
    <main className='main'>
      <div className='container'>
        <div className='content-header'>
          <h2>Создать выступление</h2>
          <Button variant='outline' as={Link} to='/'>
            ← Назад к списку
          </Button>
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
              disabled={loading}
            />
          </div>

          <div className='form-group'>
            <label htmlFor='description'>Описание</label>
            <textarea
              id='description'
              name='description'
              value={formData.description}
              onChange={handleChange}
              placeholder='Краткое описание выступления (оставьте пустым для автоматической генерации)'
              rows={3}
              disabled={loading}
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
                  disabled={loading || extractingText}
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
                  disabled={loading || extractingText}
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
                name='tag'
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                placeholder='Добавить тег'
                disabled={loading}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleAddTag(e)
                  }
                }}
              />
              <Button type='button' onClick={handleAddTag} variant='outline' disabled={loading || !tagInput.trim()}>
                Добавить
              </Button>
            </div>
            {formData.tags.length > 0 && (
              <div className='pitch-tags'>
                {formData.tags.map((tag, index) => (
                  <span key={index} className='tag tag-removable'>
                    {tag}
                    <button
                      type='button'
                      onClick={() => handleRemoveTag(tag)}
                      className='tag-remove'
                      disabled={loading}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className='form-group'>
            <label htmlFor='presentation'>Презентация (необязательно)</label>
            <input
              type='file'
              id='presentation'
              name='presentation'
              accept='.pdf,.ppt,.pptx,application/pdf,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation'
              onChange={handlePresentationUpload}
              disabled={loading}
              className='file-input'
            />
            {presentationFile && (
              <div className='file-info'>
                <span>📄 {presentationFile.name}</span>
                <button
                  type='button'
                  onClick={() => setPresentationFile(null)}
                  className='file-remove'
                  disabled={loading}
                >
                  ×
                </button>
              </div>
            )}
            <p className='form-help'>Поддерживаются файлы PDF, PPT, PPTX (максимум 50MB)</p>
          </div>

          <div className='form-actions'>
            <Button variant='secondary' as={Link} to='/'>
              Отмена
            </Button>
            <Button
              type='submit'
              variant='primary'
              disabled={loading || !formData.title.trim() || !formData.content.trim()}
            >
              {loading ? 'Создание...' : 'Создать выступление'}
            </Button>
          </div>
        </form>
      </div>
    </main>
  )
}

export default CreatePitch
