-- Repair tickets are handled by an assigned technician, quoted when out of warranty, and a replacement unit is dispatched.
ALTER TABLE service_tickets ADD COLUMN IF NOT EXISTS technician_id INTEGER REFERENCES technicians(id);
ALTER TABLE service_tickets ADD COLUMN IF NOT EXISTS inspection_notes TEXT;
ALTER TABLE service_tickets ADD COLUMN IF NOT EXISTS needs_replacement BOOLEAN;
ALTER TABLE service_tickets ADD COLUMN IF NOT EXISTS quote_status VARCHAR(20);
ALTER TABLE service_tickets ADD COLUMN IF NOT EXISTS dispatch_serial VARCHAR(100);
ALTER TABLE service_tickets ADD COLUMN IF NOT EXISTS dispatched_at TIMESTAMP;
