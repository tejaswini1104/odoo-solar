// Which staff screens each role sees. This only shapes the menu. The server enforces the real rules,
// so a role that is not listed here is refused by the API even if someone types a URL by hand.
export const TABS_BY_ROLE = {
  admin: ['dashboard', 'leads', 'customers', 'surveys', 'packages', 'quotations', 'orders', 'dispatch', 'stock', 'installations', 'subsidies', 'warranties', 'tickets', 'invoices', 'profitability', 'payroll', 'users'],
  sales: ['leads', 'customers', 'surveys', 'packages', 'quotations', 'orders', 'installations', 'subsidies', 'warranties', 'tickets', 'invoices'],
  technician: ['surveys', 'installations', 'packages'],
  support: ['customers', 'subsidies', 'warranties', 'tickets', 'invoices', 'packages'],
  warehouse: ['dispatch', 'stock', 'packages'],
};

export const ROLE_LABELS = {
  admin: 'Administrator',
  sales: 'Sales',
  technician: 'Technician',
  support: 'Customer Support',
  warehouse: 'Warehouse',
  customer: 'Customer',
};

export const isStaff = (role) => Object.prototype.hasOwnProperty.call(TABS_BY_ROLE, role);

// Where a signed-in user belongs: customers use the portal, staff use the main application
export const homeFor = (role) => (role === 'customer' ? '/portal' : '/');
