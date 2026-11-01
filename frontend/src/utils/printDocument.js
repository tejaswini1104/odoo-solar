// Opens a clean, branded page for an invoice or quotation and starts the browser's print dialog.
// "Save as PDF" in that dialog gives a file the company can email or WhatsApp to the customer.

const COMPANY = 'SunPower Solutions';

const esc = (value) =>
  String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const rupees = (n) => `₹${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const STYLE = `
  body { font-family: Arial, Helvetica, sans-serif; color: #0f172a; margin: 32px; font-size: 13px; }
  .head { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #f59e0b; padding-bottom: 12px; }
  h1 { margin: 0; font-size: 22px; } h2 { margin: 0; font-size: 18px; text-align: right; }
  .muted { color: #475569; font-size: 12px; }
  table { width: 100%; border-collapse: collapse; margin-top: 18px; }
  th { text-align: left; background: #f1f5f9; padding: 8px; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
  td { padding: 8px; border-bottom: 1px solid #e2e8f0; }
  .num { text-align: right; white-space: nowrap; }
  .totals { margin-left: auto; width: 280px; margin-top: 14px; }
  .totals div { display: flex; justify-content: space-between; padding: 4px 0; }
  .grand { border-top: 2px solid #0f172a; font-weight: bold; font-size: 15px; margin-top: 4px; padding-top: 8px !important; }
  .note { margin-top: 28px; font-size: 11px; color: #475569; }
  @media print { body { margin: 12mm; } }
`;

function open(title, body) {
  const win = window.open('', '_blank', 'width=900,height=1000');
  if (!win) {
    window.alert('Allow pop-ups for this site to print or save the document.');
    return;
  }
  win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${esc(title)}</title><style>${STYLE}</style></head><body>${body}</body></html>`);
  win.document.close();
  win.focus();
  // Give the new page a moment to lay out before the print dialog opens
  win.onload = () => win.print();
  setTimeout(() => { try { win.print(); } catch { /* the window was closed */ } }, 400);
}

function layout({ kind, number, date, customer, rows, subtotal, tax, total, status, notes }) {
  const lines = rows
    .map(
      (r, i) => `<tr><td>${i + 1}</td><td>${esc(r.description)}</td><td class="num">${esc(r.quantity)}</td>` +
        `<td class="num">${rupees(r.unit_price)}</td><td class="num">${rupees(r.total)}</td></tr>`
    )
    .join('');
  return `
    <div class="head">
      <div><h1>${COMPANY}</h1><div class="muted">Rooftop solar installation and service</div></div>
      <div><h2>${esc(kind)}</h2><div class="muted" style="text-align:right">${esc(number)}<br>${esc(date)}${status ? `<br>Status: ${esc(status)}` : ''}</div></div>
    </div>
    <p><strong>Billed to</strong><br>${esc(customer)}</p>
    <table>
      <thead><tr><th>#</th><th>Description</th><th class="num">Qty</th><th class="num">Unit price</th><th class="num">Amount</th></tr></thead>
      <tbody>${lines}</tbody>
    </table>
    <div class="totals">
      <div><span>Subtotal</span><span>${rupees(subtotal)}</span></div>
      <div><span>GST (18%)</span><span>${rupees(tax)}</span></div>
      <div class="grand"><span>Total</span><span>${rupees(total)}</span></div>
    </div>
    <p class="note">${esc(notes)}</p>`;
}

const dateOf = (iso) => new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

export function printInvoice(invoice, customerName) {
  const number = invoice.invoice_number;
  open(`Invoice ${number}`, layout({
    kind: 'TAX INVOICE',
    number,
    date: dateOf(invoice.created_at),
    customer: customerName || invoice.customer_name || `Customer #${invoice.customer_id}`,
    rows: (invoice.items || []).map((it) => ({ description: it.description, quantity: it.quantity, unit_price: it.unit_price, total: it.total })),
    subtotal: invoice.subtotal,
    tax: invoice.tax,
    total: invoice.total,
    status: invoice.status,
    notes: invoice.ticket_id
      ? `Repair service for ticket TCK-${String(invoice.ticket_id).padStart(4, '0')}. Thank you for choosing ${COMPANY}.`
      : `Thank you for choosing ${COMPANY}.`,
  }));
}

export function printQuotation(quote) {
  const number = `QTN-${String(quote.id).padStart(5, '0')}`;
  open(`Quotation ${number}`, layout({
    kind: 'QUOTATION',
    number,
    date: dateOf(quote.created_at),
    customer: quote.customer_name || `Customer #${quote.customer_id}`,
    rows: (quote.items || []).map((it) => ({ description: it.product_name, quantity: it.quantity, unit_price: it.unit_price, total: it.total_price })),
    subtotal: quote.subtotal,
    tax: quote.tax,
    total: quote.total,
    status: null,
    notes: `${quote.package_name || 'Solar system'}. Prices include supply and installation. An advance is required to confirm the order.`,
  }));
}
