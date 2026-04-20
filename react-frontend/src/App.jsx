import { Routes, Route, Navigate } from 'react-router-dom'
import Portal from './pages/Portal'
import Procesos from './pages/Procesos'
import Cargas from './pages/Cargas'
import Reportes from './pages/Reportes'
import Resultantes from './pages/Resultantes'
import SmsPage from './pages/sms/SmsPage'
import IvrPage from './pages/ivr/IvrPage'
import MailPage from './pages/mail/MailPage'
import CrmPage from './pages/CrmPage'
import BackofficeCatalogos from './pages/BackofficeCatalogos'
import GmPage from './pages/cargas/GmPage'
import SantanderPage from './pages/cargas/SantanderPage'
import PorschePage from './pages/cargas/PorschePage'
import BitPage from './pages/cargas/BitPage'
import TannerPage from './pages/cargas/TannerPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Portal />} />
      <Route path="/procesos" element={<Procesos />} />
      <Route path="/procesos/ivr" element={<IvrPage />} />
      <Route path="/procesos/mail" element={<MailPage />} />
      <Route path="/procesos/crm" element={<CrmPage />} />
      <Route path="/cargas" element={<Cargas />} />
      <Route path="/cargas/gm" element={<GmPage />} />
      <Route path="/cargas/santander" element={<SantanderPage />} />
      <Route path="/cargas/porsche" element={<PorschePage />} />
      <Route path="/cargas/bit" element={<BitPage />} />
      <Route path="/cargas/tanner" element={<TannerPage />} />
      <Route path="/reportes" element={<Reportes />} />
      <Route path="/backoffice/catalogos" element={<BackofficeCatalogos />} />
      <Route path="/resultantes" element={<Resultantes />} />
      <Route path="/procesos/sms" element={<SmsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
