import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import Button from '../components/Button'
import './RecordVideo.scss'

const RecordVideo = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const videoRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)
  const [isRecording, setIsRecording] = useState(false)
  const [isPreparingCamera, setIsPreparingCamera] = useState(true)
  const [error, setError] = useState(null)
  const [recordedBlob, setRecordedBlob] = useState(null)
  const [recordingTime, setRecordingTime] = useState(0)
  const recordingIntervalRef = useRef(null)

  const startCamera = useCallback(async () => {
    try {
      setIsPreparingCamera(true)
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true,
      })

      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        // Wait for video to be ready
        await new Promise((resolve) => {
          videoRef.current.onloadedmetadata = resolve
        })
      }

      setIsPreparingCamera(false)
    } catch (error) {
      console.error(error)
      setError('Не удалось получить доступ к камере и микрофону. Проверьте разрешения.')
      setIsPreparingCamera(false)
    }
  }, [])

  const stopCamera = useCallback(() => {
    // Use streamRef as primary source, fallback to videoRef.current.srcObject
    const stream = streamRef.current || (videoRef.current && videoRef.current.srcObject)
    if (stream) {
      const tracks = stream.getTracks()
      tracks.forEach((track) => track.stop())
      streamRef.current = null
    }
  }, [])

  useEffect(() => {
    startCamera()
    return () => {
      stopCamera()
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current)
      }
    }
  }, [startCamera, stopCamera])

  const startRecording = useCallback(async () => {
    try {
      // Use streamRef as primary source, fallback to videoRef.current.srcObject
      const stream = streamRef.current || (videoRef.current && videoRef.current.srcObject)

      if (!stream) {
        setError('Поток видео недоступен. Попробуйте перезагрузить страницу.')
        return
      }

      mediaRecorderRef.current = new MediaRecorder(stream)

      const chunks = []
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data)
        }
      }

      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(chunks, { type: 'video/webm' })
        setRecordedBlob(blob)
      }

      mediaRecorderRef.current.start()
      setIsRecording(true)
      setRecordingTime(0)

      // Запуск таймера
      recordingIntervalRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1)
      }, 1000)
    } catch (error) {
      console.error(error)
      setError('Ошибка при начале записи')
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)

      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current)
      }
    }
  }, [isRecording])

  const handleFinish = useCallback(async () => {
    if (!recordedBlob) {
      setError('Сначала запишите видео')
      return
    }

    try {
      // Создаем FormData для отправки видео
      const formData = new FormData()
      formData.append('video', recordedBlob, 'pitch-recording.webm')
      formData.append('pitch_id', id)

      const response = await fetch('/api/v1/score/pitch', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Ошибка при отправке видео')
      }

      const result = await response.json()

      // Переходим на страницу результатов
      navigate(`/pitch/${id}/results`, {
        state: { analysisResult: result },
      })
    } catch (error) {
      console.error(error)
      setError('Ошибка при обработке видео: ' + error.message)
    }
  }, [id, navigate, recordedBlob])

  const formatTime = useCallback((seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }, [])

  if (isPreparingCamera) {
    return (
      <main className='main'>
        <div className='container'>
          <div className='record-video-container'>
            <div className='camera-loading'>
              <div className='spinner'></div>
              <p>Подключение к камере...</p>
            </div>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className='main'>
      <div className='container'>
        <div className='record-video-container'>
          <div className='record-header'>
            <h2>Запись выступления</h2>
            <Button variant='outline' as={Link} to={`/pitch/${id}`}>
              ← Назад к выступлению
            </Button>
          </div>

          {error && (
            <div className='error'>
              <p>⚠️ {error}</p>
              <Button variant='secondary' onClick={() => setError(null)}>
                Закрыть
              </Button>
            </div>
          )}

          <div className='video-container'>
            <video ref={videoRef} autoPlay muted playsInline className='camera-preview' />

            {isRecording && (
              <div className='recording-indicator'>
                <div className='recording-dot'></div>
                <span>REC {formatTime(recordingTime)}</span>
              </div>
            )}
          </div>

          <div className='recording-controls'>
            {!isRecording && !recordedBlob && (
              <Button variant='primary' size='large' onClick={startRecording}>
                Начать запись
              </Button>
            )}

            {isRecording && (
              <Button variant='danger' size='large' onClick={stopRecording}>
                Остановить запись
              </Button>
            )}

            {recordedBlob && !isRecording && (
              <div className='recording-finished'>
                <p>✅ Запись завершена!</p>
                <div className='final-actions'>
                  <Button
                    variant='outline'
                    onClick={() => {
                      setRecordedBlob(null)
                      setRecordingTime(0)
                    }}
                  >
                    🔄 Записать заново
                  </Button>
                  <Button variant='primary' onClick={handleFinish}>
                    📊 Получить результаты
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  )
}

export default RecordVideo
