import { Routes, Route, Link } from 'react-router-dom'
import './App.scss'
import Home from './pages/Home'
import PitchDetail from './pages/PitchDetail'
import CreatePitch from './pages/CreatePitch'
import EditPitch from './pages/EditPitch'
import RecordVideo from './pages/RecordVideo'
import UploadVideo from './pages/UploadVideo'
import PitchResults from './pages/PitchResults'
import PresentationAnalysis from './pages/PresentationAnalysis'
import SpeechAnalysis from './pages/SpeechAnalysis'

const App = () => {
  return (
    <div className='app'>
      <header className='header'>
        <Link to='/' className='logo-link'>
          <h1 className='logo'>
            <span className='logo-light'>лайт</span>
            <span className='logo-pitch'>питч</span>
          </h1>
        </Link>
        <p className='subtitle'>AI-помощник для презентаций и питчей</p>
      </header>

      {/* Routes */}
      <Routes>
        <Route path='/' element={<Home />} />
        <Route path='/create' element={<CreatePitch />} />
        <Route path='/pitch/:id' element={<PitchDetail />} />
        <Route path='/pitch/:id/edit' element={<EditPitch />} />
        <Route path='/pitch/:id/record' element={<RecordVideo />} />
        <Route path='/pitch/:id/upload' element={<UploadVideo />} />
        <Route path='/pitch/:id/results' element={<PitchResults />} />
        <Route path='/pitch/:id/presentation-analysis' element={<PresentationAnalysis />} />
        <Route path='/pitch/:id/speech-analysis' element={<SpeechAnalysis />} />
        <Route path='*' element={<NotFound />} />
      </Routes>
    </div>
  )
}

// Компонент для 404 страницы
const NotFound = () => {
  return (
    <main className='main'>
      <div className='container'>
        <div className='empty-state'>
          <div className='empty-icon'>😕</div>
          <h3>Страница не найдена</h3>
          <p>Запрашиваемая страница не существует</p>
          <Link to='/' className='btn-primary'>
            Вернуться на главную
          </Link>
        </div>
      </div>
    </main>
  )
}

export default App
