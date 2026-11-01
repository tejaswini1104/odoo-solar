-- Links a payment to an invoice (service invoices for billable repairs).
ALTER TABLE payments ADD COLUMN IF NOT EXISTS invoice_id INTEGER REFERENCES invoices(id);
