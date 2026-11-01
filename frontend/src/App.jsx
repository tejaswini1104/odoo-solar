import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import { ToastProvider } from './components/Toast';
import { useAuth } from './auth/AuthContext';
import { TABS_BY_ROLE } from './auth/access';

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
import RepairVisits from './pages/RepairVisits';
import Invoices from './pages/Invoices';
import Profitability from './pages/Profitability';
import StaffAccounts from './pages/StaffAccounts';
import Subsidies from './pages/Subsidies';
import Payroll from './pages/Payroll';
import StockPurchases from './pages/StockPurchases';

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
  repairs: 'Repair Visits',
  invoices: 'Billing & Invoices',
  profitability: 'Order-Level Profitability View',
  users: 'Staff Accounts',
  subsidies: 'Government Subsidy Files',
  payroll: 'Technician Hours & Pay',
  stock: 'Stock Purchases',
};

export default function App() {
  const { user } = useAuth();
  const allowedTabs = TABS_BY_ROLE[user?.role] || [];
  const [requestedTab, setActiveTab] = useState(allowedTabs[0]);
  // Never show a screen the role is not allowed to use, whatever was asked for
  const activeTab = allowedTabs.includes(requestedTab) ? requestedTab : allowedTabs[0];

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
      case 'repairs':
        return <RepairVisits />;
      case 'warranties':
        return <Warranties />;
      case 'tickets':
        return <ServiceTickets setActiveTab={setActiveTab} />;
      case 'invoices':
        return <Invoices />;
      case 'profitability':
        return <Profitability />;
      case 'users':
        return <StaffAccounts />;
      case 'subsidies':
        return <Subsidies />;
      case 'payroll':
        return <Payroll />;
      case 'stock':
        return <StockPurchases />;
      default:
        return null;
    }
  };

  return (
    <ToastProvider>
      <div className="flex h-screen bg-slate-100 font-sans antialiased overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        {/* Main Workspace */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <Navbar activeTitle={tabTitles[activeTab] || 'SunPower ERP'} onOpenAlert={setActiveTab} />
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
