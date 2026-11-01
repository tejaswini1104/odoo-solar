-- Adds the bank transfer reference number to payments.
-- create_all() creates new tables but does not alter existing ones, so this runs once on an existing database.
ALTER TABLE payments ADD COLUMN IF NOT EXISTS reference_number VARCHAR(100);
CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_reference_number ON payments (reference_number);
