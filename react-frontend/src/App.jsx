import { Routes, Route, Navigate } from 'react-router-dom'
import Portal from './pages/Portal'
import Procesos from './pages/Procesos'
import Cargas from './pages/Cargas'
import Reportes from './pages/Reportes'
import Resultantes from './pages/Resultantes'
import SmsPage from './pages/sms/SmsPage'
import IvrPage from './pages/ivr/IvrPage'
import MailPage from './pages/mail/MailPage'
import SantanderConsumerPage from './pages/santander_consumer/SantanderConsumerPage'
import GmPage from './pages/cargas/GmPage'
import SantanderPage from './pages/cargas/SantanderPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Portal />} />
      <Route path="/procesos" element={<Procesos />} />
      <Route path="/procesos/ivr" element={<IvrPage />} />
      <Route path="/procesos/mail" element={<MailPage />} />
      <Route path="/procesos/santander-consumer" element={<SantanderConsumerPage />} />
      <Route path="/cargas" element={<Cargas />} />
      <Route path="/cargas/gm" element={<GmPage />} />
      <Route path="/cargas/santander" element={<SantanderPage />} />
      <Route path="/reportes" element={<Reportes />} />
      <Route path="/resultantes" element={<Resultantes />} />
      <Route path="/procesos/sms" element={<SmsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
