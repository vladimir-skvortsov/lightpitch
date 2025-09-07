import { useState, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import Button from '../components/Button'
import './UploadVideo.scss'

const UploadVideo = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)

  const handleFileSelect = useCallback((event) => {
    const file = event.target.files[0]
    if (file) {
      // Проверяем тип файла
      if (!file.type.startsWith('video/')) {
        setError('Пожалуйста, выберите видео файл')
        return
      }

      // Проверяем размер файла (максимум 100MB)
      const maxSize = 100 * 1024 * 1024
      if (file.size > maxSize) {
        setError('Размер файла не должен превышать 100MB')
        return
      }

      setSelectedFile(file)
      setError(null)
    }
  }, [])

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return

    try {
      setUploading(true)
      setError(null)

      const formData = new FormData()
      formData.append('video', selectedFile)
      formData.append('pitch_id', id)

      const response = await fetch('/api/v1/score/pitch', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Ошибка при загрузке видео')
      }

      const result = await response.json()

      // Переходим на страницу результатов
      navigate(`/pitch/${id}/results`, {
        state: { analysisResult: result },
      })
    } catch (err) {
      setError('Ошибка при обработке видео: ' + err.message)
    } finally {
      setUploading(false)
    }
  }, [id, navigate, selectedFile])

  const formatFileSize = useCallback((bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }, [])

  return (
    <main className='main'>
      <div className='container'>
        <div className='upload-video-container'>
          <div className='upload-header'>
            <h2>Загрузка видео</h2>
            <Button variant='outline' as={Link} to={`/pitch/${id}`}>
              ← Назад к выступлению
            </Button>
          </div>

          {error && (
            <div className='error'>
              <p>⚠️ {error}</p>
            </div>
          )}

          <div className='upload-section'>
            <div className='upload-area'>
              <input
                type='file'
                id='video-upload'
                accept='video/*'
                onChange={handleFileSelect}
                className='file-input'
                disabled={uploading}
              />
              <label htmlFor='video-upload' className='upload-label'>
                {selectedFile ? (
                  <div className='file-selected'>
                    <div className='file-icon'>🎥</div>
                    <div className='file-info'>
                      <div className='file-name'>{selectedFile.name}</div>
                      <div className='file-size'>{formatFileSize(selectedFile.size)}</div>
                    </div>
                  </div>
                ) : (
                  <div className='upload-placeholder'>
                    <div className='upload-icon'>📁</div>
                    <div className='upload-text'>
                      <h3>Выберите видео файл</h3>
                      <p>Поддерживаются форматы: MP4, WebM, MOV</p>
                      <p>Максимальный размер: 100MB</p>
                    </div>
                  </div>
                )}
              </label>
            </div>

            {selectedFile && (
              <div className='upload-actions'>
                <Button
                  variant='outline'
                  onClick={() => {
                    setSelectedFile(null)
                    setError(null)
                  }}
                  disabled={uploading}
                >
                  🗑️ Убрать файл
                </Button>
                <Button variant='primary' onClick={handleUpload} disabled={uploading}>
                  {uploading ? '⏳ Анализируем...' : '📊 Получить результаты'}
                </Button>
              </div>
            )}
          </div>

          <div className='upload-tips'>
            <h3>💡 Советы для лучшего анализа:</h3>
            <ul>
              <li>Убедитесь, что ваше лицо хорошо видно в кадре</li>
              <li>Обеспечьте хорошее освещение</li>
              <li>Говорите четко и достаточно громко</li>
              <li>Избегайте фонового шума</li>
            </ul>
          </div>
        </div>
      </div>
    </main>
  )
}

export default UploadVideo
