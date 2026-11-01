import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './auth/AuthContext.jsx'
import { RequireCustomer, RequireStaff } from './auth/RouteGuards.jsx'
import Login from './auth/Login.jsx'
import Register from './auth/Register.jsx'
import PortalLayout from './portal/PortalLayout.jsx'
import Catalog from './portal/Catalog.jsx'
import NewEnquiry from './portal/NewEnquiry.jsx'
import MyEnquiries from './portal/MyEnquiries.jsx'
import PortalQuotes from './portal/PortalQuotes.jsx'
import PortalPayments from './portal/PortalPayments.jsx'
import PortalInvoices from './portal/PortalInvoices.jsx'
import PortalInstallation from './portal/PortalInstallation.jsx'
import PortalSubsidy from './portal/PortalSubsidy';
import PortalWarranties from './portal/PortalWarranties.jsx'
import PortalSupport from './portal/PortalSupport.jsx'
import { ToastProvider } from './components/Toast.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/portal" element={<RequireCustomer><PortalLayout /></RequireCustomer>}>
              <Route index element={<Catalog />} />
              <Route path="enquire" element={<NewEnquiry />} />
              <Route path="enquiries" element={<MyEnquiries />} />
              <Route path="quotations" element={<PortalQuotes />} />
              <Route path="payments" element={<PortalPayments />} />
              <Route path="installation" element={<PortalInstallation />} />
              <Route path="subsidy" element={<PortalSubsidy />} />
              <Route path="invoices" element={<PortalInvoices />} />
              <Route path="warranties" element={<PortalWarranties />} />
              <Route path="support" element={<PortalSupport />} />
            </Route>
            {/* Staff application: every staff role signs in at /login and sees only its own screens */}
            <Route path="*" element={<RequireStaff><App /></RequireStaff>} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
