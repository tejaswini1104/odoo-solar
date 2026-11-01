-- What sales learn on the first call with an enquirer, and the alerts table (created by create_all).
ALTER TABLE leads ADD COLUMN IF NOT EXISTS shadow_free_area DOUBLE PRECISION;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS grid_connection_ok BOOLEAN;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS call_notes TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS contacted_at TIMESTAMP;
