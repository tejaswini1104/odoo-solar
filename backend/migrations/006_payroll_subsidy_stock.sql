-- Technician pay: a rate per hour, and a marker on each job once it has been paid.
-- (The payout, subsidy and stock purchase tables are created by create_all.)
ALTER TABLE technicians ADD COLUMN IF NOT EXISTS hourly_rate DOUBLE PRECISION NOT NULL DEFAULT 250;
ALTER TABLE installations ADD COLUMN IF NOT EXISTS payout_id INTEGER REFERENCES technician_payouts(id);
