const BASE_URL = '/api';

// FastAPI sends a plain string for most errors but a list of objects for validation errors (HTTP 422).
// Turn either into text a person can read, for example "amount: Input should be greater than 0".
function formatErrorDetail(detail) {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc.filter((part) => part !== 'body').join('.') : '';
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join('; ');
  }
  if (detail && typeof detail === 'object') return JSON.stringify(detail);
  return detail;
}

export async function request(endpoint, options = {}) {
  // A file upload sets its own content type (with the multipart boundary), so it must not be forced to JSON
  const isUpload = options.body instanceof FormData;
  const config = {
    ...options,
    headers: {
      ...(isUpload ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
  };

  if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body);
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, config);

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = formatErrorDetail(errJson.detail) || errJson.message || JSON.stringify(errJson);
    } catch (e) {
      // response wasn't JSON
    }
    const error = new Error(errorDetail);
    error.status = response.status;
    throw error;
  }

  // 204 No Content (for example, logout) has no body to parse
  if (response.status === 204) return null;

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
  getTicketTechnicians: () => request('/tickets/technicians'),
  assignTicket: (id, technicianId) => request(`/tickets/${id}/assign`, { method: 'POST', body: { technician_id: technicianId } }),
  // The technician's own repair visits and their finding at the site
  getMyRepairVisits: () => request('/repair-visits'),
  reportRepairVisit: (id, needsReplacement, notes) =>
    request(`/repair-visits/${id}/report`, { method: 'POST', body: { needs_replacement: needsReplacement, notes: notes || null } }),
  decideTicketQuote: (id, approved) => request(`/tickets/${id}/quote`, { method: 'POST', body: { approved } }),
  // Replacement units for repair tickets are sent by the warehouse
  getReplacementRequests: () => request('/dispatch/replacements/list'),
  sendReplacement: (ticketId, serialNumber) =>
    request(`/dispatch/replacements/${ticketId}/send`, { method: 'POST', body: serialNumber ? { serial_number: serialNumber } : undefined }),
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

  // Customer accounts
  register: (data) => request('/auth/register', { method: 'POST', body: data }),
  login: (data) => request('/auth/login', { method: 'POST', body: data }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/auth/me'),
  changePassword: (data) => request('/auth/change-password', { method: 'POST', body: data }),

  // Director's view
  getReportSummary: (period, from = '', to = '') =>
    request(`/reports/summary?period=${period}${period === 'custom' ? `&from=${from}&to=${to}` : ''}`),
  getPipeline: () => request('/reports/pipeline'),
  getProfitabilityRange: (from, to) => request(`/profitability?from=${from}&to=${to}`),

  // Subsidy files
  getSubsidies: () => request('/subsidies'),
  openSubsidy: (orderId) => request('/subsidies', { method: 'POST', body: { order_id: orderId } }),
  updateSubsidy: (id, data) => request(`/subsidies/${id}`, { method: 'PUT', body: data }),
  getPortalSubsidies: () => request('/portal/subsidies'),

  // Technician pay (administrator)
  getPayrollSummary: (from, to) => request(`/payroll/summary?from=${from}&to=${to}`),
  getPayouts: () => request('/payroll/payouts'),
  payTechnician: (technicianId, from, to, reference) =>
    request('/payroll/payouts', { method: 'POST', body: { technician_id: technicianId, from_date: from, to_date: to, reference: reference || null } }),
  setTechnicianRate: (technicianId, rate) =>
    request(`/payroll/technicians/${technicianId}/rate`, { method: 'PUT', body: { hourly_rate: rate } }),

  // Stock purchases (warehouse)
  getStockProducts: () => request('/stock/products'),
  getStockSerials: (status = 'In Stock') => request(`/stock/serials?status=${encodeURIComponent(status)}`),
  getStockPurchases: () => request('/stock/purchases'),
  receiveStock: (data) => request('/stock/purchases', { method: 'POST', body: data }),

  // Installation proof and delivery
  getInstallationPhotos: (id) => request(`/installations/${id}/photos`),
  uploadInstallationPhoto: (id, file, caption = '') => {
    const form = new FormData();
    form.append('file', file);
    form.append('caption', caption);
    return request(`/installations/${id}/photos`, { method: 'POST', body: form });
  },
  deleteInstallationPhoto: (id, photoId) => request(`/installations/${id}/photos/${photoId}`, { method: 'DELETE' }),
  saveInstallationSignature: (id, signedBy, dataUrl) =>
    request(`/installations/${id}/signature`, { method: 'POST', body: { signed_by: signedBy, signature_data_url: dataUrl } }),
  markDelivered: (orderId) => request(`/dispatch/${orderId}/delivered`, { method: 'POST' }),
  getPortalInstallations: () => request('/portal/installations'),

  // Survey scheduling
  scheduleSurvey: (data) => request('/surveys/schedule', { method: 'POST', body: data }),
  completeSurvey: (id, data) => request(`/surveys/${id}/complete`, { method: 'PUT', body: data }),
  reassignSurvey: (id, technicianId) =>
    request(`/surveys/${id}/reassign`, { method: 'POST', body: { technician_id: technicianId } }),
  setLeadStatus: (id, status, extra = {}) => request(`/leads/${id}/status`, { method: 'POST', body: { status, ...extra } }),

  // Alerts
  getNotifications: () => request('/notifications'),
  readNotification: (id) => request(`/notifications/${id}/read`, { method: 'POST' }),
  readAllNotifications: () => request('/notifications/read-all', { method: 'POST' }),

  // Warehouse pick list, support lookup, order cancellation
  getPickList: (orderId) => request(`/dispatch/${orderId}/pick-list`),
  searchCustomers: (q) => request(`/customers/search?q=${encodeURIComponent(q)}`),
  cancelOrder: (id, reason) => request(`/orders/${id}/cancel`, { method: 'POST', body: { reason } }),

  // Staff accounts (administrator only)
  getStaffAccounts: () => request('/admin/users'),
  createStaffAccount: (data) => request('/admin/users', { method: 'POST', body: data }),
  deactivateStaff: (id) => request(`/admin/users/${id}/deactivate`, { method: 'POST' }),
  activateStaff: (id) => request(`/admin/users/${id}/activate`, { method: 'POST' }),
  assignTechnician: (installationId, technicianId) =>
    request(`/installations/${installationId}/assign`, { method: 'POST', body: { technician_id: technicianId } }),

  // Customer portal
  getPortalPackages: () => request('/portal/packages'),
  getMyEnquiries: () => request('/portal/enquiries'),
  createEnquiry: (data) => request('/portal/enquiries', { method: 'POST', body: data }),
  getPortalQuotations: () => request('/portal/quotations'),
  acceptPortalQuotation: (id) => request(`/portal/quotations/${id}/accept`, { method: 'POST' }),
  getBankDetails: () => request('/portal/bank-details'),
  reportPayment: (data) => request('/portal/payments', { method: 'POST', body: data }),
  getMyPayments: () => request('/portal/payments'),

  getMyWarranties: () => request('/portal/warranties'),
  getMyTickets: () => request('/portal/tickets'),
  raiseTicket: (data) => request('/portal/tickets', { method: 'POST', body: data }),
  confirmMyTicket: (id) => request(`/portal/tickets/${id}/confirm`, { method: 'POST' }),
  decideMyTicketQuote: (id, approved) => request(`/portal/tickets/${id}/quote`, { method: 'POST', body: { approved } }),
  getMyInvoices: () => request('/portal/invoices'),
  payInvoice: (id, data) => request(`/portal/invoices/${id}/payments`, { method: 'POST', body: data }),

  // Staff: quotation sending, invoice sending and payment verification
  sendQuotation: (id) => request(`/quotations/${id}/send`, { method: 'POST' }),
  sendInvoice: (id) => request(`/invoices/${id}/send`, { method: 'POST' }),
  verifyPayment: (id) => request(`/payments/${id}/verify`, { method: 'POST' }),
};
