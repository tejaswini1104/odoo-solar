const BASE_URL = '/api';

export async function request(endpoint, options = {}) {
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body);
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, config);

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch (e) {
      // response wasn't JSON
    }
    const error = new Error(errorDetail);
    error.status = response.status;
    throw error;
  }

  return response.json();
}

export const api = {
  // Dashboard
  getDashboard: () => request('/dashboard'),

  // Customers
  getCustomers: () => request('/customers'),
  getCustomer: (id) => request(`/customers/${id}`),
  createCustomer: (data) => request('/customers', { method: 'POST', body: data }),

  // Leads
  getLeads: () => request('/leads'),
  createLead: (data) => request('/leads', { method: 'POST', body: data }),
  convertLead: (id) => request(`/leads/${id}/convert`, { method: 'POST' }),

  // Site Surveys
  getSurveys: () => request('/surveys'),
  getSurvey: (id) => request(`/surveys/${id}`),
  createSurvey: (data) => request('/surveys', { method: 'POST', body: data }),
  approveSurvey: (id) => request(`/surveys/${id}/approve`, { method: 'POST' }),
  rejectSurvey: (id) => request(`/surveys/${id}/reject`, { method: 'POST' }),

  // Technicians
  getTechnicians: () => request('/technicians'),

  // Packages & BOM
  getPackages: () => request('/packages'),
  getPackage: (id) => request(`/packages/${id}`),
  getPackageBOM: (id) => request(`/packages/${id}/bom`),

  // Quotations
  getQuotations: () => request('/quotations'),
  getQuotation: (id) => request(`/quotations/${id}`),
  createQuotation: (data) => request('/quotations', { method: 'POST', body: data }),
  confirmQuotation: (id) => request(`/quotations/${id}/confirm`, { method: 'POST' }),

  // Payments
  getPayments: () => request('/payments'),
  createPayment: (data) => request('/payments', { method: 'POST', body: data }),

  // Sales Orders
  getOrders: () => request('/orders'),
  getOrder: (id) => request(`/orders/${id}`),
  confirmOrder: (id) => request(`/orders/${id}/confirm`, { method: 'POST' }),

  // Dispatch & Inventory
  getInventory: () => request('/inventory'),
  getInventorySerials: (params = '') => request(`/inventory/serials${params}`),
  getDispatchRequirements: (orderId) => request(`/dispatch/${orderId}/requirements`),
  dispatchSerials: (orderId, serials) => request(`/dispatch/${orderId}/serials`, {
    method: 'POST',
    body: { serial_numbers: serials }
  }),

  // Installations
  getInstallations: () => request('/installations'),
  getInstallation: (id) => request(`/installations/${id}`),
  getInstallationSerials: (id) => request(`/installations/${id}/serials`),
  completeInstallation: (id, data) => request(`/installations/${id}/complete`, {
    method: 'POST',
    body: data
  }),

  // Warranties
  getWarranties: (serial = '') => request(`/warranties${serial ? `?serial_number=${encodeURIComponent(serial)}` : ''}`),
  getWarrantyBySerial: (serial) => request(`/warranties/${encodeURIComponent(serial)}`),

  // Service Tickets
  getTickets: () => request('/tickets'),
  getTicket: (id) => request(`/tickets/${id}`),
  createTicket: (data) => request('/tickets', { method: 'POST', body: data }),
  resolveTicket: (id) => request(`/tickets/${id}/resolve`, { method: 'POST' }),
  customerConfirmTicket: (id) => request(`/tickets/${id}/customer-confirm`, { method: 'POST' }),
  closeTicket: (id) => request(`/tickets/${id}/close`, { method: 'POST' }),

  // Invoices
  getInvoices: () => request('/invoices'),
  getInvoice: (id) => request(`/invoices/${id}`),
  updateInvoiceItems: (id, items) => request(`/invoices/${id}/items`, { method: 'PUT', body: items }),
  markInvoicePaid: (id) => request(`/invoices/${id}/pay`, { method: 'POST' }),

  // Profitability
  getProfitability: () => request('/profitability'),
};
