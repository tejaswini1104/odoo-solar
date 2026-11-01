-- A claim on the bulk solar panel warranty (no serial number) and the unit that replaced a faulty one.
ALTER TABLE service_tickets ADD COLUMN IF NOT EXISTS warranty_id INTEGER REFERENCES warranties(id);
ALTER TABLE service_tickets ADD COLUMN IF NOT EXISTS replacement_serial VARCHAR(100);
