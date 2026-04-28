import { Routes, Route, Navigate } from 'react-router-dom'
import Portal from './modules/home/PortalPage'
import Procesos from './modules/procesos/ProcesosPage'
import Cargas from './modules/cargas/CargasPage'
import Reportes from './modules/reportes/ReportesPage'
import Resultantes from './modules/resultantes/ResultantesPage'
import SmsPage from './modules/procesos/sms/SmsPage'
import IvrPage from './modules/procesos/ivr/IvrPage'
import MailPage from './modules/procesos/mail/MailPage'
import CrmPage from './modules/procesos/crm/CrmPage'
import SantanderConsumerPage from './modules/procesos/santander_consumer/SantanderConsumerPage'
import GmPage from './modules/cargas/gm/GmPage'
import SantanderPage from './modules/cargas/santander/SantanderPage'
import PorschePage from './modules/cargas/porsche/PorschePage'
import BitPage from './modules/cargas/bit/BitPage'
import TannerPage from './modules/cargas/tanner/TannerPage'
import BackofficeCatalogos from './modules/backoffice/BackofficeCatalogosPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Portal />} />
      <Route path="/procesos" element={<Procesos />} />
      <Route path="/procesos/ivr" element={<IvrPage />} />
      <Route path="/procesos/mail" element={<MailPage />} />
      <Route path="/procesos/crm" element={<CrmPage />} />
      <Route path="/procesos/santander-consumer" element={<SantanderConsumerPage />} />
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
