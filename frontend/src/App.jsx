import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import { ToastProvider } from './components/Toast';

// Pages
import Dashboard from './pages/Dashboard';
import Leads from './pages/Leads';
import Customers from './pages/Customers';
import SiteSurveys from './pages/SiteSurveys';
import SolarPackages from './pages/SolarPackages';
import Quotations from './pages/Quotations';
import SalesOrders from './pages/SalesOrders';
import Dispatch from './pages/Dispatch';
import Installations from './pages/Installations';
import Warranties from './pages/Warranties';
import ServiceTickets from './pages/ServiceTickets';
import Invoices from './pages/Invoices';
import Profitability from './pages/Profitability';

const tabTitles = {
  dashboard: 'Executive Dashboard',
  leads: 'Leads & Enquiries',
  customers: 'Customer Accounts',
  surveys: 'Site Surveys & Approvals',
  packages: 'Solar Packages & Automatic BOM',
  quotations: 'Turnkey Quotations',
  orders: 'Sales Orders & Payments',
  dispatch: 'Hardware Dispatch & Serial Validation',
  installations: 'Rooftop Installations & Completion',
  warranties: 'Warranty Registry Engine',
  tickets: 'After-Sales Service Tickets',
  invoices: 'Billing & Invoices',
  profitability: 'Order-Level Profitability View',
};

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard setActiveTab={setActiveTab} />;
      case 'leads':
        return <Leads onCustomerCreated={() => setActiveTab('customers')} />;
      case 'customers':
        return <Customers />;
      case 'surveys':
        return <SiteSurveys />;
      case 'packages':
        return <SolarPackages />;
      case 'quotations':
        return <Quotations setActiveTab={setActiveTab} />;
      case 'orders':
        return <SalesOrders setActiveTab={setActiveTab} />;
      case 'dispatch':
        return <Dispatch setActiveTab={setActiveTab} />;
      case 'installations':
        return <Installations setActiveTab={setActiveTab} />;
      case 'warranties':
        return <Warranties />;
      case 'tickets':
        return <ServiceTickets setActiveTab={setActiveTab} />;
      case 'invoices':
        return <Invoices />;
      case 'profitability':
        return <Profitability />;
      default:
        return <Dashboard setActiveTab={setActiveTab} />;
    }
  };

  return (
    <ToastProvider>
      <div className="flex h-screen bg-slate-100 font-sans antialiased overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        {/* Main Workspace */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <Navbar activeTitle={tabTitles[activeTab] || 'SunPower ERP'} />
          <main className="flex-1 p-8 overflow-y-auto">
            <div className="max-w-7xl mx-auto pb-12">
              {renderContent()}
            </div>
          </main>
        </div>
      </div>
    </ToastProvider>
  );
}
