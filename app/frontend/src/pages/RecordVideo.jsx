import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import Button from '../components/Button'
import './RecordVideo.scss'
import { FaceMesh } from '@mediapipe/face_mesh'

const EAR_THR = 0.12         // порог открытости века
const FRAME_MARGIN = 0.1    // безопасная зона кадра (доли 0..1)
const PATCH_SCALE = 0.035    // радиус патча (доля от min(W,H))
const VAR_THR = 18           // СКО яркости (низкая текстурность ⇒ перекрыт)
const EDGE_DENSITY_THR = 0.05// плотность граней; низкая ⇒ перекрыт
const DARK_P10_THR = 45      // 10-й перцентиль; высокий ⇒ нет тёмного зрачка

const BLINK_HOLD_MS = 260    // <= столько мс считаем «миганием» (не красним)
const ALERT_ON_FRAMES = 2    // антидребезг: сколько плохих кадров подряд для включения
const ALERT_OFF_FRAMES = 4   // антидребезг: сколько хороших кадров подряд для выключения


const L_EYE = [33,160,158,133,153,144]
const R_EYE = [362,385,387,263,373,380]

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
  const rafRef = useRef(null)
  const faceMeshRef = useRef(null)

  const [eyeOffCenter, setEyeOffCenter] = useState(false)
  const alertFramesRef = useRef(0)
  const safeFramesRef = useRef(0)

  const closedSinceRef = useRef(null)

  const canvasRef = useRef(null)
  const ctxRef = useRef(null)

  // --- утилиты ---
  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y)
  const haveAll = (lm, idx) => idx.every(i => lm[i])
  const ear = (lm, idx) => {
    if (!haveAll(lm, idx)) return 0
    const [p1,p2,p3,p4,p5,p6] = idx.map(i => lm[i])
    const v1 = dist(p2, p6), v2 = dist(p3, p5), h = dist(p1, p4)
    return (v1 + v2) / (2 * h + 1e-6)
  }
  const center = (lm, idx) => {
    const pts = idx.map(i => lm[i]).filter(Boolean)
    if (!pts.length) return { x: NaN, y: NaN }
    const x = pts.reduce((s,p)=>s+p.x,0)/pts.length
    const y = pts.reduce((s,p)=>s+p.y,0)/pts.length
    return { x, y }
  }
  const outOfFrame = (lm, idx) => {
    if (!haveAll(lm, idx)) return true
    const c = center(lm, idx)
    if (!Number.isFinite(c.x) || !Number.isFinite(c.y)) return true
    return (
      c.x < FRAME_MARGIN || c.x > 1 - FRAME_MARGIN ||
      c.y < FRAME_MARGIN || c.y > 1 - FRAME_MARGIN
    )
  }

  const ensureCanvas = () => {
    if (!canvasRef.current) canvasRef.current = document.createElement('canvas')
    const canvas = canvasRef.current
    const w = videoRef.current?.videoWidth || 640
    const h = videoRef.current?.videoHeight || 480
    canvas.width = w
    canvas.height = h
    ctxRef.current = canvas.getContext('2d', { willReadFrequently: true })
  }

  const patchMetrics = (cxNorm, cyNorm) => {
    const ctx = ctxRef.current, video = videoRef.current
    if (!ctx || !video) return { std: 0, edgeDensity: 0, p10: 255 }
    const W = ctx.canvas.width, H = ctx.canvas.height
    const r = Math.round(Math.min(W, H) * PATCH_SCALE)
    const cx = Math.round(cxNorm * W), cy = Math.round(cyNorm * H)
    const x0 = Math.max(0, cx - r), y0 = Math.max(0, cy - r)
    const ww = Math.min(W - x0, r * 2), hh = Math.min(H - y0, r * 2)
    if (ww <= 0 || hh <= 0) return { std: 0, edgeDensity: 0, p10: 255 }

    ctx.drawImage(video, 0, 0, W, H)
    const data = ctx.getImageData(x0, y0, ww, hh).data
    const N = (data.length / 4) | 0
    const gray = new Uint8Array(N)
    let sum = 0, sum2 = 0
    for (let i = 0, j = 0; i < data.length; i += 4, j++) {
      const y = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]
      const g = y | 0
      gray[j] = g; sum += g; sum2 += g * g
    }
    const mean = sum / N
    const variance = Math.max(0, sum2 / N - mean * mean)
    const std = Math.sqrt(variance)

    // простая оценка границ
    let edges = 0; const w = ww, h = hh; const thr = 20
    for (let y = 0; y < h - 1; y++) {
      for (let x = 0; x < w - 1; x++) {
        const idx = y * w + x
        const gx = Math.abs(gray[idx + 1] - gray[idx])
        const gy = Math.abs(gray[idx + w] - gray[idx])
        if (gx + gy > thr) edges++
      }
    }
    const edgeDensity = edges / N

    const sorted = Array.from(gray).sort((a,b)=>a-b)
    const p10 = sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.10))]

    return { std, edgeDensity, p10 }
  }

  const startCamera = useCallback(async () => {
    try {
      setIsPreparingCamera(true)
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await new Promise(res => { videoRef.current.onloadedmetadata = res })
      }

      ensureCanvas()

      faceMeshRef.current = new FaceMesh({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
      })
      faceMeshRef.current.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
      })

      const updateAlert = (shouldAlert) => {
        if (shouldAlert) {
          alertFramesRef.current += 1
          safeFramesRef.current = 0
          if (alertFramesRef.current >= ALERT_ON_FRAMES) setEyeOffCenter(true)
        } else {
          safeFramesRef.current += 1
          alertFramesRef.current = 0
          if (safeFramesRef.current >= ALERT_OFF_FRAMES) setEyeOffCenter(false)
        }
      }

      faceMeshRef.current.onResults((results) => {
        if (!results.multiFaceLandmarks || !results.multiFaceLandmarks[0]) {
          // лица нет — сразу критично
          closedSinceRef.current = null
          updateAlert(true)
          return
        }

        const lm = results.multiFaceLandmarks[0]
        const leftEAR = ear(lm, L_EYE), rightEAR = ear(lm, R_EYE)
        const leftOpen = leftEAR > EAR_THR, rightOpen = rightEAR > EAR_THR
        const leftOut = outOfFrame(lm, L_EYE), rightOut = outOfFrame(lm, R_EYE)

        const lc = center(lm, L_EYE), rc = center(lm, R_EYE)
        const { std: lStd, edgeDensity: lED, p10: lP10 } =
          Number.isFinite(lc.x) ? patchMetrics(lc.x, lc.y) : { std: 0, edgeDensity: 0, p10: 255 }
        const { std: rStd, edgeDensity: rED, p10: rP10 } =
          Number.isFinite(rc.x) ? patchMetrics(rc.x, rc.y) : { std: 0, edgeDensity: 0, p10: 255 }

        const leftOcc = (lStd < VAR_THR && lED < EDGE_DENSITY_THR) || (lStd < VAR_THR * 1.2 && lP10 > DARK_P10_THR)
        const rightOcc = (rStd < VAR_THR && rED < EDGE_DENSITY_THR) || (rStd < VAR_THR * 1.2 && rP10 > DARK_P10_THR)

        const outFlag = leftOut || rightOut
        const occFlag = leftOcc || rightOcc
        const anyClosed = !leftOpen || !rightOpen

        let shouldAlert = false
        const now = performance.now()

        if (outFlag || occFlag) {
          // перекрыто/вне кадра — сразу считаем критично, без «мигания»
          closedSinceRef.current = null
          shouldAlert = true
        } else if (anyClosed) {
          // возможно мигание — ждём удержание > BLINK_HOLD_MS
          if (closedSinceRef.current == null) closedSinceRef.current = now
          const dur = now - closedSinceRef.current
          shouldAlert = dur > BLINK_HOLD_MS
        } else {
          // глаза открыты
          closedSinceRef.current = null
          shouldAlert = false
        }

        updateAlert(shouldAlert)
      })

      const loop = async () => {
        if (videoRef.current && faceMeshRef.current) {
          await faceMeshRef.current.send({ image: videoRef.current })
        }
        rafRef.current = requestAnimationFrame(loop)
      }

      setIsPreparingCamera(false)
      loop()
    } catch (e) {
      console.error(e)
      setError('Не удалось получить доступ к камере и микрофону. Проверьте разрешения.')
      setIsPreparingCamera(false)
    }
  }, [])

  const stopCamera = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    faceMeshRef.current = null
    const stream = streamRef.current || (videoRef.current && videoRef.current.srcObject)
    if (stream) stream.getTracks().forEach(t => t.stop())
    streamRef.current = null
  }, [])

  useEffect(() => {
    startCamera()
    return () => {
      stopCamera()
      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current)
    }
  }, [startCamera, stopCamera])

  const startRecording = useCallback(async () => {
    try {
      const stream = streamRef.current || (videoRef.current && videoRef.current.srcObject)
      if (!stream) { setError('Поток видео недоступен. Перезагрузите страницу.'); return }
      mediaRecorderRef.current = new MediaRecorder(stream)
      const chunks = []
      mediaRecorderRef.current.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data) }
      mediaRecorderRef.current.onstop = () => setRecordedBlob(new Blob(chunks, { type: 'video/webm' }))
      mediaRecorderRef.current.start()
      setIsRecording(true)
      setRecordingTime(0)
      recordingIntervalRef.current = setInterval(() => setRecordingTime(p => p + 1), 1000)
    } catch (e) {
      console.error(e)
      setError('Ошибка при начале записи')
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current)
    }
  }, [isRecording])

  const handleFinish = useCallback(async () => {
    if (!recordedBlob) { setError('Сначала запишите видео'); return }
    try {
      const formData = new FormData()
      formData.append('video', recordedBlob, 'pitch-recording.webm')
      formData.append('pitch_id', id)
      const response = await fetch('/api/v1/score/pitch', { method: 'POST', body: formData })
      if (!response.ok) throw new Error('Ошибка при отправке видео')
      const result = await response.json()
      navigate(`/pitch/${id}/results`, { state: { analysisResult: result } })
    } catch (e) {
      console.error(e)
      setError('Ошибка при обработке видео: ' + e.message)
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
            <Button style={{ marginLeft: 'auto' }} variant='outline' as={Link} to={`/pitch/${id}`}>
              ← Назад к выступлению
            </Button>
          </div>

          {error && (
            <div className='error'>
              <p>⚠️ {error}</p>
              <Button variant='secondary' onClick={() => setError(null)}>Закрыть</Button>
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

            {/* Компактный бейдж-индикатор */}
            <div className={`gaze-overlay ${eyeOffCenter ? 'alert' : ''}`}>
              <div className={`lamp ${eyeOffCenter ? 'lamp-on' : 'lamp-off'}`} />
              {eyeOffCenter && <span className='gaze-text'>Проверьте глаза / позицию</span>}
            </div>
          </div>

          <div className='recording-controls'>
            {!isRecording && !recordedBlob && (
              <Button variant='primary' size='large' onClick={startRecording}>Начать запись</Button>
            )}
            {isRecording && (
              <Button variant='danger' size='large' onClick={stopRecording}>Остановить запись</Button>
            )}
            {recordedBlob && !isRecording && (
              <div className='recording-finished'>
                <p>✅ Запись завершена!</p>
                <div className='final-actions'>
                  <Button variant='outline' onClick={() => { setRecordedBlob(null); setRecordingTime(0) }}>
                    🔄 Записать заново
                  </Button>
                  <Button variant='primary' onClick={handleFinish}>📊 Получить результаты</Button>
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
